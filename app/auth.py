from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.models import create_user, verify_user, get_user_by_email

bp = Blueprint("auth", __name__)

def login_required(view):
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)
    wrapper.__name__ = view.__name__
    return wrapper

@bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email","").strip()
        name = request.form.get("name","").strip()
        password = request.form.get("password","")
        if not email or not password:
            flash("Email и пароль обязательны", "danger")
        elif get_user_by_email(email):
            flash("Пользователь уже существует", "danger")
        else:
            create_user(email, name, password)
            flash("Регистрация успешна. Войдите.", "success")
            return redirect(url_for("auth.login"))
    return render_template("auth/register.html")

@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email","")
        password = request.form.get("password","")
        user = verify_user(email, password)
        if user:
            session["user_id"] = user["id"]
            session["user_name"] = user["name"] or user["email"]
            return redirect(url_for("smm.dashboard"))
        else:
            flash("Неверные учётные данные", "danger")
    return render_template("auth/login.html")

@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
