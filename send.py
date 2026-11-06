#!/usr/bin/env python3
"""Отправка текста в Telegram через Bot API.

Запуск:
    python3 send.py "текст"

Настройки TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID берутся из переменных
окружения, а если их там нет — из файла .env рядом со скриптом.
Переменные окружения имеют приоритет над .env.

Только стандартная библиотека Python.
"""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API_BASE = "https://api.telegram.org"
REQUIRED_KEYS = ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID")
TIMEOUT_SECONDS = 15

EXIT_USAGE = 2  # нет текста или настроек
EXIT_SEND_FAILED = 1  # ошибка сети или Telegram API


class SendError(Exception):
    """Ошибка, сообщение которой можно безопасно показать пользователю."""


def load_env_file(path):
    """Читает KEY=VALUE из .env. Пустые строки и комментарии пропускаются."""
    values = {}
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return values
    except OSError as exc:
        raise SendError(f"не удалось прочитать {path}: {exc.strerror}") from None

    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export "):].lstrip()
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key] = value
    return values


def load_config(env=None, env_file=None):
    """Собирает настройки: окружение важнее .env."""
    env = os.environ if env is None else env
    if env_file is None:
        env_file = Path(__file__).resolve().parent / ".env"
    file_values = load_env_file(env_file)

    config = {}
    missing = []
    for key in REQUIRED_KEYS:
        value = (env.get(key) or "").strip() or (file_values.get(key) or "").strip()
        if value:
            config[key] = value
        else:
            missing.append(key)
    if missing:
        raise SendError(
            "не заданы настройки: " + ", ".join(missing)
            + ". Укажите их в переменных окружения или в файле .env рядом со скриптом."
        )
    return config


def _hide(message, secret):
    """Страховка: вырезает токен из любого текста перед выводом."""
    return message.replace(secret, "***") if secret else message


def _api_description(body):
    try:
        data = json.loads(body.decode("utf-8", errors="replace"))
    except ValueError:
        return None
    if isinstance(data, dict):
        return data.get("description")
    return None


def send_message(token, chat_id, text, opener=urllib.request.urlopen):
    """Отправляет сообщение. При любой ошибке бросает SendError без токена."""
    url = f"{API_BASE}/bot{token}/sendMessage"
    payload = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode("utf-8")
    request = urllib.request.Request(url, data=payload, method="POST")

    try:
        with opener(request, timeout=TIMEOUT_SECONDS) as response:
            body = response.read()
    except urllib.error.HTTPError as exc:
        description = _api_description(exc.read() or b"")
        details = f"HTTP {exc.code}" + (f": {description}" if description else "")
        raise SendError(_hide(f"Telegram API вернул ошибку ({details})", token)) from None
    except urllib.error.URLError as exc:
        raise SendError(_hide(f"нет связи с Telegram API ({exc.reason})", token)) from None
    except (TimeoutError, OSError) as exc:
        raise SendError(_hide(f"нет связи с Telegram API ({exc})", token)) from None

    try:
        data = json.loads(body.decode("utf-8"))
    except ValueError:
        raise SendError("Telegram API вернул некорректный ответ") from None
    if not isinstance(data, dict) or not data.get("ok"):
        description = data.get("description") if isinstance(data, dict) else None
        raise SendError(_hide(
            "Telegram API отклонил запрос" + (f": {description}" if description else ""),
            token,
        ))


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    text = " ".join(argv).strip()
    if not text:
        print('Ошибка: не передан текст. Использование: python3 send.py "текст"',
              file=sys.stderr)
        return EXIT_USAGE

    try:
        config = load_config()
    except SendError as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return EXIT_USAGE

    try:
        send_message(config["TELEGRAM_BOT_TOKEN"], config["TELEGRAM_CHAT_ID"], text)
    except SendError as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return EXIT_SEND_FAILED

    print("Отправлено.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
