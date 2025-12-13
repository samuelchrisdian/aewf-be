from flask import Flask
from .config import config
from .extensions import db, migrate
from .errors import register_error_handlers
import os

def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG', 'default')

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)

    # Register error handlers
    register_error_handlers(app)

    # Register blueprints
    from src.api.v1.routes import api_v1
    app.register_blueprint(api_v1)

    # Health check
    @app.route('/health')
    def health():
        return {"status": "ok"}

    return app
