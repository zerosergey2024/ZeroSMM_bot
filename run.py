# run.py — входная точка для WSGI/локального запуска
from app import create_app

app = create_app()

if __name__ == "__main__":
    # локальный запуск (на PA это не используется)
    app.run(host="127.0.0.1", port=5000, debug=False)
