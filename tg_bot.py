import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from generators.text_gen import PostGenerator
from generators.image_gen import ImageGenerator
import config as conf

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

def _parse_tone_topic(text: str):
    """
    Ожидаем формат: "<тон> | <тема>"
    Если разделителя нет — всё считаем темой, тон по умолчанию "нейтральный".
    """
    if "|" in text:
        tone, topic = [x.strip() for x in text.split("|", 1)]
        if not tone: tone = "нейтральный"
        return tone, topic
    return "нейтральный", text.strip()

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Команды:\n"
        "/post <тон> | <тема>\n"
        "/postimage <тон> | <тема>\n"
        "Пример: /post позитивный и весёлый | Новая коллекция ножей ZeroKnifes"
    )

async def post_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args_text = " ".join(context.args) if context.args else ""
    if not args_text:
        await update.message.reply_text("Формат: /post <тон> | <тема>")
        return

    tone, topic = _parse_tone_topic(args_text)
    try:
        pg = PostGenerator(conf.openai_key, tone=tone, topic=topic)
        post = pg.generate_post()
        await update.message.reply_text(post[:4096])
    except Exception as e:
        logger.exception("post_cmd error")
        await update.message.reply_text(f"Ошибка генерации поста: {e}")

async def postimage_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args_text = " ".join(context.args) if context.args else ""
    if not args_text:
        await update.message.reply_text("Формат: /postimage <тон> | <тема>")
        return

    tone, topic = _parse_tone_topic(args_text)
    try:
        pg = PostGenerator(conf.openai_key, tone=tone, topic=topic)
        post = pg.generate_post()
        img_prompt = pg.generate_post_image_description()

        ig = ImageGenerator(conf.openai_key)
        image_path = ig.generate_image(img_prompt)

        # отправляем сначала пост, потом изображение
        await update.message.reply_text(post[:4096])
        with open(image_path, "rb") as f:
            await update.message.reply_photo(f, caption="Сгенерированное изображение")
    except Exception as e:
        logger.exception("postimage_cmd error")
        await update.message.reply_text(f"Ошибка генерации поста/изображения: {e}")

def main():
    token = conf.telegram_bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
    if not token or token.startswith("PUT_"):
        raise RuntimeError("TELEGRAM_BOT_TOKEN не задан")

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("post", post_cmd))
    app.add_handler(CommandHandler("postimage", postimage_cmd))

    logger.info("Bot started")
    app.run_polling(close_loop=False)

if __name__ == "__main__":
    main()
