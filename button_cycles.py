"""Заглушка для админки, так как перелив теперь идет через независимый 1bot.py"""
import logging

logger = logging.getLogger(__name__)

STYLE_NAMES = {
    "default": "Серый",
    "primary": "Синий",
    "danger": "Красный",
    "success": "Зелёный",
}

STYLE_EMOJIS = {
    "default": "⚪️",
    "primary": "🔵",
    "danger": "🔴",
    "success": "🟢",
}

cycles_cache = {}

def load_cycles(): pass
def save_cycles(): pass
async def apply_cycle_now(client, cycle_key): pass
def start_cycle(app=None): return None
def stop_cycle(): pass
def format_cycle_info(key, config): return ""
def new_cycle_entry(chat_id, message_id, button_configs, rows=None, pattern=None): return {}