import RPi.GPIO as GPIO
import tm1637
import time
import subprocess


CLK = 23
DIO = 24
BTN_PLUS = 17
BTN_MINUS = 27
BTN_MAIN = 22
BTN_VOL_PLUS = 6
BTN_VOL_MINUS = 5

class HardwareManager:
    def __init__(self, state, logic):
        self.state = state
        self.logic = logic

        print("🔌 [HARDWARE] Inicializuji GPIO a TM1637...")

        
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        
        self.display = tm1637.TM1637(clk=CLK, dio=DIO)
        self.display.brightness(2) # Jas od 0 (nejnižší) do 7 (nejvyšší)

        
        buttons = [BTN_PLUS, BTN_MINUS, BTN_MAIN, BTN_VOL_PLUS, BTN_VOL_MINUS]
        GPIO.setup(buttons, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        
        GPIO.add_event_detect(BTN_PLUS, GPIO.FALLING, callback=self._cb_plus, bouncetime=300)
        GPIO.add_event_detect(BTN_MINUS, GPIO.FALLING, callback=self._cb_minus, bouncetime=300)
        GPIO.add_event_detect(BTN_MAIN, GPIO.FALLING, callback=self._cb_main, bouncetime=400)
        GPIO.add_event_detect(BTN_VOL_PLUS, GPIO.FALLING, callback=self._cb_vol_plus, bouncetime=250)
        GPIO.add_event_detect(BTN_VOL_MINUS, GPIO.FALLING, callback=self._cb_vol_minus, bouncetime=250)

        
        self._apply_system_volume()
        self.update_display()

    
    def _cb_plus(self, channel):
        if self.state.is_timer_running:
            return

        start_time = time.time()

        
        while GPIO.input(channel) == GPIO.LOW:
            time.sleep(0.05)

        
        duration = time.time() - start_time

        if duration > 0.6:  # DLOUHÝ STISK (déle než 0.6 sekundy)
            if self.state.edit_mode == 'S': 
                self.state.edit_mode = 'M'
            elif self.state.edit_mode == 'M': 
                self.state.edit_mode = 'H'
            elif self.state.edit_mode == 'H': 
                self.state.edit_mode = 'S' # Rotace zpět na sekundy
            print(f"Režim změněn na: {self.state.edit_mode}")
            
        else:
            if self.state.edit_mode == 'H':
                self.state.timer_seconds += 3600
            elif self.state.edit_mode == 'M':
                self.state.timer_seconds += 60
            elif self.state.edit_mode == 'S':
                self.state.timer_seconds += 1

        self.update_display()
        self.state.trigger_update()

    def _cb_minus(self, channel):
        """Ubere čas, nebo při dlouhém stisku změní jednotku dolů (H -> M -> S)"""
        if self.state.is_timer_running:
            return

        start_time = time.time()

        
        while GPIO.input(channel) == GPIO.LOW:
            time.sleep(0.05)
            
        duration = time.time() - start_time

        if duration > 0.6:
            if self.state.edit_mode == 'H': 
                self.state.edit_mode = 'M'
            elif self.state.edit_mode == 'M': 
                self.state.edit_mode = 'S'
            elif self.state.edit_mode == 'S': 
                self.state.edit_mode = 'H' # Rotace zpět na hodiny
            print(f"Režim změněn na: {self.state.edit_mode}")
            
        else:
            if self.state.edit_mode == 'H':
                self.state.timer_seconds = max(0, self.state.timer_seconds - 3600)
            elif self.state.edit_mode == 'M':
                self.state.timer_seconds = max(0, self.state.timer_seconds - 60)
            elif self.state.edit_mode == 'S':
                self.state.timer_seconds = max(0, self.state.timer_seconds - 1)

        self.update_display()
        self.state.trigger_update()

    def _cb_main(self, channel):
        
        if self.state.alarm_active:
            self.logic.stop_alarm()
        elif self.state.is_timer_running:
            self.state.is_timer_running = False
        else:
            if self.state.timer_seconds > 0:
                self.state.is_timer_running = True
        
        self.update_display()
        self.state.trigger_update()

    def _cb_vol_plus(self, channel):
        self.set_volume_relative(10) # Přidá 10%

    def _cb_vol_minus(self, channel):
        self.set_volume_relative(-10) # Ubere 10%

    
    def update_display(self):
        ts = self.state.timer_seconds

        if self.state.alarm_active:
            self.display.numbers(0, 0, colon=True)
            self.state.trigger_update()
            return

        if ts >= 3600:
            h = ts // 3600
            m = (ts % 3600) // 60
            self.display.numbers(h, m, colon=True)
        else:
            m = ts // 60
            s = ts % 60
            self.display.numbers(m, s, colon=True)

        self.state.trigger_update()

    def set_volume_relative(self, change):
        current = int(self.state.config.get("volume", 50))
        new_vol = max(0, min(100, current + change))

        self.state.config["volume"] = new_vol
        self.state.save_config()
        self._apply_system_volume()
        self.state.trigger_update() # Upozorní webové rozhraní

    def _apply_system_volume(self):
        vol = self.state.config.get("volume", 50)
        
        mixers = ["Master", "PCM", "Digital", "Speaker"]
        for mixer in mixers:
            try:
                subprocess.run(["amixer", "sset", mixer, f"{vol}%"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except:
                pass

    
    def start_loop(self):
        while True:
            time.sleep(1)

    def cleanup(self):
        print("🔌 [HARDWARE] Vypínám GPIO a zhasínám displej...")
        self.display.write([0, 0, 0, 0])
        GPIO.cleanup()
