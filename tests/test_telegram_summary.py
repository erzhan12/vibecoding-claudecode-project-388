"""Воспроизводимая проверка формата Telegram-сводки агента telegram-summary.

Без сети и без вызова модели:
- эталонный рендер (render) по правилам из .claude/agents/telegram-summary.md;
- фикстуры tests/fixtures/telegram_summary/*.expected.txt — реальные ответы Haiku,
  они должны совпадать с эталоном символ в символ;
- таблица формулировок и пример в файле агента сверяются с эталоном, чтобы тест и
  агент не разошлись;
- check_reply — проверка ответа агента перед отправкой (шаг 4 в скилле tracker):
  число строк, ссылка, название и цифры цен в каждой строке.

С моделью (по желанию, платно, нужен залогиненный claude CLI):
    RUN_HAIKU_SUMMARY=1 python3 -m unittest tests.test_telegram_summary -v
запускает `claude -p --agent telegram-summary` на каждой фикстуре и сравнивает ответ
с эталоном. В Telegram ничего не отправляется.
"""

import json
import os
import re
import shutil
import subprocess
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENT_FILE = ROOT / ".claude" / "agents" / "telegram-summary.md"
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "telegram_summary"

CHANGE_TEXT = {
    "regular_price up": "цена без скидки выросла",
    "regular_price down": "цена без скидки снизилась",
    "sale_price up": "цена со скидкой выросла",
    "sale_price down": "цена со скидкой снизилась",
    "discount started": "скидка появилась",
    "discount ended": "скидка закончилась",
    "credit gained": "рассрочка появилась",
    "credit lost": "рассрочка пропала",
    "back in stock": "снова в наличии",
    "became unavailable": "недоступен (<reason>)",
    "new product": "новый товар",
    "removed from list": "убран из списка",
}
PRICE_CHANGES = {"regular_price up", "regular_price down", "sale_price up", "sale_price down"}


def format_value(value):
    if value == "unavailable":
        return "нет в наличии"
    if value == "none":
        return "—"
    number = Decimal(str(value)).quantize(Decimal("0.01"))
    integer, kopecks = f"{number:.2f}".split(".")
    text = f"{int(integer):,}".replace(",", " ")
    if kopecks != "00":
        text += "." + kopecks
    return text + " ₸"


def render(data):
    """Эталонный текст сводки для входа агента."""
    lines = [f"Kaspi: значимые изменения цен ({data['run_at']}, Алматы)", ""]
    for change in data["changes"]:
        text = CHANGE_TEXT[change["change"]].replace("<reason>", str(change.get("reason")))
        delta = ""
        if change["change"] in PRICE_CHANGES:
            pct = change["delta_pct"]
            delta = f" ({'+' if pct > 0 else '−'}{abs(pct):.1f} %)"
        lines.append(
            f"{change['name']} — {text}: {format_value(change['old'])} → "
            f"{format_value(change['new'])}{delta} — {change['url']}"
        )
    return "\n".join(lines)


def price_digits(value):
    """Цифры цены без пробелов: 259990.00 -> '259990', 259990.5 -> '259990.50'."""
    number = Decimal(str(value)).quantize(Decimal("0.01"))
    integer, kopecks = f"{number:.2f}".split(".")
    return integer if kopecks == "00" else f"{integer}.{kopecks}"


def check_reply(data, reply):
    """Проверка ответа агента перед отправкой (скилл tracker, шаг 4). Список проблем."""
    problems = []
    text = reply.strip("\n")
    if text.startswith("ERROR:"):
        return ["agent returned ERROR"]
    lines = text.split("\n")
    changes = data["changes"]
    if len(lines) != len(changes) + 2:
        problems.append(f"expected {len(changes) + 2} lines, got {len(lines)}")
        return problems
    for index, change in enumerate(changes, start=1):
        line = lines[index + 1]
        if change["url"] not in line:
            problems.append(f"line {index}: url missing or changed")
        if change["name"] not in line:
            problems.append(f"line {index}: name missing")
        compact = line.replace(" ", "").replace(" ", "")
        for key in ("old", "new"):
            value = change[key]
            if isinstance(value, (int, float)) and price_digits(value) not in compact:
                problems.append(f"line {index}: {key} price {price_digits(value)} missing")
    return problems


def load_fixture(name):
    data = json.loads((FIXTURES / f"{name}.input.json").read_text(encoding="utf-8"))
    expected = (FIXTURES / f"{name}.expected.txt").read_text(encoding="utf-8").rstrip("\n")
    return data, expected


def fixture_names():
    return sorted(p.name[: -len(".input.json")] for p in FIXTURES.glob("*.input.json"))


def agent_file():
    return AGENT_FILE.read_text(encoding="utf-8")


class FixtureTest(unittest.TestCase):
    def test_fixtures_exist(self):
        self.assertGreaterEqual(len(fixture_names()), 2)

    def test_haiku_outputs_match_reference(self):
        for name in fixture_names():
            with self.subTest(fixture=name):
                data, expected = load_fixture(name)
                self.assertEqual(render(data), expected)

    def test_fixtures_cover_every_change_kind(self):
        kinds = set()
        for name in fixture_names():
            kinds |= {c["change"].replace(" up", "").replace(" down", "") for c in load_fixture(name)[0]["changes"]}
        expected = {k.replace(" up", "").replace(" down", "") for k in CHANGE_TEXT}
        expected -= {"credit gained"}  # same line format as "credit lost"
        self.assertLessEqual(expected, kinds)

    def test_fixtures_pass_tracker_check(self):
        for name in fixture_names():
            with self.subTest(fixture=name):
                data, expected = load_fixture(name)
                self.assertEqual(check_reply(data, expected), [])


class FormatRulesTest(unittest.TestCase):
    def test_price_format(self):
        self.assertEqual(format_value(289990), "289 990 ₸")
        self.assertEqual(format_value(1250000.00), "1 250 000 ₸")
        self.assertEqual(format_value(999), "999 ₸")
        self.assertEqual(format_value(259990.5), "259 990.50 ₸")
        self.assertEqual(format_value(155000.75), "155 000.75 ₸")
        self.assertEqual(format_value("unavailable"), "нет в наличии")
        self.assertEqual(format_value("none"), "—")

    def test_change_text_table_matches_agent_file(self):
        rows = dict(re.findall(r"^\| `([a-z_ ]+)` \| `([^`]+)`", agent_file(), flags=re.M))
        rows.pop("change", None)  # table header
        self.assertEqual(rows, CHANGE_TEXT)

    def test_agent_example_matches_reference(self):
        example = agent_file().split("### Example", 1)[1]
        blocks = re.findall(r"```(json|text)\n(.*?)```", example, flags=re.S)
        example_input = json.loads(blocks[0][1])
        example_output = blocks[1][1].rstrip("\n")
        self.assertEqual(render(example_input), example_output)

    def test_agent_frontmatter(self):
        front = agent_file().split("---", 2)[1]
        self.assertIn("name: telegram-summary", front)
        self.assertRegex(front, r"(?m)^model: haiku$")
        self.assertRegex(front, r"(?m)^tools: \[\]$")
        self.assertNotIn("disallowedTools", front)


class CheckReplyTest(unittest.TestCase):
    def setUp(self):
        self.data, self.good = load_fixture("all_kinds")

    def mutate(self, old, new):
        self.assertIn(old, self.good)
        return self.good.replace(old, new, 1)

    def test_good_reply_passes(self):
        self.assertEqual(check_reply(self.data, self.good), [])
        self.assertEqual(check_reply(self.data, self.good + "\n"), [])

    def test_changed_price_fails(self):
        self.assertTrue(check_reply(self.data, self.mutate("160 000 ₸", "161 000 ₸")))

    def test_dropped_kopecks_fail(self):
        self.assertTrue(check_reply(self.data, self.mutate("259 990.50 ₸", "259 990 ₸")))

    def test_changed_url_fails(self):
        self.assertTrue(check_reply(self.data, self.mutate("?c=750000000", "?c=750000001")))

    def test_shortened_url_fails(self):
        self.assertTrue(check_reply(self.data, self.mutate("/?c=750000000", "/")))

    def test_missing_line_fails(self):
        lines = self.good.split("\n")
        self.assertTrue(check_reply(self.data, "\n".join(lines[:-1])))

    def test_preamble_fails(self):
        self.assertTrue(check_reply(self.data, "Вот сводка:\n" + self.good))

    def test_error_reply_fails(self):
        self.assertEqual(check_reply(self.data, "ERROR: changes is empty"), ["agent returned ERROR"])


@unittest.skipUnless(os.environ.get("RUN_HAIKU_SUMMARY") == "1", "set RUN_HAIKU_SUMMARY=1 to call the real agent")
class LiveHaikuTest(unittest.TestCase):
    """Реальный вызов агента через claude CLI. Ничего не отправляет в Telegram."""

    def run_agent(self, prompt):
        claude = shutil.which("claude")
        if not claude:
            self.skipTest("claude CLI not found")
        result = subprocess.run(
            [claude, "-p", "--agent", "telegram-summary", "--output-format", "json", prompt],
            cwd=ROOT, capture_output=True, text=True, timeout=300, stdin=subprocess.DEVNULL, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr[-500:])
        return json.loads(result.stdout)

    def test_agent_matches_reference(self):
        for name in fixture_names():
            with self.subTest(fixture=name):
                data, expected = load_fixture(name)
                out = self.run_agent(json.dumps(data, ensure_ascii=False))
                self.assertTrue(all("haiku" in m for m in out["modelUsage"]), list(out["modelUsage"]))
                self.assertEqual(check_reply(data, out["result"]), [])
                self.assertEqual(out["result"].strip("\n"), expected)

    def test_agent_rejects_empty_changes(self):
        out = self.run_agent('{"run_at": "2026-11-06 18:00", "changes": []}')
        self.assertTrue(out["result"].startswith("ERROR:"))


if __name__ == "__main__":
    unittest.main()
