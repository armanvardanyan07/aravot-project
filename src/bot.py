import os
import sys
import time
from pathlib import Path

import joblib
import requests


DEFAULT_MODEL_PATH = Path(__file__).resolve().parent.parent / "model.pkl"
MODEL_PATH = Path(os.getenv("MODEL_PATH", DEFAULT_MODEL_PATH))
TOKEN_ENV_NAME = "TELEGRAM_BOT_TOKEN"
LABELS_HY = {
    "politics": "Քաղաքականություն",
    "sport": "Սպորտ",
}


def setup_console_encoding():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")


def get_token():
    token = os.getenv(TOKEN_ENV_NAME)
    if not token:
        raise RuntimeError(f"Set {TOKEN_ENV_NAME}")
    return token


def api_url(token, method):
    return f"https://api.telegram.org/bot{token}/{method}"


def telegram_request(token, method, payload=None, timeout=35):
    response = requests.post(api_url(token, method), json=payload or {}, timeout=timeout)
    response.raise_for_status()
    data = response.json()
    if not data.get("ok"):
        raise RuntimeError(data)
    return data["result"]


def predict_label(model, text):
    prediction = model.predict([text])[0]
    return LABELS_HY.get(prediction, prediction)


def send_message(token, chat_id, text):
    telegram_request(token, "sendMessage", {"chat_id": chat_id, "text": text}, timeout=10)


def handle_message(token, model, message):
    chat_id = message["chat"]["id"]
    text = (message.get("text") or "").strip()

    if not text:
        send_message(token, chat_id, "Ուղարկեք հայերեն տեքստ։")
        return

    if text.startswith("/start"):
        send_message(
            token,
            chat_id,
            "Բարև։ Ուղարկեք հայերեն նախադասություն, ես կասեմ՝ Սպորտ է, թե Քաղաքականություն։",
        )
        return

    if text.startswith("/help"):
        send_message(token, chat_id, "Ուղարկեք լուրի վերնագիր կամ նախադասություն։")
        return

    send_message(token, chat_id, predict_label(model, text))


def run_bot():
    setup_console_encoding()
    token = get_token()
    model = joblib.load(MODEL_PATH)
    offset = None

    print("Bot started")

    while True:
        try:
            payload = {"timeout": 30}
            if offset is not None:
                payload["offset"] = offset

            updates = telegram_request(token, "getUpdates", payload, timeout=40)
            for update in updates:
                offset = update["update_id"] + 1
                message = update.get("message")
                if message:
                    handle_message(token, model, message)
        except KeyboardInterrupt:
            print("Bot stopped")
            break
        except Exception as exc:
            print(f"Error: {exc}", file=sys.stderr)
            time.sleep(3)


if __name__ == "__main__":
    run_bot()
