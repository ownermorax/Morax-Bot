import json
import os

from config import WEB_JSON

active_tasks = {}


def load_web_data():
    if not os.path.exists(WEB_JSON):
        return {}
    try:
        with open(WEB_JSON, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def save_web_data(data):
    with open(WEB_JSON, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)