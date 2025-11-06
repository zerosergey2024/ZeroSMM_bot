# test.py
import os
from dotenv import load_dotenv, find_dotenv
from generators.text_gen import PostGenerator
from generators.image_gen import ImageGenerator
from social_publishers.vk_publisher import VKPublisher

# Загружаем переменные окружения из .env
load_dotenv(find_dotenv() or ".env")

# Переменные окружения
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
VK_API_KEY     = os.getenv("VK_API_KEY")       # токен сообщества (wall, photos)
VK_GROUP_ID    = os.getenv("VK_GROUP_ID")      # без минуса, только цифры
TONE           = os.getenv("TEST_TONE", "позитивный и весёлый")
TOPIC          = os.getenv("TEST_TOPIC", "Новая коллекция кухонных ножей от компании ZeroKnifes")
IMAGE_OUT_DIR  = os.getenv("IMAGE_OUT_DIR", "generated_images")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY не найден. Добавьте его в .env")
if not VK_API_KEY:
    raise RuntimeError("VK_API_KEY не найден. Добавьте его в .env")
if not VK_GROUP_ID or not VK_GROUP_ID.isdigit():
    raise RuntimeError("VK_GROUP_ID не задан или не число. Укажите ID группы без минуса.")

def main():
    # Генерация текста и промпта
    post_gen = PostGenerator(openai_key=OPENAI_API_KEY, tone=TONE, topic=TOPIC)
    content = post_gen.generate_post()
    image_prompt = post_gen.generate_post_image_description()

    # Генерация изображения
    img_gen = ImageGenerator(openai_key=OPENAI_API_KEY, out_dir=IMAGE_OUT_DIR)
    image_path = img_gen.generate_image(image_prompt)

    # Публикация в ВКонтакте
    vk_pub = VKPublisher(vk_api_key=VK_API_KEY, group_id=int(VK_GROUP_ID))
    pub_result = vk_pub.publish_post(content, image_path=image_path)

    print("=== СГЕНЕРИРОВАННЫЙ ПОСТ ===")
    print(content)
    print("\n=== ПУТЬ К ИЗОБРАЖЕНИЮ ===")
    print(image_path)
    print("\n=== ССЫЛКА НА ПОСТ ===")
    print(pub_result.get("permalink"))

if __name__ == "__main__":
    main()




