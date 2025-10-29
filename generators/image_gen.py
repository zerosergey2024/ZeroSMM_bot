# generators/image_gen.py
import base64
import os
import uuid
from openai import OpenAI
import requests  # если вдруг захочешь качать по URL

class ImageGenerator:
    def __init__(self, openai_key, out_dir="generated_images"):
        self.client = OpenAI(api_key=openai_key)
        self.out_dir = out_dir
        os.makedirs(self.out_dir, exist_ok=True)

    def _save_png(self, image_bytes, filename=None):
        name = filename or f"{uuid.uuid4().hex}.png"
        path = os.path.join(self.out_dir, name)
        with open(path, "wb") as f:
            f.write(image_bytes)
        return path

    def generate_image(self, prompt, model="gpt-image-1", size="1024x1024"):
        # Для gpt-image-1 API ВСЕГДА отдаёт base64
        if model == "gpt-image-1":
            resp = self.client.images.generate(
                model=model,
                prompt=prompt,
                size=size,
                n=1,
            )
            b64 = resp.data[0].b64_json
            return self._save_png(base64.b64decode(b64))
