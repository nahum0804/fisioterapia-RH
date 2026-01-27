from flask import Flask, request
from flask_cors import CORS
import os

from .extensions import db


def create_app():
    app = Flask(__name__)

    # --- DB ---
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        f"postgresql+psycopg2://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
        f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    # evita redirect 308 por slash
    app.url_map.strict_slashes = False

    # --- Preflight (por si acaso) ---
    @app.before_request
    def handle_preflight():
        if request.method == "OPTIONS":
            return "", 200

    # --- CORS ---
    CORS(
        app,
        resources={
            r"/*": {
                "origins": [
                    "http://localhost:5173",
                    "http://127.0.0.1:5173",
                    "https://statuesque-naiad-e59157.netlify.app/",
                ]
            }
        },
        supports_credentials=True,
        allow_headers=["Content-Type", "Authorization"],
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    )

    # --- Blueprints (SIN duplicar imports) ---
    from .routes.patients_routes import bp as patients_bp
    from .routes.appointments_routes import bp as appointments_bp
    from .routes.planner_routes import bp as planner_bp
    from .routes.users_routes import bp as users_bp
    from .routes.chatbot_routes import bp as chatbot_bp
    from .routes.auth_routes import bp as auth_bp
    from .routes.site_routes import site_bp
    from .routes.record_routes import bp as records_bp

    # --- Register ---
    app.register_blueprint(patients_bp, url_prefix="/api/patients")
    app.register_blueprint(appointments_bp, url_prefix="/api/appointments")
    app.register_blueprint(planner_bp, url_prefix="/api/planner")
    app.register_blueprint(users_bp, url_prefix="/api/users")
    app.register_blueprint(records_bp, url_prefix="/api/records")

    # Nota: define tu chatbot como /api/chatbot o /chatbot, pero NO ambos.
    app.register_blueprint(chatbot_bp, url_prefix="/chatbot")

    # auth/site normalmente ya traen sus rutas internas
    app.register_blueprint(auth_bp)
    app.register_blueprint(site_bp)

    return app
