import os
import sys
import time
import socket
import threading
from datetime import datetime
from flask import Flask
from flask_cors import CORS
from config import config


def _cleanup_old_artifacts(base_dir, max_age_seconds):
    """Delete old report/chart artifacts older than max_age_seconds."""
    now_ts = time.time()
    removed = 0
    artifact_exts = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.pdf', '.html', '.md', '.csv', '.xlsx'}

    for root, _, files in os.walk(base_dir):
        for name in files:
            ext = os.path.splitext(name)[1].lower()
            if ext not in artifact_exts:
                continue

            path = os.path.join(root, name)
            try:
                age_seconds = now_ts - os.path.getmtime(path)
                if age_seconds > max_age_seconds:
                    os.remove(path)
                    removed += 1
            except Exception:
                continue

    return removed


def _start_cleanup_worker(app):
    """Start a small background cleanup worker for generated artifacts."""
    if not app.config.get('CLEANUP_ENABLED', True):
        print("🧹 Artifact cleanup disabled")
        return

    interval_minutes = max(5, int(app.config.get('CLEANUP_INTERVAL_MINUTES', 60)))
    max_age_hours = max(1, int(app.config.get('CLEANUP_MAX_AGE_HOURS', 48)))
    max_age_seconds = max_age_hours * 3600

    backend_reports = os.path.join(app.root_path, 'reports')
    team4_reports = os.path.normpath(os.path.join(app.root_path, '..', '..', 'Team4_module', 'reports'))
    targets = [backend_reports, team4_reports]

    def worker():
        while True:
            total_removed = 0
            for target in targets:
                if os.path.isdir(target):
                    total_removed += _cleanup_old_artifacts(target, max_age_seconds)
            if total_removed > 0:
                print(f"🧹 Cleanup removed {total_removed} old artifact file(s) at {datetime.now().isoformat()}")
            time.sleep(interval_minutes * 60)

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    print(f"🧹 Artifact cleanup worker started (max_age={max_age_hours}h, interval={interval_minutes}m)")


def _parse_bool_env(var_name, default=False):
    """Parse boolean environment variable with safe defaults."""
    raw = os.getenv(var_name)
    if raw is None:
        return bool(default)
    return str(raw).strip().lower() in {'1', 'true', 'yes', 'on'}


def _pick_available_port(host, preferred_port, max_attempts=15):
    """Pick first available TCP port, starting from preferred_port."""
    for offset in range(max_attempts):
        candidate = int(preferred_port) + offset
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind((host, candidate))
            return candidate
        except OSError:
            continue
    return None

def create_app(config_name='development'):
    """Application factory"""
    import os

    # Determine frontend folder path
    frontend_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend'))

    # Create Flask app
    app = Flask(__name__, static_folder=frontend_folder, static_url_path='')

    @app.route('/')
    def serve_index():
        return app.send_static_file('index.html')
    app.config.from_object(config[config_name])
    
    # Configure CORS for credentialed browser sessions.
    cors_origins = app.config.get('CORS_ALLOWED_ORIGINS', [])
    supports_credentials = bool(app.config.get('CORS_SUPPORTS_CREDENTIALS', True))

    if supports_credentials:
        cors_origins = [origin for origin in cors_origins if origin != '*']

    if not cors_origins:
        cors_origins = ['http://localhost:3000']

    CORS(
        app,
        resources={
            r"/api/*": {
                'origins': cors_origins,
                'supports_credentials': supports_credentials,
                'allow_headers': ['Content-Type', 'Authorization'],
                'methods': ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS']
            }
        },
        supports_credentials=supports_credentials
    )
    
    # Session configuration
    app.config['PERMANENT_SESSION_LIFETIME'] = config[config_name].PERMANENT_SESSION_LIFETIME
    
    # Register blueprints
    from api.auth_routes import auth_bp
    from api.analysis_routes import analysis_bp, initialize_services
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(analysis_bp)
    
    # Initialize analysis services
    models_path = app.config['MODELS_PATH']
    gemini_api_key = app.config.get('GEMINI_API_KEY', '')
    mapper_threshold = app.config.get('COLUMN_MAPPER_CONFIDENCE_THRESHOLD', 0.55)
    initialize_services(models_path, gemini_api_key, mapper_confidence_threshold=mapper_threshold)

    # Start lightweight artifact cleanup worker once in reloader child process.
    if (not app.debug) or (os.environ.get('WERKZEUG_RUN_MAIN') == 'true'):
        _start_cleanup_worker(app)
    
    # Health check endpoint
    @app.route('/api/health', methods=['GET'])
    def health_check():
        return {
            'status': 'healthy',
            'service': 'Nexus AI Analytics Backend',
            'version': '1.0.0'
        }, 200
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        return {
            'success': False,
            'message': 'Endpoint not found'
        }, 404
    
    @app.errorhandler(500)
    def internal_error(e):
        return {
            'success': False,
            'message': 'Internal server error'
        }, 500
    
    print("✅ Flask app initialized")
    print(f"📁 Models path: {models_path}")
    print(f"🔑 Gemini API configured: {'Yes' if gemini_api_key else 'No'}")
    
    return app


if __name__ == '__main__':
    config_name = os.getenv('FLASK_ENV', 'development')
    if config_name not in config:
        config_name = 'development'

    app = create_app(config_name)

    host = os.getenv('SERVER_HOST', '0.0.0.0')
    requested_port = int(os.getenv('SERVER_PORT', '5000'))
    debug_mode = _parse_bool_env('FLASK_DEBUG', default=app.debug)
    use_reloader = _parse_bool_env('FLASK_USE_RELOADER', default=(debug_mode and os.name != 'nt'))

    selected_port = _pick_available_port(host, requested_port)
    if selected_port is None:
        raise RuntimeError(f"No free port found near {requested_port}. Set SERVER_PORT in .env to an open port.")

    if selected_port != requested_port:
        print(f"⚠️ Port {requested_port} is in use, switching to {selected_port}.")

    # With reloader disabled in debug mode (recommended on Windows), start cleanup worker in the single process.
    if (not use_reloader) and app.debug:
        _start_cleanup_worker(app)
    
    print("\n" + "="*50)
    print("🚀 Nexus AI Backend Starting...")
    print("="*50)
    print(f"Environment: {config_name}")
    print(f"Debug Mode: {debug_mode}")
    print(f"Use Reloader: {use_reloader}")
    print(f"Upload Folder: {app.config['UPLOAD_FOLDER']}")
    print(f"Server URL: http://127.0.0.1:{selected_port}")
    print("="*50 + "\n")
    
    app.run(
        host=host,
        port=selected_port,
        debug=debug_mode,
        use_reloader=use_reloader
    )
