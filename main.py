"""
Telegram Bot — Entry Point
"""
import ssl
import socket
import asyncio
import os
from pyrogram import Client
from pyrogram.session import Session

ssl._create_default_https_context = ssl._create_unverified_context

original_connect = socket.socket.connect
Session.IPv6 = False


def patched_connect(self, address):
    host, port = address
    if port == 443 or port == 80 or port == 5222:
        if isinstance(host, str):
            if host.startswith('149.154.'):
                host = '149.154.175.100'
        elif host in ['149.154.167.50', '149.154.167.51', '149.154.166.110', '149.154.175.101']:
            host = '149.154.175.100'
    return original_connect(self, (host, port))


socket.socket.connect = patched_connect
Session.TIMEOUT = 30
print("✅ Сокет-патч активирован")

from config import API_ID, API_HASH, BOT_TOKEN

app = Client(
    "my_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    proxy={
        "scheme": "socks5",
        "hostname": "127.0.0.1",
        "port": 9050
    },
    ipv6=False,
    test_mode=False,
    sleep_threshold=30
)

from config import (
    DELETED_MSGS_FILE, EDITED_MSGS_FILE, CHATS_FILE,
    DELETED_CHATS_FILE, BASE_FILE,
    MEDIA_FOLDER, DATA_FOLDER, CHATS_FOLDER
)
from storage import MessageStorage
from database import PersonDatabase

os.makedirs(MEDIA_FOLDER, exist_ok=True)
os.makedirs(DATA_FOLDER, exist_ok=True)
os.makedirs(CHATS_FOLDER, exist_ok=True)

deleted_storage = MessageStorage(DELETED_MSGS_FILE, save_interval=60)
edited_storage = MessageStorage(EDITED_MSGS_FILE, save_interval=60)
chats_storage = MessageStorage(CHATS_FILE, save_interval=60)
deleted_chats_storage = MessageStorage(DELETED_CHATS_FILE, save_interval=60)
db = PersonDatabase(BASE_FILE)

from handlers import register_all

register_all(
    app,
    deleted_storage=deleted_storage,
    edited_storage=edited_storage,
    chats_storage=chats_storage,
    deleted_chats_storage=deleted_chats_storage,
    db=db
)

async def main():
    try:
        await app.start()
        print("✅ Pyrogram клиент запущен")

        from background import start_background_tasks
        start_background_tasks(
            app,
            deleted_storage=deleted_storage,
            edited_storage=edited_storage,
            chats_storage=chats_storage,
            deleted_chats_storage=deleted_chats_storage
        )

        import subprocess
        import sys
        import atexit
        import signal

        script_path = os.path.join(os.path.dirname(__file__), "1bot.py")
        sub_process = None

        if os.path.exists(script_path):
            sub_process = subprocess.Popen(
                [sys.executable, script_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            print("🌀 [ПЕРЕЛИВ] Изолированный 1bot.py УСПЕШНО ЗАПУЩЕН И ПРИВЯЗАН К СИСТЕМЕ!")

            def kill_child_process():
                if sub_process and sub_process.poll() is None:
                    print("\n🌀 [ПЕРЕЛИВ] Системный перехват: Глушу зависимый 1bot.py...")
                    sub_process.terminate()
                    sub_process.wait()
                    print("🛑 [ПЕРЕЛИВ] 1bot.py полностью уничтожен в системе.")

            atexit.register(kill_child_process)

            def signal_handler(sig, frame):
                sys.exit(0)

            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
        else:
            print(f"❌ [ПЕРЕЛИВ] Файл {script_path} не найден!")

        print("=" * 60)
        print("🚀 БОТ ЗАПУЩЕН И ГОТОВ К РАБОТЕ (Нажми Ctrl+C для полной остановки)")
        print("=" * 60)

        while True:
            await asyncio.sleep(3600)

    except Exception as e:
        print(f"💥 КРИТИЧЕСКАЯ ОШИБКА В МЕЙНЕ: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass