# generators/text_gen.py
from openai import OpenAI, api_key


class PostGenerator:
    def __init__(self, openai_key, tone, topic):
        self.client = OpenAI(api_key=api_key)
        self.tone = tone
        self.topic = topic

    def generate_post(self):
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": f"Ты копирайтер. Напиши пост в {self.tone} тоне."},
                {"role": "user", "content": f"Создай пост на тему: {self.topic}"}
            ],
            temperature=0.7,
        )
        return response.choices[0].message.content

    def generate_post_image_description(self):
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Ты создаешь описания изображений для генераторов."},
                {"role": "user", "content": f"Опиши изображение для поста на тему: {self.topic}. Тон: {self.tone}"}
            ],
            temperature=0.7,
        )
        return response.choices[0].message.content


