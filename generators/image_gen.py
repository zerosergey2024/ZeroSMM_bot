# generators/image_gen.py
import os
import uuid
import base64

import requests
import self
from openai import OpenAI

class ImageGenerator:
    def __init__(self, openai_key, out_dir="generated_images"):
        self.client = OpenAI(api_key=openai_key)
        self.out_dir = out_dir
        os.makedirs(self.out_dir, exist_ok=True)

    def _save_png(self, image_bytes: bytes, filename: str = None) -> str:
        """Сохраняет байты изображения в файл PNG и возвращает путь к нему."""
        name = filename or f"{uuid.uuid4().hex}.png"
        path = os.path.join(self.out_dir, name)
        with open(path, "wb") as f:
            f.write(image_bytes)
        return path

    def generate_image(self, prompt: str, model: str = "dall-e-2", size: str = "1024x1024") -> str:
        """
        Генерирует изображение по промпту.
        По умолчанию используется DALL·E 2.
        DALL·E 3 возвращает URL, DALL·E 2 — base64.
        """
        try:
            response = self.client.images.generate(
                model=model,
                prompt=prompt,
                size=size,
                n=1,
                response_format="b64_json" if model == "dall-e-2" else "url"
            )

            if model == "dall-e-2":
                # base64 → PNG
                b64 = response.data[0].b64_json
                image_bytes = base64.b64decode(b64)
                return self._save_png(image_bytes)
            else:
                # model == "dall-e-3" или другие — URL
                image_url = response.data[0].url
                # Чтобы сохранить по URL, нужно отдельно скачать:
                # import requests
                img_data = requests.get(image_url).content
                return self._save_png(img_data)

        except Exception as e:
            print(f"[ImageGenerator] Ошибка при генерации изображения: {e}")
            return ""

