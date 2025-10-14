from flask import Flask
from flask_login import LoginManager
from config import Config
from db import db
from auth import auth_bp
from routes import routes
from models import User
import os

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login = LoginManager(app)
    login.login_view = 'auth.login'

    @login.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    app.register_blueprint(auth_bp)
    app.register_blueprint(routes)

    with app.app_context():
        db.create_all()

    return app

if __name__=='__main__':
    create_app().run(debug=False)
