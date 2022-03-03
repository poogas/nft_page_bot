import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ANTI_CAPTCHA_KEY = os.getenv("ANTI_CAPTCHA_KEY")
DEVICE_INFO = os.getenv("DEVICE_INFO")
