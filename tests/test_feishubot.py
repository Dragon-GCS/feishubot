import os
import unittest
from contextlib import contextmanager
from importlib import reload

import requests
from loguru import logger

import feishubot as feishu


@contextmanager
def capture_logs(level="INFO", format="{level}:{name}:{message}"):
    """Capture loguru-based logs."""
    output = []
    handler_id = logger.add(output.append, level=level, format=format)
    yield output
    logger.remove(handler_id)


class TestFeishu(unittest.TestCase):
    @unittest.skipUnless(feishu.ENABLE, "Feishu is disabled")
    def test_send_text(self):
        feishu.bot.send_text("This is a test message.")

    @unittest.skipUnless(feishu.ENABLE, "Feishu is disabled")
    def test_send_file(self):
        with open(__file__, "rb") as f:
            feishu.bot.send_file(f, "stream")

    @unittest.skipUnless(feishu.ENABLE, "Feishu is disabled")
    def test_send_image(self):
        feishu.bot.send_image(requests.get("https://random.imagecdn.app/500/150").content)

    @unittest.skipUnless(feishu.ENABLE and os.path.exists("test.mp4"), "test.mp4 not found")
    def test_send_media(self):
        with open("test.mp4", "rb") as f:
            feishu.bot.send_media(f)

    @unittest.skipUnless(feishu.ENABLE and os.path.exists("test.opus"), "test.opus not found")
    def test_send_audio(self):
        with open("test.opus", "rb") as f:
            feishu.bot.send_audio(f)

    @unittest.skipUnless(feishu.ENABLE, "Feishu is disabled")
    def test_send_card(self):
        feishu.bot.send_card("This is a test **message**.", "Test card")

    def test_disable(self):
        app_id = os.environ.get("FEISHU_APP_ID", "")
        os.environ["FEISHU_APP_ID"] = ""
        with capture_logs(level="DEBUG") as logs:
            reload(feishu)
        self.assertFalse(feishu.ENABLE)
        self.assertFalse(dir(feishu.bot))
        self.assertTrue(any("feishu bot is unavailable" in log for log in logs))

        os.environ["FEISHU_APP_ID"] = app_id
        with capture_logs(level="DEBUG") as logs:
            reload(feishu)
        self.assertTrue(feishu.ENABLE)
        self.assertTrue(dir(feishu.bot))
        self.assertFalse(any("feishu bot is unavailable" in log for log in logs))
 