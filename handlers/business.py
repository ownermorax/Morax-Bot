import logging
import os
import json
from datetime import datetime

from pyrogram import filters

from config import MY_USER_ID
from utils import get_user_info, save_media_file, send_to_topic

logger = logging.getLogger(__name__)


def register(app, deleted_storage, edited_storage, chats_storage):
    MY_USER_ID_LOCAL = MY_USER_ID

    @app.on_business_message()
    async def handle_business(client, message):
        try:
            name, username = get_user_info(message.from_user) if message.from_user else ("Unknown", "unknown")
            user_id = message.from_user.id if message.from_user else 0

            if message.text and message.text.startswith('/'):
                return

            media_type = None
            file_ext = None
            media_info = {}
            media_type_ru = None

            if message.photo:
                media_type = "photo"
                file_ext = "jpg"
                media_type_ru = "Фото"
                media_info = {
                    "type": "photo",
                    "file_id": message.photo.file_id,
                    "caption": message.caption
                }
            elif message.video:
                media_type = "video"
                file_ext = "mp4"
                media_type_ru = "Видео"
                media_info = {
                    "type": "video",
                    "file_id": message.video.file_id,
                    "duration": message.video.duration,
                    "caption": message.caption
                }
            elif message.voice:
                media_type = "voice"
                file_ext = "ogg"
                media_type_ru = "Голосовое"
                media_info = {
                    "type": "voice",
                    "file_id": message.voice.file_id,
                    "duration": message.voice.duration
                }
            elif message.video_note:
                media_type = "video_note"
                file_ext = "mp4"
                media_type_ru = "Видеосообщение"
                media_info = {
                    "type": "video_note",
                    "file_id": message.video_note.file_id,
                    "duration": message.video_note.duration
                }
            elif message.sticker:
                media_type = "sticker"
                file_ext = "webp"
                media_type_ru = "Стикер"
                media_info = {
                    "type": "sticker",
                    "file_id": message.sticker.file_id,
                    "emoji": message.sticker.emoji
                }
            elif message.document:
                media_type = "document"
                file_ext = message.document.file_name.split('.')[-1] if message.document.file_name else "bin"
                media_type_ru = "Документ"
                media_info = {
                    "type": "document",
                    "file_id": message.document.file_id,
                    "file_name": message.document.file_name,
                    "mime_type": message.document.mime_type
                }
            elif message.audio:
                media_type = "audio"
                file_ext = "mp3"
                media_type_ru = "Аудио"
                media_info = {
                    "type": "audio",
                    "file_id": message.audio.file_id,
                    "title": message.audio.title,
                    "performer": message.audio.performer,
                    "duration": message.audio.duration
                }
            elif message.animation:
                media_type = "animation"
                file_ext = "gif"
                media_type_ru = "Анимация"
                media_info = {
                    "type": "animation",
                    "file_id": message.animation.file_id
                }

            message_data = {
                "name": name,
                "username": username,
                "user_id": user_id,
                "time": datetime.now().strftime("%H:%M:%S"),
                "chat_id": message.chat.id,
                "date": str(message.date),
                "text": message.text or message.caption or "",
                "is_my_message": (user_id == MY_USER_ID_LOCAL),
                "was_deleted": False
            }



            deleted_storage.add(message.id, message_data)

            if media_type:
                message_data["media"] = media_info
                message_data["has_media"] = True
                message_data["media_type"] = media_type_ru

                try:
                    filepath, filename = await save_media_file(client, message, media_type, file_ext, name, user_id)
                    if filepath:
                        message_data["media_file"] = filename
                        message_data["media_path"] = filepath
                except Exception as e:
                    logger.error(f"Ошибка сохранения медиа для {message.id}: {e}")

            chat_key = f"chat_{message.chat.id}"
            chat_data = {
                "chat_id": message.chat.id,
                "chat_type": str(message.chat.type),
                "last_message_time": message_data["time"],
                "last_message_id": message.id,
                "users": {}
            }

            if message.from_user:
                chat_data["users"][str(user_id)] = {
                    "name": name,
                    "username": username,
                    "is_me": (user_id == MY_USER_ID_LOCAL)
                }

            if message.chat and hasattr(message.chat, 'title'):
                chat_data["title"] = message.chat.title
            else:
                chat_data["title"] = f"Личный чат с {name}"

            if chats_storage.contains(chat_key):
                existing = chats_storage.get(chat_key)
                existing["last_message_time"] = message_data["time"]
                existing["last_message_id"] = message.id
                existing["active"] = True
                if message.from_user and str(user_id) not in existing["users"]:
                    existing["users"][str(user_id)] = {
                        "name": name,
                        "username": username,
                        "is_me": (user_id == MY_USER_ID_LOCAL)
                    }
                chats_storage.add(chat_key, existing)
            else:
                chat_data["active"] = True
                chat_data["created_at"] = message_data["time"]
                chats_storage.add(chat_key, chat_data)

            log_prefix = "👤" if user_id != MY_USER_ID_LOCAL else "🤖"
            logger.info(f"{log_prefix} Сохранил: {message.id} от {name} ({media_type_ru if media_type_ru else 'текст'}) в чате {message.chat.id}")

            if user_id != MY_USER_ID_LOCAL and (message.text or message.caption):
                text_to_check = (message.text or message.caption or "").lower()
                textS = ''.join(text_to_check.split())
                trigger_words = ['можно нфт', 'хочу нфт', 'дай нфт']

                if (('можно' in textS or 'подари' in textS or 'дай' in textS or 'даришь' in textS or 'дариш' in textS or 'дарите' in textS) and
                    ('подарок' in textS or 'нфт' in textS or 'мишку' in textS or
                     'медведя' in textS or 'ракету' in textS or 'подарки' in textS or 'подарочек' in textS or 'падарочек' in textS or 'падарок' in textS)) or \
                    any(word in text_to_check for word in trigger_words):

                    await client.send_message(
                        chat_id=message.chat.id,
                        text=f"Вот как получить от меня подарок\n->https://telegra.ph/HowToGetGiftFromMe-02-17\n\nЕсли всё сделано, то жди пока я всё проверю и выдам подарок.",
                        business_connection_id=message.business_connection_id
                    )
                    logger.info(f"🎯 Ответ на триггер от {name}")
        except Exception as e:
            logger.error(f"Ошибка в handle_business: {e}")

    @app.on_deleted_business_messages()
    async def handle_deleted_messages(client, messages):
        try:
            for message in messages:
                if deleted_storage.contains(message.id):
                    cached = deleted_storage.get(message.id)

                    cached["was_deleted"] = True
                    cached["deleted_at"] = datetime.now().strftime("%H:%M:%S")
                    deleted_storage.add(message.id, cached)

                    if cached.get('is_my_message'):
                        logger.info(f"⏭ Пропущено уведомление о моём удаленном сообщении ID {message.id}")
                        continue

                    content_type = cached.get('media_type', 'текст')
                    content_info = cached.get('text', '')

                    if cached.get('has_media'):
                        media = cached.get('media', {})
                        if media.get('caption'):
                            content_info = media['caption']
                        elif media.get('file_name'):
                            content_info = media['file_name']
                        elif media.get('title'):
                            content_info = f"{media.get('title', '')} - {media.get('performer', '')}"

                    if len(content_info) > 200:
                        content_info = content_info[:200] + "..."

                    report = f"""
🗑 **УДАЛЕНО СООБЩЕНИЕ**

**От:** {cached['name']}
**Юзернейм:** {cached['username']}
**ID:** `{cached['user_id']}`
**Чат:** `{cached['chat_id']}`
**Тип:** {content_type}
**Время отправки:** {cached['time']}
**Время удаления:** {datetime.now().strftime("%H:%M:%S")}
**Содержимое:** `{content_info}`

[#удалено](https://t.me/{cached['username'].replace('@', '') if cached['username'] != 'нет юзернейма' else 'telegram'})
"""
                    await send_to_topic(client, report)

                    if cached.get('has_media') and cached.get('media_path'):
                        try:
                            filepath = cached['media_path']
                            if os.path.exists(filepath):
                                media_caption = f"🗑 Удаленное {cached.get('media_type', 'Медиа')} от {cached['name']}"
                                await send_to_topic(
                                    client,
                                    media_caption,
                                    filepath,
                                    cached.get('media_type')
                                )
                        except Exception as e:
                            logger.error(f"Ошибка отправки удаленного медиа: {e}")

                    logger.info(f"📨 Удалено {content_type} от {cached['name']} (ID: {message.id})")
                else:
                    logger.warning(f"⚠️ Удалено сообщение ID {message.id} (не в хранилище)")
                    await send_to_topic(
                        client,
                        f"⚠️ Удалено сообщение ID {message.id} (не найдено в хранилище)"
                    )
        except Exception as e:
            logger.error(f"Ошибка при удалении: {e}")

    @app.on_edited_business_message()
    async def handle_edited_messages(client, message):
        try:
            name, username = get_user_info(message.from_user) if message.from_user else ("Unknown", "unknown")
            user_id = message.from_user.id if message.from_user else 0

            if user_id == MY_USER_ID_LOCAL:
                logger.info(f"⏭ Пропущено уведомление о моём измененном сообщении ID {message.id}")
                return

            old_text = "не найдено"
            old_media = None
            old_media_type = None

            if deleted_storage.contains(message.id):
                old_data = deleted_storage.get(message.id)
                old_text = old_data.get("text", "")
                old_media = old_data.get("media")
                old_media_type = old_data.get("media_type")

                message_data = {
                    "name": name,
                    "username": username,
                    "user_id": user_id,
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "chat_id": message.chat.id,
                    "date": str(message.date),
                    "text": message.text or message.caption or "",
                    "edited": True,
                    "previous_version": old_text,
                    "media_type": old_media_type,
                    "is_my_message": (user_id == MY_USER_ID_LOCAL)
                }

                if old_media:
                    message_data["media"] = old_media
                    message_data["has_media"] = True

                deleted_storage.add(f"{message.id}_edited_{datetime.now().timestamp()}", message_data)

            edit_data = {
                "message_id": message.id,
                "user_id": user_id,
                "name": name,
                "username": username,
                "old_text": old_text,
                "new_text": message.text or message.caption or "",
                "had_media": bool(old_media),
                "media_type": old_media_type,
                "time": datetime.now().strftime("%H:%M:%S"),
                "is_my_message": (user_id == MY_USER_ID_LOCAL)
            }
            edited_storage.add(f"{message.id}_{datetime.now().timestamp()}", edit_data)

            old_text_short = old_text[:100] + "..." if len(old_text) > 100 else old_text
            new_text_short = (message.text or message.caption or "")[:100] + "..." if len(message.text or message.caption or "") > 100 else (message.text or message.caption or "")

            report = f"""
✏️ **ИЗМЕНЕНО СООБЩЕНИЕ**

**От:** {name}
**Юзернейм:** {username}
**ID:** `{user_id}`
**Чат:** `{message.chat.id}`
**Время:** {datetime.now().strftime("%H:%M:%S")}
**Тип:** {old_media_type or 'Текст'}

**Было:** `{old_text_short}`
**Стало:** `{new_text_short}`

[#изменено](https://t.me/{username.replace('@', '') if username != 'нет юзернейма' else 'telegram'})
"""
            await send_to_topic(client, report)
            logger.info(f"✏️ Изменено от {name} (ID: {message.id})")
        except Exception as e:
            logger.error(f"Ошибка при изменении: {e}")