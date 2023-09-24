# feishubot

Send message to you by feishu bot

## Install

```bash
pip install feishubot2
```

If you need send image, you need install with `media` option

```bash
pip install feishubot2[media]
```

## Usage

1. Set environment `FEISHU_APP_ID` and `FEISHU_APP_SECRET` to use feishu api
2. set FEISHU_PHONE or `FEISHU_EMAIL` or `FEISHU_OPEN_ID` for sending message to you

> when environment was not set correctly, bot will be disable

## Feature

- Send plain message
- Send file
- Send image
- Send video with cover
- Send audio
- Send simple card

## Examples

```python
from feishubot import bot

def test_send_text(self):
    bot.send_text("This is a test message.")

def test_send_file(self):
    with open(__file__, "rb") as f:
        bot.send_file(f, "stream")

def test_send_image(self):
    bot.send_image(requests.get("https://random.imagecdn.app/500/150").content)

def send_audio(self):
    with open("test.opus", "rb") as f:
        bot.send_audio(f)

def test_send_media(self):
    with open("test.mp4", "rb") as f:
        bot.send_media(f)

def test_send_card(self):
    bot.send_card("This is a test **message**.", header="Test card")
```
