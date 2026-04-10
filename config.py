import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0")) if os.getenv("CHANNEL_ID") else None
PRICE = int(os.getenv("PRICE", "900000"))
CARD_NUMBER = os.getenv("CARD_NUMBER", "8600 1234 5678 9012")