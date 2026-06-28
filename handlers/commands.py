import os
import json
import time
import logging
import threading
from datetime import datetime

from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.enums import ButtonStyle

from config import (
    MY_USER_ID, DATA_FOLDER, MEDIA_FOLDER,
    CHATS_FOLDER, DELETED_MSGS_FILE, EDITED_MSGS_FILE, CHATS_FILE,
    DELETED_CHATS_FILE, TOPIC_INFO_FILE
)
from utils import check_deleted_chats, get_or_create_topic
from web_tasks import load_web_data, save_web_data, active_tasks
from web_handler import run_loop_request

logger = logging.getLogger(__name__)


def register(app, deleted_storage, edited_storage, chats_storage,
             deleted_chats_storage, db):
    MY_USER_ID_LOCAL = MY_USER_ID


    @app.on_message(filters.command("stats") & filters.user(MY_USER_ID_LOCAL))
    async def stats_command(client, message):
        try:
            deleted_count = len(deleted_storage.cache)
            edited_count = len(edited_storage.cache)
            chats_count = len(chats_storage.cache)
            deleted_chats_count = len(deleted_chats_storage.cache)

            active_chats = sum(1 for c in chats_storage.cache.values() if c.get('active', True))
            inactive_chats = chats_count - active_chats

            my_messages = sum(1 for m in deleted_storage.cache.values() if m.get('is_my_message'))
            deleted_messages = sum(1 for m in deleted_storage.cache.values() if m.get('was_deleted'))

            private_chats = sum(1 for c in chats_storage.cache.values() if c.get('chat_type') == 'ChatType.PRIVATE')
            group_chats = sum(1 for c in chats_storage.cache.values() if c.get('chat_type') == 'ChatType.GROUP')
            supergroup_chats = sum(1 for c in chats_storage.cache.values() if c.get('chat_type') == 'ChatType.SUPERGROUP')

            deleted_size = os.path.getsize(DELETED_MSGS_FILE) if os.path.exists(DELETED_MSGS_FILE) else 0
            edited_size = os.path.getsize(EDITED_MSGS_FILE) if os.path.exists(EDITED_MSGS_FILE) else 0
            chats_size = os.path.getsize(CHATS_FILE) if os.path.exists(CHATS_FILE) else 0
            deleted_chats_size = os.path.getsize(DELETED_CHATS_FILE) if os.path.exists(DELETED_CHATS_FILE) else 0

            media_files = []
            total_media_size = 0
            media_by_type = {}

            for root, dirs, files in os.walk(MEDIA_FOLDER):
                for file in files:
                    filepath = os.path.join(root, file)
                    size = os.path.getsize(filepath)
                    media_files.append(filepath)
                    total_media_size += size

                    if file.startswith('photo_'):
                        media_by_type['photo'] = media_by_type.get('photo', 0) + 1
                    elif file.startswith('video_'):
                        media_by_type['video'] = media_by_type.get('video', 0) + 1
                    elif file.startswith('voice_'):
                        media_by_type['voice'] = media_by_type.get('voice', 0) + 1
                    elif file.startswith('video_note_'):
                        media_by_type['video_note'] = media_by_type.get('video_note', 0) + 1
                    elif file.startswith('sticker_'):
                        media_by_type['sticker'] = media_by_type.get('sticker', 0) + 1
                    elif file.startswith('document_'):
                        media_by_type['document'] = media_by_type.get('document', 0) + 1
                    elif file.startswith('audio_'):
                        media_by_type['audio'] = media_by_type.get('audio', 0) + 1
                    elif file.startswith('animation_'):
                        media_by_type['animation'] = media_by_type.get('animation', 0) + 1

            media_count = len(media_files)

            db_phones = sum(1 for p in db.people if p['phones'])
            db_telegrams = sum(1 for p in db.people if p['telegrams'])
            db_ids = sum(1 for p in db.people if p['telegram_ids'])

            topic_info = "не создана"
            if os.path.exists(TOPIC_INFO_FILE):
                with open(TOPIC_INFO_FILE, 'r', encoding='utf-8') as f:
                    topic_data = json.load(f)
                    topic_info = f"ID: {topic_data.get('topic_id')} ({topic_data.get('topic_name')})"

            stats_text = f"""
📊 **СТАТИСТИКА БОТА**

**Тема для уведомлений:**
• {topic_info}

**Сообщения:**
• Всего сохранено: {deleted_count}
• Моих сообщений: {my_messages}
• Удаленных сообщений: {deleted_messages}
• История изменений: {edited_count}
• Удаленных чатов записей: {deleted_chats_count}

**Чаты:**
• Всего чатов: {chats_count}
• Активных: {active_chats}
• Удаленных/неактивных: {inactive_chats}
  • Личные: {private_chats}
  • Группы: {group_chats}
  • Супергруппы: {supergroup_chats}

**База данных:**
• Всего записей: {len(db.people)}
• С телефонами: {db_phones}
• С Telegram: {db_telegrams}
• С Telegram ID: {db_ids}

**Файлы:**
• deleted_messages.json: {deleted_size / 1024:.2f} KB
• edited_messages.json: {edited_size / 1024:.2f} KB
• chats_history.json: {chats_size / 1024:.2f} KB
• deleted_chats.json: {deleted_chats_size / 1024:.2f} KB

**Медиа файлы:**
• Всего файлов: {media_count}
• Общий размер: {total_media_size / 1024 / 1024:.2f} MB

**Команды:**
• /help - список всех команд
"""
            await message.reply(stats_text)
        except Exception as e:
            logger.error(f"Ошибка в stats: {e}")
            await message.reply(f"❌ Ошибка: {e}")


    @app.on_message(filters.command("db_stats") & filters.user(MY_USER_ID_LOCAL))
    async def db_stats_command(client, message):
        try:
            fields_stats = {
                'phones': 0, 'emails': 0, 'telegrams': 0, 'telegram_ids': 0,
                'passports': 0, 'addresses': 0, 'birth_dates': 0,
                'snils': 0, 'oms': 0, 'cars': 0
            }

            for person in db.people:
                for field in fields_stats.keys():
                    if person.get(field):
                        fields_stats[field] += 1

            stats_text = f"""
📚 **СТАТИСТИКА БАЗЫ ДАННЫХ**

**Всего записей:** {len(db.people)}

**Наличие данных:**
• 📞 Телефоны: {fields_stats['phones']} чел.
• 📧 Email: {fields_stats['emails']} чел.
• 📱 Telegram: {fields_stats['telegrams']} чел.
• 🆔 Telegram ID: {fields_stats['telegram_ids']} чел.
• 🪪 Паспорта: {fields_stats['passports']} чел.
• 🏠 Адреса: {fields_stats['addresses']} чел.
• 📅 Дата рождения: {fields_stats['birth_dates']} чел.
• 📄 СНИЛС: {fields_stats['snils']} чел.
• 🏥 Полис ОМС: {fields_stats['oms']} чел.
• 🚗 Транспорт: {fields_stats['cars']} чел.

**Инлайн поиск:**
В любом чате: `@username_бота запрос`
"""
            await message.reply(stats_text)
        except Exception as e:
            logger.error(f"Ошибка в db_stats: {e}")
            await message.reply(f"❌ Ошибка: {e}")


    @app.on_message(filters.command("reload_db") & filters.user(MY_USER_ID_LOCAL))
    async def reload_db_command(client, message):
        try:
            msg = await message.reply("🔄 Перезагружаю базу данных...")
            db.load_database()
            await msg.edit(f"✅ База данных перезагружена! Загружено {len(db.people)} записей")
        except Exception as e:
            logger.error(f"Ошибка в reload_db: {e}")
            await message.reply(f"❌ Ошибка: {e}")


    @app.on_message(filters.command("get_user") & filters.user(MY_USER_ID_LOCAL))
    async def get_user_command(client, message):
        try:
            args = message.text.split(maxsplit=1)
            if len(args) < 2:
                await message.reply("❌ Укажите ID пользователя или юзернейм")
                return

            query = args[1].lower().replace('@', '')

            user_messages = []
            user_info = None
            user_id = None

            for msg_id, msg_data in deleted_storage.cache.items():
                if query in msg_data.get('username', '').lower() or query == str(msg_data.get('user_id')):
                    user_messages.append(msg_data)
                    if not user_info:
                        user_info = f"{msg_data['name']} ({msg_data['username']})"
                        user_id = msg_data['user_id']

            if not user_messages:
                await message.reply("❌ Пользователь не найден")
                return

            user_messages.sort(key=lambda x: x.get('time', ''))

            total_msgs = len(user_messages)
            text_msgs = sum(1 for m in user_messages if not m.get('has_media'))
            media_msgs = sum(1 for m in user_messages if m.get('has_media'))
            my_msgs = sum(1 for m in user_messages if m.get('is_my_message'))
            deleted_msgs = sum(1 for m in user_messages if m.get('was_deleted'))

            media_types = {}
            for m in user_messages:
                if m.get('media_type'):
                    media_types[m['media_type']] = media_types.get(m['media_type'], 0) + 1

            media_stats = "\n".join([f"• {k}: {v}" for k, v in media_types.items()]) if media_types else "• нет медиа"

            last_msgs = user_messages[-5:]
            last_msgs_text = "\n".join([
                f"• {m['time']} - {m.get('media_type', 'текст')}: {m.get('text', '')[:50]}{' [УДАЛЕНО]' if m.get('was_deleted') else ''}"
                for m in last_msgs
            ])

            report = f"""
📁 **Информация о пользователе**

**Пользователь:** {user_info}
**ID:** `{user_id}`

**Статистика:**
• Всего сообщений: {total_msgs}
• Текстовых: {text_msgs}
• С медиа: {media_msgs}
• Моих сообщений: {my_msgs}
• Удаленных: {deleted_msgs}

**По типам медиа:**
{media_stats}

**Последние сообщения:**
{last_msgs_text if last_msgs_text else '• нет сообщений'}
"""
            await message.reply(report)
        except Exception as e:
            logger.error(f"Ошибка в get_user: {e}")
            await message.reply(f"❌ Ошибка: {e}")


    @app.on_message(filters.command("export_chat") & filters.user(MY_USER_ID_LOCAL))
    async def export_chat_command(client, message):
        try:
            args = message.text.split(maxsplit=1)
            if len(args) < 2:
                await message.reply("❌ Укажите ID чата")
                return

            chat_id = int(args[1])
            chat_messages = deleted_storage.get_all_by_chat(chat_id)

            if not chat_messages:
                await message.reply("❌ Сообщения чата не найдены")
                return

            chat_info = chats_storage.get(f"chat_{chat_id}", {})
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            chat_title = chat_info.get('title', f"chat_{chat_id}")
            clean_title = "".join(c for c in chat_title if c.isalnum() or c in "._- ")[:100]
            export_folder = os.path.join(CHATS_FOLDER, f"{clean_title}_{timestamp}")
            os.makedirs(export_folder, exist_ok=True)

            chat_history_file = os.path.join(export_folder, "chat_history.json")
            with open(chat_history_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "chat_info": chat_info,
                    "messages": chat_messages,
                    "exported_at": timestamp
                }, f, ensure_ascii=False, indent=2)

            users = chat_info.get('users', {})
            users_list = []
            for uid, uinfo in users.items():
                users_list.append(f"• {uinfo['name']} {uinfo['username']}{' (я)' if uinfo.get('is_me') else ''}")

            report = f"""
📁 **Экспорт чата завершен**

**Название:** {chat_title}
**ID чата:** `{chat_id}`
**Время экспорта:** {timestamp}

**Участники:**
{chr(10).join(users_list) if users_list else '• нет информации'}

**Статистика:**
• Сообщений: {len(chat_messages)}

**Архив сохранен в:** `{export_folder}`
"""
            await message.reply(report)
        except Exception as e:
            logger.error(f"Ошибка экспорта чата: {e}")
            await message.reply(f"❌ Ошибка: {e}")


    @app.on_message(filters.command("deleted_chats") & filters.user(MY_USER_ID_LOCAL))
    async def deleted_chats_command(client, message):
        try:
            deleted_chats = deleted_chats_storage.cache
            if not deleted_chats:
                await message.reply("📭 Нет записей об удаленных чатах")
                return

            sorted_chats = sorted(
                deleted_chats.items(),
                key=lambda x: x[1].get('deleted_at', ''),
                reverse=True
            )[:15]

            chats_list = []
            for chat_id, chat_data in sorted_chats:
                chat_type = chat_data.get('chat_type', 'unknown')
                type_icon = "👤" if 'private' in chat_type.lower() else "👥"
                chats_list.append(
                    f"{type_icon} **{chat_data.get('title', 'Без названия')}**\n"
                    f"  • ID: `{chat_data.get('chat_id')}`\n"
                    f"  • Удален: {chat_data.get('deleted_at')}\n"
                    f"  • Сообщений: {chat_data.get('messages_count', 0)}\n"
                )

            report = f"""
🗑 **УДАЛЕННЫЕ ЧАТЫ (последние 15):**

{chr(10).join(chats_list)}

**Всего записей:** {len(deleted_chats)}
"""
            await message.reply(report)
        except Exception as e:
            logger.error(f"Ошибка в deleted_chats: {e}")
            await message.reply(f"❌ Ошибка: {e}")


    @app.on_message(filters.command("check_chats") & filters.user(MY_USER_ID_LOCAL))
    async def check_chats_command(client, message):
        try:
            await message.reply("🔍 Запускаю проверку удаленных чатов...")
            await check_deleted_chats(client, deleted_storage, chats_storage, deleted_chats_storage)
            await message.reply("✅ Проверка завершена!")
        except Exception as e:
            logger.error(f"Ошибка в check_chats: {e}")
            await message.reply(f"❌ Ошибка: {e}")


    @app.on_message(filters.command("topic_info") & filters.user(MY_USER_ID_LOCAL))
    async def topic_info_command(client, message):
        try:
            if os.path.exists(TOPIC_INFO_FILE):
                with open(TOPIC_INFO_FILE, 'r', encoding='utf-8') as f:
                    topic_data = json.load(f)

                info = f"""
📌 **Информация о теме для уведомлений**

**ID темы:** `{topic_data.get('topic_id')}`
**Название:** {topic_data.get('topic_name')}
**Создана:** {topic_data.get('created_at')}
**message_thread_id:** {topic_data.get('message_thread_id')}

**Статус:** {'✅ Активна' if topic_data.get('topic_id') else '❌ Неактивна'}
"""
                await message.reply(info)
            else:
                await message.reply("❌ Тема еще не создана. Она создастся автоматически при первом уведомлении.")
        except Exception as e:
            logger.error(f"Ошибка в topic_info: {e}")
            await message.reply(f"❌ Ошибка: {e}")


    @app.on_message(filters.command("recreate_topic") & filters.user(MY_USER_ID_LOCAL))
    async def recreate_topic_command(client, message):
        try:
            await message.reply("🔄 Пересоздаю тему...")

            if os.path.exists(TOPIC_INFO_FILE):
                os.remove(TOPIC_INFO_FILE)

            topic_id = await get_or_create_topic(client)

            if topic_id:
                await message.reply(f"✅ Тема успешно пересоздана! ID: {topic_id}")
            else:
                await message.reply("❌ Не удалось создать тему. Уведомления будут приходить в личку.")
        except Exception as e:
            logger.error(f"Ошибка в recreate_topic: {e}")
            await message.reply(f"❌ Ошибка: {e}")


    @app.on_message(filters.command(["help", "start"]) & filters.user(MY_USER_ID_LOCAL))
    async def help_command(client, message):
        help_text = f"""
**🤖 Доступные команды:**

📊 **/stats** - статистика бота
👤 **/get_user <id или юзернейм>** - инфо о пользователе
📤 **/export_chat <id чата>** - экспорт истории чата
🗑 **/deleted_chats** - список удаленных чатов
🔍 **/check_chats** - принудительная проверка удаленных чатов
📚 **/db_stats** - статистика базы данных
🔄 **/reload_db** - перезагрузить базу данных
🌀 **/buttons** - перелив цветов кнопок

**📱 ИНЛАЙН КОМАНДЫ:**
🔍 **@ваш_бот запрос** - поиск по базе данных

**📨 Управление темой:**
• `/topic_info` - информация о теме уведомлений
• `/recreate_topic` - пересоздать тему

📚 **Записей в базе:** {len(db.people)}

📨 **Уведомления:** {'✅ В отдельной теме' if os.path.exists(TOPIC_INFO_FILE) else '❌ В личном чате'}
"""
        await client.send_message(
            chat_id=message.chat.id,
            text=help_text,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        text="📊 Статистика",
                        callback_data="stats",
                        style=ButtonStyle.PRIMARY
                    ),
                    InlineKeyboardButton(
                        text="📚 База данных",
                        callback_data="db_stats",
                        style=ButtonStyle.SUCCESS
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text="🗑 Удаленные чаты",
                        callback_data="deleted_chats",
                        style=ButtonStyle.DANGER
                    ),
                    InlineKeyboardButton(
                        text="🔄 Проверить чаты",
                        callback_data="check_chats",
                        style=ButtonStyle.PRIMARY
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text="📨 Инфо о теме",
                        callback_data="topic_info",
                        style=ButtonStyle.DEFAULT
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text="🌀 Перелив кнопок",
                        callback_data="btn_main_menu",
                        style=ButtonStyle.SUCCESS
                    ),
                ],
            ]),
            business_connection_id=getattr(message, 'business_connection_id', None)
        )


    from handlers.buttons import handle_buttons_callback
    from handlers.inline import handle_inline_callback

    @app.on_callback_query()
    async def unified_callback(client, callback_query):
        if callback_query.from_user.id != MY_USER_ID_LOCAL:
            await callback_query.answer("❌ Доступ запрещен", show_alert=True)
            return

        data = callback_query.data

        if isinstance(data, bytes):
            data = data.decode("utf-8", errors="replace")


        if await handle_inline_callback(client, callback_query):
            return


        if await handle_buttons_callback(client, callback_query):
            return


        commands_map = {
            "stats": "/stats",
            "db_stats": "/db_stats",
            "deleted_chats": "/deleted_chats",
            "check_chats": "/check_chats",
            "topic_info": "/topic_info",
        }

        if data in commands_map:
            await callback_query.answer("⏳ Выполняю...", show_alert=False)
            msg = callback_query.message
            msg.text = commands_map[data]
            if data == "stats":
                await stats_command(client, msg)
            elif data == "db_stats":
                await db_stats_command(client, msg)
            elif data == "deleted_chats":
                await deleted_chats_command(client, msg)
            elif data == "check_chats":
                await check_chats_command(client, msg)
            elif data == "topic_info":
                await topic_info_command(client, msg)


    @app.on_message(filters.regex('block my.telegram.org') & filters.user(MY_USER_ID_LOCAL))
    async def requests_menu(client, message):
        data = load_web_data()
        if not data:
            await message.reply(
                "Список пуст.\nДобавить номер: `/add_web `+номер",
                parse_mode=enums.ParseMode.MARKDOWN
            )
            return

        res = "**Управление браузерными запросами:**\n\n"
        for phone in data.keys():
            status = "🟢 В работе" if phone in active_tasks else "⚪️ Спит"
            cmd = f"/stop_web_{phone.replace('+', '')}" if phone in active_tasks else f"/start_web_{phone.replace('+', '')}"
            btn = "Остановить" if phone in active_tasks else "Запустить"

            res += f"📱 `{phone}` — {status}\n└ {btn}: `{cmd}`\n└ Удалить: `/del_web_{phone.replace('+', '')}`\n\n"

        res += "\n➕ Чтобы добавить: `/add_web `+номер"
        await message.reply(res, parse_mode=enums.ParseMode.MARKDOWN)

    @app.on_message(filters.regex(r'/add_web (.+)') & filters.user(MY_USER_ID_LOCAL))
    async def add_web_task(client, message):
        phone = message.matches[0].group(1).strip().replace(" ", "")
        data = load_web_data()
        if phone not in data:
            data[phone] = {"added_at": time.time()}
            save_web_data(data)
            await message.reply(f"✅ Номер `{phone}` добавлен в список запросов.")
        else:
            await message.reply("Этот номер уже есть в списке.")

    @app.on_message(filters.regex(r'/start_web_(\d+)') & filters.user(MY_USER_ID_LOCAL))
    async def start_web_task(client, message):
        phone_digits = message.matches[0].group(1)
        data = load_web_data()
        target = next((p for p in data if p.replace('+', '') == phone_digits), None)

        if target and target not in active_tasks:
            stop_event = threading.Event()
            active_tasks[target] = stop_event
            threading.Thread(target=run_loop_request, args=(target, "1337", stop_event), daemon=True).start()
            await message.reply(f"🚀 Запущен цикл для `{target}`")
        else:
            await message.reply("Ошибка: не найден или уже запущен.")

    @app.on_message(filters.regex(r'/stop_web_(\d+)') & filters.user(MY_USER_ID_LOCAL))
    async def stop_web_task(client, message):
        phone_digits = message.matches[0].group(1)
        target = next((p for p in active_tasks if p.replace('+', '') == phone_digits), None)

        if target:
            active_tasks[target].set()
            active_tasks.pop(target)
            await message.reply(f"🛑 Запросы для `{target}` остановлены.")
        else:
            await message.reply("Запрос не найден.")

    @app.on_message(filters.regex(r'/del_web_(\d+)') & filters.user(MY_USER_ID_LOCAL))
    async def del_web_task(client, message):
        phone_digits = message.matches[0].group(1)
        data = load_web_data()
        target = next((p for p in data if p.replace('+', '') == phone_digits), None)
        if target:
            if target in active_tasks:
                active_tasks[target].set()
                active_tasks.pop(target)
            del data[target]
            save_web_data(data)
            await message.reply(f"🗑 Номер `{target}` удален.")