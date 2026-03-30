import threading
from shared import AppState
from hardware import HardwareManager
from logic import TimerLogic
from web import create_app

if __name__ == "__main__":
    print("🚀 Startuji Minutku (PC VERZE)...")

    # 1. Vytvoření instancí
    state = AppState()
    logic = TimerLogic(state)
    hw = HardwareManager(state, logic)
    logic.set_hardware(hw)

    # 2. Spuštění logiky a hardwaru na pozadí
    threading.Thread(target=logic.start_loop, daemon=True).start()
    threading.Thread(target=hw.start_loop, daemon=True).start()

    # 3. Spuštění Webu (blokuje hlavní vlákno)
    app, socketio = create_app(state, logic, hw)

    try:
        # allow_unsafe_werkzeug je potřeba pro vývojové prostředí s Websockety
        socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True, use_reloader=False)
    except KeyboardInterrupt:
        print("Ukončuji...")
