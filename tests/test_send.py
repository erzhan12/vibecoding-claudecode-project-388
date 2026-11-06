"""Тесты send.py без реальной отправки: сеть подменяется заглушками.

Запуск: python3 -m unittest discover -s tests -v
"""

import contextlib
import io
import json
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import send  # noqa: E402

FAKE_TOKEN = "000000:FAKE-TOKEN-FOR-TESTS"
FAKE_CHAT = "-100000"


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def opener_returning(payload):
    def opener(request, timeout):
        opener.request = request
        return FakeResponse(json.dumps(payload).encode())
    return opener


def opener_raising(exc):
    def opener(request, timeout):
        raise exc
    return opener


def http_error(code, payload):
    return urllib.error.HTTPError(
        f"{send.API_BASE}/bot{FAKE_TOKEN}/sendMessage", code, "err", {},
        io.BytesIO(json.dumps(payload).encode()),
    )


class LoadConfigTest(unittest.TestCase):
    def write_env(self, text):
        tmp = tempfile.NamedTemporaryFile("w", suffix=".env", delete=False, encoding="utf-8")
        tmp.write(text)
        tmp.close()
        self.addCleanup(Path(tmp.name).unlink)
        return tmp.name

    def test_reads_env_file(self):
        path = self.write_env(
            "# comment\nexport TELEGRAM_BOT_TOKEN='file-token'\nTELEGRAM_CHAT_ID=\"42\"\n"
        )
        config = send.load_config(env={}, env_file=path)
        self.assertEqual(config, {"TELEGRAM_BOT_TOKEN": "file-token", "TELEGRAM_CHAT_ID": "42"})

    def test_environment_has_priority(self):
        path = self.write_env("TELEGRAM_BOT_TOKEN=file-token\nTELEGRAM_CHAT_ID=1\n")
        config = send.load_config(env={"TELEGRAM_BOT_TOKEN": "env-token"}, env_file=path)
        self.assertEqual(config["TELEGRAM_BOT_TOKEN"], "env-token")
        self.assertEqual(config["TELEGRAM_CHAT_ID"], "1")

    def test_missing_settings(self):
        with self.assertRaises(send.SendError) as ctx:
            send.load_config(env={"TELEGRAM_BOT_TOKEN": "  "}, env_file="/nonexistent/.env")
        self.assertIn("TELEGRAM_BOT_TOKEN", str(ctx.exception))
        self.assertIn("TELEGRAM_CHAT_ID", str(ctx.exception))


class SendMessageTest(unittest.TestCase):
    def test_success(self):
        opener = opener_returning({"ok": True, "result": {}})
        send.send_message(FAKE_TOKEN, FAKE_CHAT, "привет", opener=opener)
        self.assertEqual(opener.request.get_method(), "POST")
        self.assertIn(b"chat_id=-100000", opener.request.data)

    def assert_safe_error(self, opener, expected):
        with self.assertRaises(send.SendError) as ctx:
            send.send_message(FAKE_TOKEN, FAKE_CHAT, "привет", opener=opener)
        message = str(ctx.exception)
        self.assertIn(expected, message)
        self.assertNotIn(FAKE_TOKEN, message)
        self.assertNotIn("FAKE-TOKEN", message)

    def test_unauthorized(self):
        self.assert_safe_error(
            opener_raising(http_error(401, {"ok": False, "description": "Unauthorized"})),
            "HTTP 401: Unauthorized",
        )

    def test_chat_not_found(self):
        self.assert_safe_error(
            opener_raising(http_error(400, {"ok": False, "description": "Bad Request: chat not found"})),
            "chat not found",
        )

    def test_ok_false_in_200(self):
        self.assert_safe_error(opener_returning({"ok": False, "description": "nope"}), "nope")

    def test_network_error(self):
        self.assert_safe_error(
            opener_raising(urllib.error.URLError("Name or service not known")), "нет связи"
        )

    def test_timeout(self):
        self.assert_safe_error(opener_raising(TimeoutError("timed out")), "нет связи")

    def test_token_echoed_by_api_is_hidden(self):
        self.assert_safe_error(
            opener_returning({"ok": False, "description": f"bad token {FAKE_TOKEN}"}), "***"
        )

    def test_invalid_json(self):
        def opener(request, timeout):
            return FakeResponse(b"<html>")
        self.assert_safe_error(opener, "некорректный ответ")


class MainTest(unittest.TestCase):
    def run_main(self, argv, config=None, send_side_effect=None):
        out, err = io.StringIO(), io.StringIO()
        load = mock.patch.object(
            send, "load_config",
            return_value=config or {"TELEGRAM_BOT_TOKEN": FAKE_TOKEN, "TELEGRAM_CHAT_ID": FAKE_CHAT},
        )
        if isinstance(config, Exception):
            load = mock.patch.object(send, "load_config", side_effect=config)
        with load, mock.patch.object(send, "send_message", side_effect=send_side_effect) as sm, \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = send.main(argv)
        return code, out.getvalue(), err.getvalue(), sm

    def test_success_prints_sent(self):
        code, out, err, sm = self.run_main(["привет"])
        self.assertEqual((code, out, err), (0, "Отправлено.\n", ""))
        sm.assert_called_once_with(FAKE_TOKEN, FAKE_CHAT, "привет")

    def test_no_text(self):
        for argv in ([], ["   "]):
            code, out, err, sm = self.run_main(argv)
            self.assertEqual(code, send.EXIT_USAGE)
            self.assertIn("не передан текст", err)
            sm.assert_not_called()

    def test_missing_config(self):
        code, out, err, sm = self.run_main(["привет"], config=send.SendError("не заданы настройки: X"))
        self.assertEqual(code, send.EXIT_USAGE)
        self.assertIn("не заданы настройки", err)
        sm.assert_not_called()

    def test_api_error(self):
        code, out, err, _ = self.run_main(["привет"], send_side_effect=send.SendError("HTTP 401"))
        self.assertEqual(code, send.EXIT_SEND_FAILED)
        self.assertEqual(out, "")
        self.assertIn("Ошибка: HTTP 401", err)
        self.assertNotIn(FAKE_TOKEN, err)


if __name__ == "__main__":
    unittest.main()
