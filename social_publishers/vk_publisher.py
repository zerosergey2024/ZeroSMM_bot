# social_publishers/vk_publisher.py
import os
import time
import json
from typing import Iterable, List, Optional, Tuple, Union

import requests
from requests import Session
from requests.exceptions import RequestException


class VKAPIError(RuntimeError):
    pass


class VKPublisher:
    def __init__(
        self,
        vk_api_key: str,
        group_id: int,
        api_version: str = "5.199",
        timeout: int = 30,
        retries: int = 3,
        retry_backoff_sec: float = 1.5,
        session: Optional[Session] = None,
    ):
        """
        :param vk_api_key: токен доступа с правами wall, photos, groups
        :param group_id: ID группы без минуса (например 123456)
        :param api_version: версия VK API
        :param timeout: таймаут HTTP запросов (сек)
        :param retries: кол-во повторов при сетевых ошибках
        :param retry_backoff_sec: множитель бэкоффа между ретраями
        :param session: опционально — внешний requests.Session
        """
        self.vk_api_key = vk_api_key
        self.group_id = int(group_id)
        self.api_version = api_version
        self.timeout = timeout
        self.retries = retries
        self.retry_backoff_sec = retry_backoff_sec
        self.sess = session or requests.Session()

    # ----------------------- low-level helpers -----------------------

    def _get(self, url: str, params: dict) -> dict:
        attempt = 0
        while True:
            try:
                resp = self.sess.get(url, params=params, timeout=self.timeout)
                resp.raise_for_status()
                data = resp.json()
                if "error" in data:
                    # Поднимем читабельную ошибку
                    err = data["error"]
                    raise VKAPIError(f"{err.get('error_code')}: {err.get('error_msg')}")
                return data["response"]
            except (RequestException, VKAPIError) as e:
                attempt += 1
                if attempt > self.retries:
                    raise VKAPIError(f"VK GET failed after {self.retries} retries: {e}")
                time.sleep(self.retry_backoff_sec * attempt)

    def _post(self, url: str, params: dict, files: Optional[dict] = None) -> dict:
        attempt = 0
        while True:
            try:
                resp = self.sess.post(url, params=params, files=files, timeout=self.timeout)
                resp.raise_for_status()
                data = resp.json()
                if "error" in data:
                    err = data["error"]
                    raise VKAPIError(f"{err.get('error_code')}: {err.get('error_msg')}")
                return data["response"]
            except (RequestException, VKAPIError) as e:
                attempt += 1
                if attempt > self.retries:
                    raise VKAPIError(f"VK POST failed after {self.retries} retries: {e}")
                time.sleep(self.retry_backoff_sec * attempt)

    # ----------------------- photos helpers -----------------------

    def _get_wall_upload_url(self) -> str:
        resp = self._get(
            "https://api.vk.com/method/photos.getWallUploadServer",
            {
                "access_token": self.vk_api_key,
                "v": self.api_version,
                "group_id": self.group_id,
            },
        )
        return resp["upload_url"]

    def _upload_single_photo(self, image_path: str) -> Tuple[int, int]:
        """
        Загружает одну картинку и возвращает (owner_id, media_id).
        """
        if not os.path.isfile(image_path):
            raise VKAPIError(f"Image file not found: {image_path}")

        upload_url = self._get_wall_upload_url()

        with open(image_path, "rb") as f:
            upload_resp = self._post(
                upload_url,
                params={},  # у upload_url нет обязательных query-параметров
                files={"photo": f},
            )

        # upload_resp — это не финальный 'response' VK, а промежуточный JSON со строковыми полями
        # но мы вызвали _post, который ожидает 'response'; потому для upload_url делаем прямой requests.post выше.
        # Поэтому обойдём _post и сделаем отдельный raw POST для upload_url:
        # (исправление) — переопределим логику выше

    def upload_photo(self, image_path: str) -> str:
        """
        Загрузка одной картинки и возврат attachment вида 'photo{owner_id}_{media_id}'
        """
        upload_url = self._get_wall_upload_url()

        # Для upload_url нужно сделать "сырой" POST без проверки VK-ошибки (там её нет),
        # затем этот ответ передать в photos.saveWallPhoto.
        with open(image_path, "rb") as f:
            raw = self.sess.post(upload_url, files={"photo": f}, timeout=self.timeout)
            raw.raise_for_status()
            up = raw.json()

        if "photo" not in up or "server" not in up or "hash" not in up:
            raise VKAPIError(f"Unexpected upload response: {json.dumps(up, ensure_ascii=False)}")

        saved = self._get(
            "https://api.vk.com/method/photos.saveWallPhoto",
            {
                "access_token": self.vk_api_key,
                "v": self.api_version,
                "group_id": self.group_id,
                "photo": up["photo"],
                "server": up["server"],
                "hash": up["hash"],
            },
        )

        item = saved[0]
        owner_id = item["owner_id"]
        media_id = item["id"]
        return f"photo{owner_id}_{media_id}"

    def upload_photos(self, image_paths: Iterable[str]) -> List[str]:
        """
        Загрузка нескольких картинок, возвращает список attachment-строк.
        """
        attachments = []
        for p in image_paths:
            attachments.append(self.upload_photo(p))
        return attachments

    # ----------------------- wall.post -----------------------

    def publish_post(
        self,
        content: str,
        image_path: Optional[Union[str, Iterable[str]]] = None,
        from_group: int = 1,
        signed: int = 0,
        **extra_wall_params,
    ) -> dict:
        """
        Публикует пост на стене сообщества.

        :param content: текст поста
        :param image_path: путь к файлу или список путей
        :param from_group: 1 — публиковать от имени сообщества
        :param signed: 1 — подписывать автора (для от имени соо обычно 0)
        :param extra_wall_params: любые доп. параметры wall.post (attachments, publish_date и т.п.)
        :return: словарь с 'post_id', 'owner_id', 'permalink' и полным ответом VK
        """
        attachments_str = None

        if image_path:
            if isinstance(image_path, (list, tuple, set)):
                att = self.upload_photos(image_path)
            else:
                att = [self.upload_photo(str(image_path))]
            attachments_str = ",".join(att)

        # Параметры для wall.post
        params = {
            "access_token": self.vk_api_key,
            "v": self.api_version,
            "owner_id": -self.group_id,  # для группы — отрицательное значение
            "from_group": from_group,
            "signed": signed,
            "message": content or "",
            **extra_wall_params,
        }
        if attachments_str:
            # Если пользователь уже передал attachments в extra_wall_params — объединим
            if "attachments" in params and params["attachments"]:
                params["attachments"] = f"{params['attachments']},{attachments_str}"
            else:
                params["attachments"] = attachments_str

        resp = self._post("https://api.vk.com/method/wall.post", params=params)

        post_id = resp.get("post_id")
        owner_id = -self.group_id
        permalink = f"https://vk.com/wall{owner_id}_{post_id}"

        return {
            "post_id": post_id,
            "owner_id": owner_id,
            "permalink": permalink,
            "raw": resp,
        }