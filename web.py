from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
import logging
import os
from werkzeug.utils import secure_filename # Nutné pro bezpečné nahrávání


ALLOWED_EXTENSIONS = {'wav', 'mp3', 'ogg', 'm4a', 'flac'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def create_app(state, logic, hardware):
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'tajne'
    app.config['UPLOAD_FOLDER'] = 'sounds' # Složka pro zvuky

    
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
    logging.getLogger('werkzeug').setLevel(logging.ERROR)

    
    def push_update():
        data = {
            "time": state.timer_seconds,
            "running": state.is_timer_running,
            "alarm": state.alarm_active,
            "volume": int(state.config.get("volume", 50)),
            "current_sound": state.config.get("selected_sound", "alarm.wav")
        }
        socketio.emit('status_update', data)

    state.update_callback = push_update

    
    @app.route('/')
    def index(): return render_template('index.html')

    
    @app.route('/api/sounds')
    def get_sounds():
        files = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) if allowed_file(f)]
        return jsonify(files)

    
    @app.route('/api/upload', methods=['POST'])
    def upload_file():
        if 'file' not in request.files: return jsonify({'error': 'No file part'}), 400
        file = request.files['file']
        if file.filename == '': return jsonify({'error': 'No selected file'}), 400
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return jsonify({'success': True, 'filename': filename})
        return jsonify({'error': 'Invalid file type'}), 400

    
    @socketio.on('connect')
    def handle_connect():
        push_update()

    @socketio.on('action')
    def handle_action(data):
        action = data.get('type')
        if state.alarm_active: logic.stop_alarm()
        elif action == 'start': state.is_timer_running = True
        elif action == 'pause': state.is_timer_running = False
        elif action == 'reset': state.is_timer_running = False; state.timer_seconds = 0
        hardware.update_display()

    @socketio.on('set_time')
    def handle_set_time(data):
        if not state.is_timer_running:
            state.timer_seconds = max(0, int(data.get('seconds', 0)))
            hardware.update_display()
            state.trigger_update()

    
    @socketio.on('set_volume')
    def handle_volume(data):
        vol = int(data.get('volume', 50))
        # Rozdíl oproti aktuální, abychom využili relativní změnu v hardware.py
        current = int(state.config.get("volume", 50))
        hardware.set_volume_relative(vol - current)

    
    @socketio.on('set_sound')
    def handle_set_sound(data):
        spotify_link = data.get('spotify_link', '').strip()

        
        if spotify_link:
            if "spotify.com/track/" in spotify_link:
                track_id = spotify_link.split("track/")[1].split("?")[0]
                state.config['selected_sound'] = f"spotify:track:{track_id}"
        elif spotify_link.startswith("spotify:"):
            state.config['selected_sound'] = spotify_link
        else:
            # Jinak uložíme klasický lokální zvuk
            sound = data.get('sound')
            if sound:
                state.config['selected_sound'] = sound
            
        state.save_config()
        state.trigger_update()

    
    @socketio.on('preview_sound')
    def handle_preview(data):
        sound_name = data.get('sound')
        # Logic modul musí mít metodu play_preview
        if logic: logic.play_preview(sound_name)

    return app, socketio
