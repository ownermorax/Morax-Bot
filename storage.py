import json
import os
import time
import logging

logger = logging.getLogger(__name__)


class MessageStorage:
    def __init__(self, filename, max_size=None, save_interval=60):
        self.filename = filename
        self.cache = {}
        self.max_size = max_size
        self.save_interval = save_interval
        self.dirty = False
        self.last_save = time.time()
        self.save_task = None
        self.loop = None
        self.auto_save_running = False
        self.load_from_file()

    def load_from_file(self):
        try:
            if os.path.exists(self.filename):
                with open(self.filename, 'r', encoding='utf-8') as f:
                    self.cache = json.load(f)
                logger.info(f"📂 Загружено {len(self.cache)} записей из {self.filename}")
            else:
                self.cache = {}
                self.save_to_file()
        except Exception as e:
            logger.error(f"Ошибка загрузки {self.filename}: {e}")
            self.cache = {}

    def save_to_file(self):
        if not self.dirty:
            return
        try:
            if self.max_size and len(self.cache) > self.max_size:
                sorted_items = sorted(
                    self.cache.items(),
                    key=lambda x: x[1].get('time', ''),
                    reverse=True
                )[:self.max_size]
                self.cache = dict(sorted_items)

            temp_file = f"{self.filename}.tmp"
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)

            os.replace(temp_file, self.filename)
            self.dirty = False
            self.last_save = time.time()
            logger.info(f"💾 Сохранено {len(self.cache)} записей в {self.filename}")
        except Exception as e:
            logger.error(f"Ошибка сохранения {self.filename}: {e}")

    def add(self, key, value):
        self.cache[str(key)] = value
        self.dirty = True

    def get(self, key, default=None):
        return self.cache.get(str(key), default)

    def contains(self, key):
        return str(key) in self.cache

    def get_all_by_user(self, user_id):
        return {k: v for k, v in self.cache.items() if v.get('user_id') == user_id}

    def get_all_by_chat(self, chat_id):
        return {k: v for k, v in self.cache.items() if v.get('chat_id') == chat_id}


