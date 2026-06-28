import asyncio
import json
import os
import time
import logging
import shutil
from datetime import datetime

from pyrogram import Client, enums

from config import (
    DATA_FOLDER, MEDIA_FOLDER,
    DELETED_MSGS_FILE, EDITED_MSGS_FILE, CHATS_FILE, DELETED_CHATS_FILE
)
from utils import check_deleted_chats
from button_cycles import load_cycles, start_cycle

logger = logging.getLogger(__name__)


def start_background_tasks(app, deleted_storage, edited_storage, chats_storage,
                           deleted_chats_storage):
    """Create and start all background asyncio tasks"""


    async def periodic_chat_check():
        while True:
            try:
                await asyncio.sleep(1800)
                logger.info("🔍 Периодическая проверка удаленных чатов...")
                await check_deleted_chats(app, deleted_storage, chats_storage, deleted_chats_storage)
            except Exception as e:
                logger.error(f"Ошибка в periodic_chat_check: {e}")


    async def force_save_all():
        while True:
            await asyncio.sleep(300)
            try:
                if deleted_storage.dirty:
                    deleted_storage.save_to_file()
                if edited_storage.dirty:
                    edited_storage.save_to_file()
                if chats_storage.dirty:
                    chats_storage.save_to_file()
                if deleted_chats_storage.dirty:
                    deleted_chats_storage.save_to_file()
                logger.info("💾 Автосохранение всех хранилищ")
            except Exception as e:
                logger.error(f"Ошибка автосохранения: {e}")


    async def cleanup_old_messages():
        """Удаляет сообщения старше 30 дней и логи старше 7 дней"""
        while True:
            try:
                await asyncio.sleep(3600)
                now = time.time()


                deleted_count = 0
                for msg_id in list(deleted_storage.cache.keys()):
                    msg_data = deleted_storage.cache[msg_id]
                    try:
                        msg_time = datetime.strptime(
                            f"{msg_data.get('date', '2000-01-01')} {msg_data.get('time', '00:00:00')}",
                            "%Y-%m-%d %H:%M:%S"
                        ).timestamp()
                        if now - msg_time > 30 * 24 * 3600:
                            if msg_data.get('media_path') and os.path.exists(msg_data['media_path']):
                                os.remove(msg_data['media_path'])
                            del deleted_storage.cache[msg_id]
                            deleted_count += 1
                    except Exception:
                        try:
                            msg_id_int = int(msg_id)
                            if msg_id_int < 100000:
                                if msg_data.get('media_path') and os.path.exists(msg_data['media_path']):
                                    os.remove(msg_data['media_path'])
                                del deleted_storage.cache[msg_id]
                                deleted_count += 1
                        except Exception:
                            pass

                if deleted_count > 0:
                    deleted_storage.dirty = True
                    logger.info(f"🧹 Удалено {deleted_count} старых сообщений")


                edited_count = 0
                for msg_id in list(edited_storage.cache.keys()):
                    msg_data = edited_storage.cache[msg_id]
                    try:
                        if '_' in str(msg_id):
                            timestamp_part = str(msg_id).split('_')[-1]
                            msg_timestamp = float(timestamp_part)
                            if now - msg_timestamp > 30 * 24 * 3600:
                                del edited_storage.cache[msg_id]
                                edited_count += 1
                    except Exception:
                        pass

                if edited_count > 0:
                    edited_storage.dirty = True
                    logger.info(f"🧹 Удалено {edited_count} старых изменений")


                if os.path.exists(MEDIA_FOLDER):
                    for date_folder in os.listdir(MEDIA_FOLDER):
                        folder_path = os.path.join(MEDIA_FOLDER, date_folder)
                        if os.path.isdir(folder_path):
                            try:
                                folder_date = datetime.strptime(date_folder, "%Y%m%d")
                                if now - folder_date.timestamp() > 7 * 24 * 3600:
                                    shutil.rmtree(folder_path)
                                    logger.info(f"🗑 Удалена папка с медиа: {date_folder}")
                            except Exception:
                                pass


                log_files = ['bot.log']
                for log_file in log_files:
                    log_path = os.path.join(DATA_FOLDER, log_file)
                    if os.path.exists(log_path):
                        file_age = now - os.path.getmtime(log_path)
                        if file_age > 7 * 24 * 3600:
                            open(log_path, 'w').close()
                            logger.info(f"🧹 Очищен лог-файл: {log_file}")

                if deleted_storage.dirty:
                    deleted_storage.save_to_file()
                if edited_storage.dirty:
                    edited_storage.save_to_file()

            except Exception as e:
                logger.error(f"Ошибка при очистке данных: {e}")


    load_cycles()
    start_cycle(app)


    tasks = [
        asyncio.create_task(periodic_chat_check()),
        asyncio.create_task(force_save_all()),
        asyncio.create_task(cleanup_old_messages()),
    ]
    return tasks