from flask import Flask

def create_app():
    app = Flask(__name__)

    from .routes.patients_routes import bp as patients_bp
    from .routes.appointments_routes import bp as appointments_bp
    from .routes.auth_routes import bp as auth_bp
    from .routes.site_routes import site_bp
    from .routes.chatbot_routes import bp as chatbot_bp


    app.register_blueprint(patients_bp, url_prefix="/api/patients")
    app.register_blueprint(appointments_bp, url_prefix="/api/appointments")
    app.register_blueprint(chatbot_bp, url_prefix="/chatbot") 
    app.register_blueprint(auth_bp)
    app.register_blueprint(site_bp)
    
    return app
