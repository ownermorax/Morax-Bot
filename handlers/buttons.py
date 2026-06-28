"""Интерактивное меню управления переливом кнопок в канале"""

import logging

from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, LinkPreviewOptions

from config import MY_USER_ID
from button_cycles import (
    cycles_cache, load_cycles, save_cycles, format_cycle_info,
    new_cycle_entry, STYLE_NAMES, STYLE_EMOJIS, start_cycle, apply_cycle_now,
)

logger = logging.getLogger(__name__)

_pending_setup = {}


async def handle_buttons_callback(client, callback_query):
    if callback_query.from_user.id != MY_USER_ID:
        return False

    data = callback_query.data
    if isinstance(data, bytes):
        data = data.decode("utf-8", errors="replace")

    if not data.startswith("btn_"):
        return False

    msg = callback_query.message

    if data == "btn_main_menu":
        await callback_query.answer()
        await _show_main_menu(client, msg.chat.id, msg.id)

    elif data == "btn_cycles_list":
        await callback_query.answer()
        await _show_cycles_list(client, msg.chat.id, msg.id)

    elif data == "btn_add_cycle":
        await callback_query.answer()
        await msg.edit_text(
            "**➕ Добавление перелива**\n\n"
            "Отправь юзернейм канала и ID сообщения через пробел.\n"
            "Например: `@mychannel 27`\n\n"
            "Или ID канала с минусом:\n"
            "Например: `-100123456789 27`\n\n"
            "Или просто перешли сообщение из канала сюда.\n\n"
            "_Важно: у бота должны быть права администратора в канале, и сообщение должно быть отправлено самим ботом._",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Назад", callback_data="btn_main_menu")
            ]]),
            link_preview_options=LinkPreviewOptions(is_disabled=True),
        )
        _pending_setup[msg.chat.id] = {"step": "awaiting_input"}

    elif data.startswith("btn_toggle_"):
        cycle_key = data.replace("btn_toggle_", "")
        if cycle_key in cycles_cache:
            was = cycles_cache[cycle_key].get("enabled", False)
            cycles_cache[cycle_key]["enabled"] = not was
            save_cycles()
            if not was:
                start_cycle()
                await apply_cycle_now(client, cycle_key)
            await callback_query.answer(
                "🟢 Запущен" if cycles_cache[cycle_key]["enabled"] else "🔴 Остановлен",
                show_alert=False,
            )
            await _show_cycles_list(client, msg.chat.id, msg.id)

    elif data.startswith("btn_config_"):
        cycle_key = data.replace("btn_config_", "")
        await callback_query.answer()
        await _show_color_config(client, msg.chat.id, msg.id, cycle_key)

    elif data.startswith("btn_color_"):
        encoded = data[len("btn_color_"):]
        parts = encoded.rsplit("|", 2)
        if len(parts) >= 2:
            cycle_key = parts[0]
            try:
                btn_idx = int(parts[1])
            except ValueError:
                await callback_query.answer("Ошибка", show_alert=True)
                return True

            if len(parts) >= 3 and parts[2]:
                color_name = parts[2]
                if cycle_key in cycles_cache:
                    pattern = cycles_cache[cycle_key].get("color_pattern", ["danger", "primary", "success"])
                    if btn_idx < len(pattern):
                        pattern[btn_idx] = color_name
                        cycles_cache[cycle_key]["color_pattern"] = pattern
                        save_cycles()
                        await apply_cycle_now(client, cycle_key)
                        await callback_query.answer(
                            f"✅ Кнопка {btn_idx + 1}: {STYLE_NAMES.get(color_name, color_name)}",
                            show_alert=False,
                        )
                        await _show_color_config(client, msg.chat.id, msg.id, cycle_key)

    elif data.startswith("btn_remove_button_"):
        encoded = data[len("btn_remove_button_"):]
        parts = encoded.rsplit("|", 1)
        if len(parts) == 2:
            cycle_key = parts[0]
            try:
                btn_idx = int(parts[1])
            except ValueError:
                await callback_query.answer("Ошибка", show_alert=True)
                return True

            if cycle_key in cycles_cache:
                config = cycles_cache[cycle_key]
                btns = config.get("button_configs", [])
                rows = config.get("rows", [])
                if btn_idx < len(btns):
                    removed_text = btns[btn_idx].get("text", "?")
                    del btns[btn_idx]

                    removed = False
                    for row in rows:
                        for i, b in enumerate(row):
                            if b.get("text") == removed_text:
                                del row[i]
                                if not row:
                                    rows.remove(row)
                                removed = True
                                break
                        if removed:
                            break
                    config["button_configs"] = btns
                    config["rows"] = rows

                    if "color_pattern" in config and btn_idx < len(config["color_pattern"]):
                        del config["color_pattern"][btn_idx]
                    save_cycles()

                    await apply_cycle_now(client, cycle_key)
                    await callback_query.answer(f"🗑 Кнопка «{removed_text}» удалена", show_alert=False)
                    await _show_color_config(client, msg.chat.id, msg.id, cycle_key)

    elif data.startswith("btn_delete_"):
        cycle_key = data.replace("btn_delete_", "")
        if cycle_key in cycles_cache:
            del cycles_cache[cycle_key]
            save_cycles()
            await callback_query.answer("🗑 Удалено", show_alert=False)
            await _show_cycles_list(client, msg.chat.id, msg.id)

    return True


def register(app):
    MY_USER_ID_LOCAL = MY_USER_ID
    load_cycles()

    start_cycle()

    @app.on_message(filters.command("buttons") & filters.user(MY_USER_ID_LOCAL))
    async def buttons_menu(client, message):
        await _send_main_menu(client, message.chat.id)

    @app.on_message(filters.text & filters.user(MY_USER_ID_LOCAL) & filters.private)
    async def handle_pending_input(client, message):
        cid = message.chat.id
        if cid not in _pending_setup or _pending_setup[cid].get("step") != "awaiting_input":
            return

        text = message.text.strip()

        forward_origin = getattr(message, 'forward_origin', None)
        if forward_origin:
            source_chat = getattr(forward_origin, 'chat', None)
            source_msg_id = getattr(forward_origin, 'message_id', None)
            if source_chat and source_msg_id:
                src_chat_id = getattr(source_chat, 'id', None) or getattr(source_chat, 'sender_chat_id', None)
                if src_chat_id:
                    key = f"{src_chat_id}_{source_msg_id}"
                    await _setup_cycle_from_message(client, message, src_chat_id, source_msg_id, key)
                    return

        parts = text.split()
        if len(parts) >= 2:
            chat_identifier = parts[0]
            try:
                msg_id_val = int(parts[1])
            except ValueError:
                await message.reply("❌ ID сообщения должен быть числом.")
                return

            if chat_identifier.startswith('@'):
                key = f"{chat_identifier}_{msg_id_val}"
                await _setup_cycle_from_message(client, message, chat_identifier, msg_id_val, key)
                return

            try:
                chat_id_val = int(chat_identifier)
                key = f"{chat_id_val}_{msg_id_val}"
                await _setup_cycle_from_message(client, message, chat_id_val, msg_id_val, key)
                return
            except ValueError:
                pass


async def _send_main_menu(client, chat_id):
    total = len(cycles_cache)
    active = sum(1 for c in cycles_cache.values() if c.get("enabled", False))

    text = (
        "**🌀 Управление переливом кнопок (Telebot Core)**\n\n"
        "Кнопки в твоём канале переливаются через синхронное ядро Telebot.\n"
        "📊 **Всего циклов:** {total} | **Активно:** {active}"
    ).format(total=total, active=active)

    buttons = [[
        InlineKeyboardButton("➕ Добавить", callback_data="btn_add_cycle"),
        InlineKeyboardButton("📋 Список", callback_data="btn_cycles_list"),
    ]]
    await client.send_message(chat_id, text, reply_markup=InlineKeyboardMarkup(buttons))


async def _show_main_menu(client, chat_id, msg_id):
    total = len(cycles_cache)
    active = sum(1 for c in cycles_cache.values() if c.get("enabled", False))
    text = (
        "**🌀 Управление переливом кнопок (Telebot Core)**\n\n"
        "📊 **Всего циклов:** {total} | **Активно:** {active}"
    ).format(total=total, active=active)

    buttons = [[
        InlineKeyboardButton("➕ Добавить", callback_data="btn_add_cycle"),
        InlineKeyboardButton("📋 Список", callback_data="btn_cycles_list"),
    ]]
    await client.edit_message_text(chat_id, msg_id, text, reply_markup=InlineKeyboardMarkup(buttons))


async def _show_cycles_list(client, chat_id, msg_id):
    if not cycles_cache:
        await client.edit_message_text(
            chat_id, msg_id, "**📋 Список переливов**\n\nНет активных циклов.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Назад", callback_data="btn_main_menu"),
                InlineKeyboardButton("➕ Добавить", callback_data="btn_add_cycle"),
            ]])
        )
        return

    text_lines = ["**📋 Список переливов:**\n"]
    buttons = []

    for key, config in cycles_cache.items():
        text_lines.append(format_cycle_info(key, config))
        btn_text = "🟢" if config.get("enabled", False) else "🔴"
        btn_text += f" {str(key).split('_')[-1]}"
        buttons.append([
            InlineKeyboardButton(btn_text, callback_data=f"btn_config_{key}"),
            InlineKeyboardButton("⏹" if config.get("enabled") else "▶️", callback_data=f"btn_toggle_{key}"),
        ])

    buttons.append([
        InlineKeyboardButton("🔙 Назад", callback_data="btn_main_menu"),
        InlineKeyboardButton("➕ Добавить", callback_data="btn_add_cycle"),
    ])
    await client.edit_message_text(chat_id, msg_id, "\n".join(text_lines), reply_markup=InlineKeyboardMarkup(buttons))


async def _show_color_config(client, chat_id, msg_id, cycle_key):
    config = cycles_cache.get(cycle_key)
    if not config:
        return

    button_configs = config.get("button_configs", [])
    pattern = config.get("color_pattern", ["danger", "primary", "success"])
    enabled = config.get("enabled", False)

    text_parts = [f"**⚙️ Настройка перелива (Telebot Core)**\n"]
    text_parts.append(f"**Статус:** {'🟢 Активен' if enabled else '🔴 Остановлен'}")
    text_parts.append(f"**ID сообщения:** `{config.get('message_id')}`\n")

    for i, btn in enumerate(button_configs):
        color_name = pattern[i] if i < len(pattern) else "default"
        text_parts.append(f"{i+1}. {STYLE_EMOJIS.get(color_name, '⚪️')} {btn.get('text')} — {STYLE_NAMES.get(color_name)}")

    color_buttons = []
    for i, btn in enumerate(button_configs):
        btn_text = btn.get("text")[:10]
        color_buttons.append([
            InlineKeyboardButton(f"{i+1}. 🔴", callback_data=f"btn_color_{cycle_key}|{i}|danger"),
            InlineKeyboardButton(f"{i+1}. 🔵", callback_data=f"btn_color_{cycle_key}|{i}|primary"),
            InlineKeyboardButton(f"{i+1}. 🟢", callback_data=f"btn_color_{cycle_key}|{i}|success"),
        ])
        color_buttons.append([InlineKeyboardButton(f"🗑 Удалить «{btn_text}»", callback_data=f"btn_remove_button_{cycle_key}|{i}")])

    color_buttons.append([InlineKeyboardButton("▶️ Запустить" if not enabled else "⏹ Остановить", callback_data=f"btn_toggle_{cycle_key}")])
    color_buttons.append([InlineKeyboardButton("🗑 Удалить весь цикл", callback_data=f"btn_delete_{cycle_key}")])
    color_buttons.append([InlineKeyboardButton("🔙 К списку", callback_data="btn_cycles_list")])

    await client.edit_message_text(chat_id, msg_id, "\n".join(text_parts), reply_markup=InlineKeyboardMarkup(color_buttons))


async def _setup_cycle_from_message(client, message, chat_id_val, msg_id_val, key):
    try:
        resolved_chat = await client.get_chat(chat_id_val)
        chat_id_str = str(resolved_chat.id)
    except Exception:
        await message.reply("❌ Канал не найден.")
        return

    try:
        target_msg = await client.get_messages(resolved_chat.id, int(msg_id_val))
    except Exception as e:
        await message.reply(f"❌ Ошибка получения сообщения: {e}")
        return

    if not target_msg or not target_msg.reply_markup:
        await message.reply("❌ Сообщение или кнопки не найдены.")
        return

    rows = []
    flat_configs = []
    for row in target_msg.reply_markup.inline_keyboard:
        row_data = []
        for btn in row:
            btn_data = {"text": btn.text}
            if btn.url: btn_data["url"] = btn.url
            if btn.callback_data: btn_data["callback_data"] = btn.callback_data
            row_data.append(btn_data)
            flat_configs.append(btn_data)
        rows.append(row_data)


    cycle_entry = new_cycle_entry(chat_id_str, msg_id_val, flat_configs, rows=rows)
    cycles_cache[key] = cycle_entry
    save_cycles()


    await apply_cycle_now(client, key)
    start_cycle()

    if message.chat.id in _pending_setup:
        del _pending_setup[message.chat.id]

    sent = await client.send_message(message.chat.id, f"✅ **Перелив через Telebot успешно настроен для поста {msg_id_val}!**")
    await _show_color_config(client, sent.chat.id, sent.id, key)