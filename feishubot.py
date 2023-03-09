# Author: Dragon
# Python: 3.9
# Created at 2022/12/29 21:38
# Edit with VS Code
# Filename: feishubot.py
# Description: Feishu bot to send message to user
# Reference: https://open.feishu.cn/document/ukTMukTMukTM/uQjN3QjL0YzN04CN2cDN

import json
import os
from datetime import datetime, timedelta
from io import BufferedReader
from typing import Any, Literal, TypeAlias

try:
    import cv2
except ImportError:
    cv2 = None

import requests
from loguru import logger
from requests_toolbelt import MultipartEncoder

TENANT_TOKEN_API = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
USER_ID_API = "https://open.feishu.cn/open-apis/contact/v3/users/batch_get_id"
MESSAGE_API = "https://open.feishu.cn/open-apis/im/v1/messages"
UPLOAD_IMAGE_API = "https://open.feishu.cn/open-apis/im/v1/images"
UPLOAD_FILE_API = "https://open.feishu.cn/open-apis/im/v1/files"

FEISHU_APP_ID = os.getenv("FEISHU_APP_ID")
FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET")
# if open_id is not set, use phone or email to query open_id, prefer to use phone
FEISHU_PHONE = os.getenv("FEISHU_PHONE")
FEISHU_EMAIL = os.getenv("FEISHU_EMAIL")
# open_id of user who will receive the message
FEISHU_OPEN_ID = os.getenv("FEISHU_OPEN_ID")

ENABLE = True if all(
    (FEISHU_APP_ID, FEISHU_APP_SECRET, any((FEISHU_OPEN_ID, FEISHU_PHONE, FEISHU_EMAIL)))
) else False

if not ENABLE:
    logger.warning(
        f"{FEISHU_APP_ID=} or {FEISHU_APP_SECRET=} is not set, feishu bot is unavailable."
    )

FileStream: TypeAlias = BufferedReader | bytes | bytearray
File: TypeAlias = str | FileStream
FileType: TypeAlias = Literal["opus", "mp4", "pdf", "doc", "xls", "ppt", "stream"]
MsgType: TypeAlias = Literal["text", "image", "audio", "media", "file", "interactive"]


def _post(url: str, token: str = "", **kwargs) -> dict:
    if "headers" not in kwargs:
        kwargs["headers"] = {"Content-Type": "application/json"}
    if token:
        kwargs["headers"]["authorization"] = f"Bearer {token}"
    resp = requests.post(url, **kwargs).json()
    if resp["code"]:
        raise ValueError(f"Message failed: {resp['msg']}")
    return resp


def get_open_id(token: str) -> str:
    if not any((FEISHU_PHONE, FEISHU_EMAIL)):
        raise ValueError(
            "To query open_id when FEISHU_OPEN_ID isn't set, FEISHU_PHONE "
            "or FEISHU_EMAIL must be set with your phone or email."
        )
    body = {}
    if FEISHU_PHONE:
        body["mobiles"] = [FEISHU_PHONE]
    if FEISHU_EMAIL:
        body["emails"] = [FEISHU_EMAIL]
    resp = _post(USER_ID_API, token, params={"user_id_type": "open_id"}, json=body)
    for user in resp["data"]["user_list"]:
        if "user_id" in user:
            return user["user_id"]
    raise ValueError(f"Query open_id failed: no user_id found. {body=}")


class TenantToken:
    def __init__(self) -> None:
        self.token = ""
        self.expire_at = datetime.now()

    def request_token(self):
        resp = _post(
            TENANT_TOKEN_API, json={
                "app_id": FEISHU_APP_ID,
                "app_secret": FEISHU_APP_SECRET
            }
        )
        self.token = resp["tenant_access_token"]
        self.expire_at = timedelta(seconds=resp["expire"]) + datetime.now()

    def __get__(self, instance, owner) -> str:
        if not self.token or self.expire_at < datetime.now():
            self.request_token()
        return self.token

    def __set__(self, instance, value):
        raise AttributeError("TenantToken is read-only")


class FeiShuBot:
    token = TenantToken()

    def __init__(self) -> None:
        if not ENABLE:
            return
        self.user_id = FEISHU_OPEN_ID or get_open_id(self.token)

    def __getattribute__(self, __name: str) -> Any:
        """Disable all methods when enable is False"""
        if ENABLE:
            return super().__getattribute__(__name)
        if __name == "token":
            return ""

        def wrap(*_, **__):
            logger.warning(f"FeiShuBot is disabled, {__name} is unavailable.")

        return wrap

    def _send_message(self, msg_type: MsgType, content: dict) -> dict:
        # TODO: message card
        return _post(
            MESSAGE_API,
            self.token,
            params={"receive_id_type": "open_id"},
            json={
                "receive_id": self.user_id,
                "msg_type": msg_type,
                "content": json.dumps(content)
            }
        )

    def _post_file(
        self, file_type: Literal["image"] | FileType, file: File, filename: str = ""
    ) -> dict:
        if not filename:
            filename = os.path.basename(file.name) if isinstance(file, BufferedReader) else "file"
        if file_type == "image":
            url = UPLOAD_IMAGE_API
            fields = {"image_type": "message", "image": (filename, file)}
        else:
            url = UPLOAD_FILE_API
            fields = {"file_type": file_type, "file": (filename, file), "filename": filename}
        return _post(
            url,
            self.token,
            data=(form := MultipartEncoder(fields)),
            headers={"Content-Type": form.content_type},
        )["data"]

    def send_text(self, msg: str) -> dict:
        """send text message

        Args:
            msg(str): message to be sent
        """
        return self._send_message("text", {"text": msg})

    def send_image(self, image: FileStream) -> dict:
        """Send image message

        Args:
            image(FileStream): image to be sent, must be a file opened in binary mode or bytes
        """
        return self._send_message("image", self._post_file("image", image))

    def send_file(self, file: File, file_type: FileType, filename: str = "") -> dict:
        """Send file message

        Args:
            file(File): file to be sent, must be file opened in binary mode, str or bytes
            file_type (str): One of "opus", "mp4", "pdf", "doc", "xls", "ppt", "stream"
        """
        return self._send_message("file", self._post_file(file_type, file, filename))

    def send_audio(self, audio: FileStream) -> dict:
        """Send audio message, audio must be opus format. For other audio type, 
        refer to the following command to convert:

        `ffmpeg -i SourceFile.mp3 -acodec libopus -ac 1 -ar 16000 TargetFile.opus`

        Args:
            audio(FileStream): audio to be sent, must be opened in binary mode
        """

        return self._send_message("audio", self._post_file("opus", audio))

    def send_media(self, media: FileStream, cover: FileStream | bytes = b"") -> dict:
        """Send media message, media must be mp4 format.

        Args:
            media(FileStream): media to be sent, must be opened in binary mode
            cover(FileStream | bytes): cover for media, default is first frame of media
            filename(str): filename of the audio, default is empty
        """
        if cv2 is None:
            logger.warning("opencv-python is not installed, send_media is unavailable")
            return {}
        if not cover:
            if not isinstance(media, BufferedReader):
                raise ValueError("Cover must be set when media is not an opened file")
            _, frame = cv2.VideoCapture(media.name).read()
            _, _cover = cv2.imencode(".jpg", frame)
            cover = _cover.tobytes()
        content = self._post_file("mp4", media) | self._post_file("image", cover)
        return self._send_message("media", content)

    def send_card(self, message: str, header: str = ""):
        """Send feishu card message, only support markdown format now.

        Refer to https://open.feishu.cn/document/ukTMukTMukTM/uADOwUjLwgDM14CM4ATN

        Args:
            message(str): markdown message to be sent
            header(str): card header, default is empty
        """

        content = {
            "config": {"wide_screen_mode": True},
            "elements": [{"tag": "markdown", "content": message}],
        }
        if header:
            content["header"] = {
                "title": {
                    "tag": "plain_text",
                    "content": header
                },
                "template": "blue"
            }
        self._send_message("interactive", content)


bot = FeiShuBot()
