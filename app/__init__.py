from flask import Flask

def create_app():
    app = Flask(__name__)

    from app.routes.auth_routes import auth_bp
    app.register_blueprint(auth_bp)

    return app