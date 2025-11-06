import os
from flask import Flask
from dotenv import load_dotenv

load_dotenv()

def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "change-me")

    # Инициализируем БД (простая sqlite через наши функции)
    from .models import init_db
    init_db()

    # Регистрируем blueprints
    from .auth import bp as auth_bp
    from .smm import bp as smm_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(smm_bp)

    @app.get("/health")
    def health():
        return {"ok": True}

    return app
