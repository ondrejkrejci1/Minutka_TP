import time
import threading
import os
import subprocess
import spotipy
from spotipy.oauth2 import SpotifyOAuth


SOUNDS_DIR = "sounds"

class TimerLogic:
    def __init__(self, state):
        self.state = state
        self.hw = None

        
        self.sp = None
        self.spotify_was_playing = False # Pamatuje si, jestli jsme Spotify pauzli my
        
        try:
            self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
                client_id='b83fc018517a4c33aa267c181b72a048',
                client_secret='ee70194def7b4114a40f0de4e3514f37',
                redirect_uri='http://127.0.0.1:8080',
                scope="user-modify-playback-state user-read-playback-state",
                open_browser=False
            ))
        except Exception as e:
            print(f"⚠️ [SPOTIFY] Nelze se připojit pro dálkové ovládání: {e}")

    def set_hardware(self, hw):
        self.hw = hw

    def play_sound_file(self, filename):
        path = os.path.join(SOUNDS_DIR, filename)
        if not os.path.exists(path):
            print(f"❌ [AUDIO CHYBA] Soubor nenalezen: {path}")
            return
        cmd = ["ffplay", "-nodisp", "-autoexit", "-v", "0", path]
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            print(f"🎵 [PC SIMULACE ZVUKU] Přehrávám: {filename}")
        except Exception as e: pass

    def play_preview(self, sound_name):
        threading.Thread(target=self.play_sound_file, args=(sound_name,), daemon=True).start()

    def alarm_loop(self):
        print("🔔 [LOGIKA] ALARM START")
        start_time = time.time()
        while not self.state.stop_alarm_event.is_set():
            current_sound = self.state.config.get("selected_sound", "alarm.wav")
            self.play_sound_file(current_sound)
            elapsed = time.time() - start_time
            wait = 1.0 if elapsed < 10 else (0.5 if elapsed < 20 else 0.1)
            for _ in range(int(wait * 10)):
                if self.state.stop_alarm_event.is_set(): break
                time.sleep(0.1)
        print("🔕 [LOGIKA] ALARM STOP")

    def start_alarm(self):
        if not self.state.alarm_active:
            self.state.alarm_active = True
            self.state.stop_alarm_event.clear()

            
            if self.sp:
                try:
                    playback = self.sp.current_playback()
                    
                    if playback and playback['is_playing']:
                        self.sp.pause_playback()
                        self.spotify_was_playing = True
                        print("⏸️ [SPOTIFY] Hudba pozastavena kvůli alarmu.")
                except Exception as e:
                    print(f"⚠️ [SPOTIFY] Chyba pauzy: {e}")
            
            threading.Thread(target=self.alarm_loop, daemon=True).start()
            self.state.trigger_update()

    def stop_alarm(self):
        self.state.alarm_active = False
        self.state.stop_alarm_event.set()

        
        if self.sp and self.spotify_was_playing:
            try:
                self.sp.start_playback()
                self.spotify_was_playing = False
                print("▶️ [SPOTIFY] Pokračuji v přehrávání hudby.")
            except Exception as e:
                print(f"⚠️ [SPOTIFY] Chyba obnovení: {e}")
                
        if self.hw: self.hw.update_display()
        self.state.trigger_update()

    def start_loop(self):
        while True:
            if self.state.is_timer_running and self.state.timer_seconds > 0:
                time.sleep(1)
                if not self.state.is_timer_running: continue
                if self.state.timer_seconds > 0: self.state.timer_seconds -= 1
                if self.hw: self.hw.update_display()
                if self.state.timer_seconds == 0:
                    self.state.is_timer_running = False
                    self.start_alarm()
            else:
                time.sleep(0.1)
