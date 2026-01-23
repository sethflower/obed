import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "8372459093:AAEfF6Ev2cOoKjxMW3kZLvh3oYoMm5OFIXs")
DB_PATH = os.getenv("DB_PATH", "data.sqlite3")
