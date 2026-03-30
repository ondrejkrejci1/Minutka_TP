import threading
from shared import AppState
from hardware import HardwareManager
from logic import TimerLogic
from web import create_app

if __name__ == "__main__":
    print("🚀 Startuji Minutku (PC VERZE)...")

    state = AppState()
    logic = TimerLogic(state)
    hw = HardwareManager(state, logic)
    logic.set_hardware(hw)

    threading.Thread(target=logic.start_loop, daemon=True).start()
    threading.Thread(target=hw.start_loop, daemon=True).start()

    app, socketio = create_app(state, logic, hw)

    try:
        socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True, use_reloader=False)
    except KeyboardInterrupt:
        print("Ukončuji...")
