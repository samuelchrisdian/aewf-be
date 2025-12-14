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
    from src.api.v1.students import students_bp
    from src.api.v1.classes import classes_bp
    from src.api.v1.teachers import teachers_bp
    from src.api.v1.attendance import attendance_bp
    from src.api.v1.machines import machines_bp
    from src.api.v1.mapping import mapping_bp
    from src.api.v1.dashboard import dashboard_bp
    from src.api.v1.analytics import analytics_bp
    from src.api.v1.risk import risk_bp
    from src.api.v1.models import models_bp
    from src.api.v1.reports import reports_bp
    from src.api.v1.export import export_bp
    from src.api.v1.notifications import notifications_bp
    from src.api.v1.auth import auth_bp
    from src.api.v1.users import users_bp
    from src.api.v1.config import config_bp
    
    app.register_blueprint(api_v1)
    app.register_blueprint(students_bp)
    app.register_blueprint(classes_bp)
    app.register_blueprint(teachers_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(machines_bp)
    app.register_blueprint(mapping_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(risk_bp)
    app.register_blueprint(models_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(export_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(config_bp)

    # Health check
    @app.route('/health')
    def health():
        return {"status": "ok"}

    return app
