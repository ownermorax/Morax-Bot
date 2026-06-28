import time
import threading
import ssl
import telebot
from telebot import types
from telebot.apihelper import ApiException

from config import BOT_TOKEN_2, CHANNEL_ID, MESSAGE_ID, COLOR_PATTERN, BUTTONS_DATA

bot = telebot.TeleBot(BOT_TOKEN_2)

ssl._create_default_https_context = ssl._create_unverified_context

telebot.apihelper.proxy = {
    'http': 'socks5h://127.0.0.1:9050',
    'https': 'socks5h://127.0.0.1:9050'
}

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

is_running = True

def build_markup(step):
    markup = types.InlineKeyboardMarkup()

    for idx, btn_info in enumerate(BUTTONS_DATA):
        color_idx = (idx + step) % len(COLOR_PATTERN)
        color_name = COLOR_PATTERN[color_idx]

        button_params = {
            "text": btn_info["text"],
            "url": btn_info["url"]
        }

        if color_name in ["primary", "success", "danger", "default"]:
            button_params["style"] = color_name

        markup.add(types.InlineKeyboardButton(**button_params))
    return markup

def color_cycler_loop():
    print(f"🚀 [ВОРКЕР] Запущен цикл через Tor для канала {CHANNEL_ID}, пост №{MESSAGE_ID}")

    current_step = 0
    while is_running:
        try:
            markup = build_markup(current_step)

            bot.edit_message_reply_markup(
                chat_id=CHANNEL_ID,
                message_id=MESSAGE_ID,
                reply_markup=markup
            )
            print(f"🟢 [УСПЕХ] Цвета обновлены. Шаг: {current_step}")
            current_step = (current_step + 1) % len(COLOR_PATTERN)

        except ApiException as e:
            err = str(e).lower()
            print(err)
            if "message is not modified" in err:
                pass
            elif "message_id_invalid" in err or "message not found" in err:
                print(f"❌ [ОШИБКА API] Telegram вернул MESSAGE_ID_INVALID. Проверь токен или ID поста!")
                time.sleep(5)
            else:
                print(f"⚠️ [API EXCEPTION] Ошибка Bot API: {e}")
        except Exception as e:
            print(f"💀 [СЕТЬ] Ошибка соединения через Tor (проверь, запущен ли Tor): {e}")
            time.sleep(1)

        time.sleep(0.4)

if __name__ == "__main__":
    print("============================================================")
    print("🤖 ИЗОЛИРОВАННЫЙ БОТ ПЕРЕЛИВА ЧЕРЕЗ TOR ЗАПУЩЕН")
    print("============================================================")

    worker_thread = threading.Thread(target=color_cycler_loop, daemon=True)
    worker_thread.start()

    try:
        while worker_thread.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Останавливаю бота...")
        is_running = False