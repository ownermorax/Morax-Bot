import logging

from pyrogram.types import InlineQueryResultArticle, InputTextMessageContent, InlineKeyboardMarkup, InlineKeyboardButton, LinkPreviewOptions

from config import MY_USER_ID

logger = logging.getLogger(__name__)


async def handle_inline_callback(client, callback_query):
    """Обрабатывает колбэки инлайн-поиска (copy_id_)"""
    if callback_query.from_user.id != MY_USER_ID:
        return False

    data = callback_query.data
    if isinstance(data, bytes):
        data = data.decode("utf-8", errors="replace")

    if data.startswith("copy_id_"):
        tg_id = data.replace("copy_id_", "")
        if tg_id:
            await callback_query.answer(f"ID: {tg_id}", show_alert=False)
        else:
            await callback_query.answer("Нет Telegram ID", show_alert=True)
        return True
    return False


def register(app, db):
    MY_USER_ID_LOCAL = MY_USER_ID

    @app.on_inline_query()
    async def inline_handler(client, inline_query):
        if inline_query.from_user.id != MY_USER_ID_LOCAL:
            await inline_query.answer(
                [],
                switch_pm_text="❌ Доступ запрещен",
                switch_pm_parameter="blocked"
            )
            return

        query = inline_query.query.strip()

        if not query:
            results = [
                InlineQueryResultArticle(
                    title="🔍 Поиск по базе данных",
                    description="Введите имя, телефон, ID или юзернейм для поиска",
                    input_message_content=InputTextMessageContent(
                        "Используйте инлайн режим для поиска:\n"
                        "• `@бот Иванов` - поиск по имени\n"
                        "• `@бот +79123456789` - поиск по телефону"
                    ),
                    thumb_url="https://telegra.ph/file/8b7d3a9f8b9c3e5a1d2e3.png"
                ),
            ]
            await inline_query.answer(results, cache_time=10, is_personal=True)
            return

        if len(query) < 2:
            results = [InlineQueryResultArticle(
                title="🔍 Введите запрос",
                description="Минимум 2 символа. Поиск по ФИО, телефону, ID, юзернейму",
                input_message_content=InputTextMessageContent(
                    "Введите имя, телефон, ID или юзернейм для поиска в базе данных"
                ),
                thumb_url="https://telegra.ph/file/8b7d3a9f8b9c3e5a1d2e3.png"
            )]
            await inline_query.answer(results, cache_time=1, is_personal=True)
            return

        search_results = db.search(query)

        if not search_results:
            results = [InlineQueryResultArticle(
                title="❌ Ничего не найдено",
                description=f"По запросу '{query}' ничего не найдено",
                input_message_content=InputTextMessageContent(
                    f"По запросу '{query}' ничего не найдено в базе данных"
                ),
                thumb_url="https://telegra.ph/file/8b7d3a9f8b9c3e5a1d2e3.png"
            )]
        else:
            results = []
            for i, result in enumerate(search_results[:20]):
                person = result['person']
                preview_lines = []
                if person['phones']:
                    preview_lines.append(f"📞 {person['phones'][0]}")
                if person['telegrams']:
                    tg = person['telegrams'][0].replace('https://t.me/', '@')
                    preview_lines.append(f"📱 {tg}")
                if person['telegram_ids']:
                    preview_lines.append(f"🆔 {person['telegram_ids'][0]}")
                if person['emails']:
                    preview_lines.append(f"📧 {person['emails'][0]}")

                preview = ' | '.join(preview_lines[:2]) if preview_lines else "Нет контактов"
                full_info = db.format_person_info(person)
                full_info += f"\n\n_Совпадение по: {result['reason']}_"
                if person['telegram_ids']:
                    full_info += f"\n\n`{person['telegram_ids'][0]}`"

                results.append(InlineQueryResultArticle(
                    title=f"{person['name'][:50]}",
                    description=preview,
                    input_message_content=InputTextMessageContent(
                        full_info,
                        link_preview_options=LinkPreviewOptions(is_disabled=True)
                    ),
                    thumb_url="https://telegra.ph/file/8b7d3a9f8b9c3e5a1d2e3.png",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(
                            "📋 Скопировать ID",
                            callback_data=f"copy_id_{person['telegram_ids'][0] if person['telegram_ids'] else ''}"
                        )
                    ]])
                ))

        await inline_query.answer(results, cache_time=0, is_personal=True)