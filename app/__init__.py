from flask import Flask
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

from app.config import TestConfig, DeploymentConfig

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'main.landing'

csrf = CSRFProtect()
login_manager.login_message = 'Please log in to access your dashboard.'
login_manager.login_message_category = 'warning'

def create_app(config):
    app = Flask(__name__)
    app.config.from_object(config)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    from app.blueprints import main
    app.register_blueprint(main)

    return app

from app.models import User

@login_manager.user_loader
def load_user(email):
    return db.session.get(User, email)

from app import models