import os

# ==================== API КЛЮЧИ ====================
API_ID = 12345678
API_HASH = "ваш_api_hash"
BOT_TOKEN = "ваш_токен_бота"

# ==================== КОНФИГУРАЦИЯ ПОЛЬЗОВАТЕЛЯ ====================
MY_USER_ID = 123456789
BASE_FILE = "base.txt"

# ==================== ПАПКИ ====================
MEDIA_FOLDER = "deleted_media"
DATA_FOLDER = "bot_data"
CHATS_FOLDER = "deleted_chats"

# ==================== ФАЙЛЫ ДАННЫХ ====================
DELETED_MSGS_FILE = os.path.join(DATA_FOLDER, "deleted_messages.json")
EDITED_MSGS_FILE = os.path.join(DATA_FOLDER, "edited_messages.json")
CHATS_FILE = os.path.join(DATA_FOLDER, "chats_history.json")
DELETED_CHATS_FILE = os.path.join(DATA_FOLDER, "deleted_chats.json")
TOPIC_INFO_FILE = os.path.join(DATA_FOLDER, "topic_info.json")

# ==================== АККАУНТЫ ====================
WEB_JSON = "web_tasks.json"

# ==================== ПЕРЕЛИВ (1bot.py) ====================
BOT_TOKEN_2 = "токен_второго_бота_для_перелива"
CHANNEL_ID = -100123456789
MESSAGE_ID = 123
COLOR_PATTERN = ["danger", "primary", "success"]
BUTTONS_DATA = [
    {"text": "Текст кнопки", "url": "https://example.com"},
]