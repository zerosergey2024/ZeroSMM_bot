# app/smm.py
import os
from flask import Blueprint, render_template, request, flash
from .auth import login_required
from generators.text_gen import PostGenerator
from generators.image_gen import ImageGenerator
from social_publishers.vk_publisher import VKPublisher
from sheets_reader import read_leads, compute_summary


bp = Blueprint("smm", __name__)  # если уже есть, повторно не объявляй

@bp.route("/")
@login_required
def dashboard():
    return render_template("dashboard.html")

@bp.route("/post-generator", methods=["GET", "POST"])
@login_required
def post_generator():
    result_text = None
    image_url = None
    permalink = None
    tone = request.form.get("tone", "нейтральный")
    topic = request.form.get("topic", "")

    if request.method == "POST":
        gen_image = request.form.get("gen_image") == "on"
        autopost_vk = request.form.get("autopost_vk") == "on"

        # 1) Генерация текста (+ промпт для изображения)
        key = os.getenv("OPENAI_API_KEY", "")
        if not key:
            result_text = "OPENAI_API_KEY не задан в .env"
        else:
            pg = PostGenerator(openai_key=key, tone=tone, topic=topic)
            result_text = pg.generate_post()
            img_prompt = pg.generate_post_image_description() if gen_image else None

            # 2) Картинка (если чекбокс включён)
            image_path = None
            if gen_image and img_prompt:
                # кладём в статическую папку, чтобы можно было отдать через Flask
                out_dir = os.path.join("app", "static", "generated_images")
                os.makedirs(out_dir, exist_ok=True)
                ig = ImageGenerator(openai_key=key, out_dir=out_dir)
                image_path = ig.generate_image(img_prompt)
                # превратим файловый путь в URL для тега <img>
                # image_path, например: "app/static/generated_images/xxx.png"
                rel = image_path.split("app/static/", 1)[-1]
                image_url = f"/static/{rel}"

            # 3) Автопубликация в VK (если чекбокс включён)
            if autopost_vk:
                vk_key = os.getenv("VK_API_KEY")
                vk_group = os.getenv("VK_GROUP_ID")
                if not vk_key or not vk_group:
                    permalink = "VK_API_KEY/VK_GROUP_ID не заданы в .env — публикация пропущена."
                else:
                    try:
                        pub = VKPublisher(vk_api_key=vk_key, group_id=int(vk_group))
                        pub_res = pub.publish_post(result_text, image_path=image_path)
                        permalink = pub_res.get("permalink") or "Опубликовано (ссылку VK не вернул)."
                    except Exception as e:
                        permalink = f"Ошибка публикации VK: {e}"

    return render_template(
        "postgen/generator.html",
        tone=tone,
        topic=topic,
        result_text=result_text,
        image_url=image_url,
        permalink=permalink,
    )
@bp.route("/stats", methods=["GET"])
@login_required
def stats():
    # Параметры фильтра: даты (необязательно)
    date_from = request.args.get("from", "").strip() or None
    date_to   = request.args.get("to", "").strip() or None

    rows = []
    summary = None
    try:
        rows = read_leads(date_from, date_to)
        summary = compute_summary(rows)
    except Exception as e:
        flash(f"Ошибка чтения Google Sheets: {e}", "danger")

    # чтобы таблица не была слишком большой при первом открытии — покажем первые 200 строк
    MAX_ROWS = 200
    rows_view = rows[:MAX_ROWS]

    # набор колонок для таблицы: базовые + заглушки (могут быть пустыми сейчас)
    columns = [
        ("created_at",  "Создано"),
        ("client_name", "Имя"),
        ("client_phone","Телефон"),
        ("service",     "Услуга"),
        ("comment",     "Комментарий"),
        ("source",      "Источник"),
        # заглушки на будущее:
        ("manager",     "Менеджер"),
        ("city",        "Город"),
        ("lead_status", "Статус"),
        ("price",       "Цена"),
    ]

    return render_template("stats/index.html",
                           date_from=date_from or "",
                           date_to=date_to or "",
                           rows=rows_view,
                           columns=columns,
                           summary=summary,
                           total_all=len(rows),
                           max_rows=MAX_ROWS)
