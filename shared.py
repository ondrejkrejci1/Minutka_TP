import threading
import json
import os

CONFIG_FILE = "config.json"


class AppState:
    def __init__(self):
        self.timer_seconds = 0
        self.is_timer_running = False
        self.alarm_active = False
        self.stop_alarm_event = threading.Event()
        self.edit_mode = 'M'

        # Výchozí konfigurace
        self.config = {
            "volume": 50,
            "selected_sound": "spotify:track:4cOdK2wGLETKBW3PvgPWqT"
        }

        self.load_config()

        # Callback pro WebSocket (nastaví se ve web.py)
        self.update_callback = None

    def load_config(self):
        """Načte nastavení ze souboru, pokud existuje."""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    self.config.update(data)
            except:
                pass

    def save_config(self):
        """Uloží aktuální nastavení do souboru."""
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.config, f)
        except Exception as e:
            print(f"Chyba při ukládání configu: {e}")

    def trigger_update(self):
        """Zavolá funkci ve web.py, která pošle data přes WebSocket."""
        if self.update_callback:
            try:
                self.update_callback()
            except Exception as e:
                print(f"Chyba update callbacku: {e}")
