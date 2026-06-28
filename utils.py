import json
import os
import time
import asyncio
import logging
import shutil
from datetime import datetime

from config import MY_USER_ID, MEDIA_FOLDER, DATA_FOLDER, CHATS_FOLDER, TOPIC_INFO_FILE
from pyrogram.types import LinkPreviewOptions

logger = logging.getLogger(__name__)


def clean_text_from_formatting(text):
    import re
    if not text:
        return ""
    text = re.sub(r'\${1,2}(.*?)\${1,2}', r'\1', text)
    text = re.sub(r'\\\(.*?\\\)', '', text)
    text = re.sub(r'\\\[.*?\\\]', '', text)
    text = re.sub(r'<[^>]+>', '', text)
    return text.strip()


def get_user_info(user):
    if not user:
        return "Unknown", "unknown"
    name = user.first_name or ""
    if user.last_name:
        name += f" {user.last_name}"
    if not name:
        name = "Без имени"
    username = f"@{user.username}" if user.username else "нет юзернейма"
    return name, username


async def save_media_file(client, message, media_type, file_ext, name, user_id):
    try:
        clean_name = "".join(c for c in name if c.isalnum() or c in "._- ")[:50]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        date_folder = datetime.now().strftime("%Y%m%d")
        user_folder = f"user_{user_id}"
        full_media_folder = os.path.join(MEDIA_FOLDER, date_folder, user_folder)
        os.makedirs(full_media_folder, exist_ok=True)
        filename = f"{media_type}_{clean_name}_{timestamp}_{message.id}.{file_ext}"
        filepath = os.path.join(full_media_folder, filename)
        await client.download_media(message, file_name=filepath)
        logger.info(f"📸 Сохранил {media_type}: {filename}")
        return filepath, filename
    except Exception as e:
        logger.error(f"Ошибка сохранения медиа: {e}")
        return None, None


async def get_or_create_topic(client):
    """Получает или создает тему для уведомлений"""
    try:
        if os.path.exists(TOPIC_INFO_FILE):
            with open(TOPIC_INFO_FILE, 'r', encoding='utf-8') as f:
                topic_data = json.load(f)
                topic_id = topic_data.get('topic_id')

                try:
                    await client.get_forum_topics(chat_id=MY_USER_ID)
                    logger.info(f"📌 Использую существующую тему ID: {topic_id}")
                    return topic_id
                except Exception:
                    logger.warning("⚠️ Сохраненная тема не найдена, создаю новую")

        topic_name = f"📨 Уведомления бота {datetime.now().strftime('%d.%m.%Y')}"

        try:
            result = await client.create_forum_topic(
                chat_id=MY_USER_ID,
                title=topic_name
            )

            if result and hasattr(result, 'id'):
                topic_id = result.id

                topic_data = {
                    'topic_id': topic_id,
                    'topic_name': topic_name,
                    'created_at': datetime.now().isoformat(),
                    'message_thread_id': topic_id
                }

                with open(TOPIC_INFO_FILE, 'w', encoding='utf-8') as f:
                    json.dump(topic_data, f, ensure_ascii=False, indent=2)

                logger.info(f"✅ Создана новая тема ID: {topic_id}")

                await client.send_message(
                    chat_id=MY_USER_ID,
                    text="📨 **Тема для уведомлений создана**\n\nСюда будут приходить все уведомления об удаленных и измененных сообщениях.",
                    message_thread_id=topic_id
                )

                return topic_id
        except Exception as e:
            logger.error(f"Ошибка создания темы: {e}")

        return None
    except Exception as e:
        logger.error(f"Ошибка в get_or_create_topic: {e}")
        return None


async def send_to_topic(client, text, file_path=None, media_type=None):
    """Отправляет уведомление в личку (без тем)"""
    try:
        if file_path and os.path.exists(file_path):
            if media_type == "Фото":
                await client.send_photo(
                    chat_id=MY_USER_ID,
                    photo=file_path,
                    caption=text
                )
            elif media_type == "Видео":
                await client.send_video(
                    chat_id=MY_USER_ID,
                    video=file_path,
                    caption=text
                )
            elif media_type == "Голосовое":
                await client.send_voice(
                    chat_id=MY_USER_ID,
                    voice=file_path,
                    caption=text
                )
            elif media_type == "Видеосообщение":
                await client.send_video_note(
                    chat_id=MY_USER_ID,
                    video_note=file_path
                )
            elif media_type == "Аудио":
                await client.send_audio(
                    chat_id=MY_USER_ID,
                    audio=file_path,
                    caption=text
                )
            elif media_type == "Стикер":
                await client.send_sticker(
                    chat_id=MY_USER_ID,
                    sticker=file_path
                )
            elif media_type == "Анимация":
                await client.send_animation(
                    chat_id=MY_USER_ID,
                    animation=file_path,
                    caption=text
                )
            else:
                await client.send_document(
                    chat_id=MY_USER_ID,
                    document=file_path,
                    caption=text
                )
        else:
            await client.send_message(
                chat_id=MY_USER_ID,
                text=text,
                link_preview_options=LinkPreviewOptions(is_disabled=True)
            )
    except Exception as e:
        logger.error(f"Ошибка отправки: {e}")


async def check_deleted_chats(client, deleted_storage, chats_storage, deleted_chats_storage):
    """Проверяет доступность всех отслеживаемых чатов и экспортирует данные при потере доступа"""
    try:
        all_chats = list(chats_storage.cache.values())

        for chat_info in all_chats:
            chat_id = chat_info.get('chat_id')
            if not chat_id or not chat_info.get('active', True):
                continue

            try:
                chat = await client.get_chat(chat_id)
                logger.info(f"✅ Чат активен: {getattr(chat, 'title', str(chat_id))}")
            except Exception as e:
                error_str = str(e).lower()
                if "chat not found" in error_str or "forbidden" in error_str or "user not participating" in error_str:
                    logger.info(f"🚫 Потерян доступ к чату: {chat_id}")

                    chat_messages = deleted_storage.get_all_by_chat(chat_id)
                    chat_title = chat_info.get('title', f"chat_{chat_id}")

                    chat_type = chat_info.get('chat_type', 'unknown')
                    if chat_type == 'private':
                        other_user = None
                        for uid, uinfo in chat_info.get('users', {}).items():
                            if not uinfo.get('is_me'):
                                other_user = uinfo
                                break
                        if other_user:
                            chat_title = f"Личный чат с {other_user['name']} ({other_user['username']})"
                        else:
                            chat_title = f"Личный чат (ID: {chat_id})"

                    deleted_chat_data = {
                        "chat_id": chat_id,
                        "title": chat_title,
                        "chat_type": chat_type,
                        "deleted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "last_message_time": chat_info.get("last_message_time", "неизвестно"),
                        "messages_count": len(chat_messages),
                        "users": chat_info.get("users", {})
                    }

                    deleted_chats_storage.add(f"deleted_{chat_id}_{datetime.now().timestamp()}", deleted_chat_data)

                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    clean_title = "".join(c for c in chat_title if c.isalnum() or c in "._- ")[:100]
                    export_folder = os.path.join(CHATS_FOLDER, f"DELETED_{clean_title}_{timestamp}")
                    os.makedirs(export_folder, exist_ok=True)

                    chat_history_file = os.path.join(export_folder, "chat_history.json")
                    with open(chat_history_file, 'w', encoding='utf-8') as f:
                        json.dump({
                            "chat_info": chat_info,
                            "messages": chat_messages,
                            "deleted_at": timestamp,
                            "reason": "bot_removed"
                        }, f, ensure_ascii=False, indent=2)

                    users_list = []
                    for uid, uinfo in chat_info.get('users', {}).items():
                        users_list.append(f"• {uinfo['name']} {uinfo['username']}{' (я)' if uinfo.get('is_me') else ''}")

                    report = f"""
🚫 **МЕНЯ УДАЛИЛИ ИЗ ЧАТА!**

**Чат:** {chat_title}
**ID:** `{chat_id}`
**Тип:** {chat_type}
**Время:** {timestamp}

**Статистика:**
• Сообщений сохранено: {len(chat_messages)}
**Участники чата:**
{chr(10).join(users_list) if users_list else '• нет информации'}

**Архив сохранен в:** `{export_folder}`
"""
                    await send_to_topic(client, report)

                    chat_info["active"] = False
                    chat_info["deleted_at"] = timestamp
                    chats_storage.add(f"chat_{chat_id}", chat_info)
            await asyncio.sleep(2)
    except Exception as e:
        logger.error(f"Ошибка при проверке удаленных чатов: {e}")