"""Проверка таблицы «Примеры на границах» из KNOWLEDGE.md (без сети).

Правила значимости живут только в KNOWLEDGE.md, трекер применяет их сам.
Здесь — эталонная проверка ценовых правил (порог, скидка, зачёркнутая цена)
на примерах из той же таблицы: если правило или пример поменяли, а другое
забыли, тест упадёт. Плюс проверка, что tracker не хардкодит правила.
"""

import re
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE = ROOT / "KNOWLEDGE.md"
TRACKER = ROOT / ".claude" / "skills" / "tracker" / "SKILL.md"

THRESHOLD = Decimal("0.01")  # «Порог: 1 %» — сверяется с KNOWLEDGE.md в test_threshold_matches


def price_changes(old_regular, old_sale, new_regular, new_sale):
    """Значимые ценовые изменения одного товара (оба прогона без error)."""
    changes = set()

    def by_threshold(field, old, new):
        if old == new:
            return
        if abs(new - old) / old >= THRESHOLD:
            changes.add(f"{field} {'up' if new > old else 'down'}")

    discount_before = old_sale is not None
    discount_after = new_sale is not None

    if not discount_before and discount_after:
        # Одно событие: изменение regular_price в том же прогоне в него входит.
        changes.add("discount started")
    elif discount_before and not discount_after:
        changes.add("discount ended")
    elif discount_before and discount_after:
        # Зачёркнутая цена при скидке в обоих прогонах не значима никогда.
        by_threshold("sale_price", old_sale, new_sale)
    else:
        by_threshold("regular_price", old_regular, new_regular)
    return changes


def current_price(regular, sale):
    """Цена покупки по контракту TASK.md: sale_price, а если его нет — regular_price."""
    return sale if sale is not None else regular


def event_transition(old_regular, old_sale, new_regular, new_sale):
    """Что показывает строка события скидки: цена покупки до → после; None, если события нет."""
    if (old_sale is None) == (new_sale is None):
        return None
    return current_price(old_regular, old_sale), current_price(new_regular, new_sale)


def parse_price(cell):
    cell = cell.strip()
    return None if cell == "null" else Decimal(cell)


def load_examples():
    text = KNOWLEDGE.read_text(encoding="utf-8")
    block = re.search(
        r"<!-- significance-examples:start -->(.*?)<!-- significance-examples:end -->",
        text,
        re.S,
    )
    if block is None:
        raise AssertionError("в KNOWLEDGE.md нет таблицы significance-examples")
    rows = []
    for line in block.group(1).strip().splitlines()[2:]:  # без заголовка и |---|
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        number, old_r, old_s, new_r, new_s, expected, transition, _why = cells
        expected_set = set() if expected == "—" else {e.strip() for e in expected.split(",")}
        if transition == "—":
            transition = None
        else:
            before, after = transition.split("→")
            transition = (parse_price(before), parse_price(after))
        rows.append(
            (
                number,
                (parse_price(old_r), parse_price(old_s), parse_price(new_r), parse_price(new_s)),
                expected_set,
                transition,
            )
        )
    return rows


class KnowledgeExamplesTest(unittest.TestCase):
    def test_threshold_matches(self):
        text = KNOWLEDGE.read_text(encoding="utf-8")
        self.assertIn("**Порог: 1 %**", text)

    def test_examples_present(self):
        self.assertGreaterEqual(len(load_examples()), 10)

    def test_examples_follow_rules(self):
        for number, prices, expected, _transition in load_examples():
            with self.subTest(example=number):
                self.assertEqual(price_changes(*prices), expected)

    def test_examples_show_purchase_price_transition(self):
        for number, prices, _expected, transition in load_examples():
            with self.subTest(example=number):
                self.assertEqual(event_transition(*prices), transition)

    def test_examples_cover_both_discount_events_with_regular_change(self):
        kinds = set()
        for _number, (old_r, _old_s, new_r, _new_s), expected, _transition in load_examples():
            if old_r != new_r:
                kinds |= expected & {"discount started", "discount ended"}
        self.assertEqual(kinds, {"discount started", "discount ended"})

    def test_regular_price_ignored_while_discount_in_both(self):
        # Скидка в обоих, sale_price та же: зачёркнутая меняется хоть вдвое — тишина.
        for new_regular in ("150000.00", "260000.01", "299999.99", "600000.00"):
            with self.subTest(new_regular=new_regular):
                self.assertEqual(
                    price_changes(D("300000"), D("260000"), D(new_regular), D("260000")), set()
                )

    def test_regular_price_by_threshold_without_discount(self):
        self.assertEqual(price_changes(D("100000"), None, D("99000"), None), {"regular_price down"})
        self.assertEqual(price_changes(D("100000"), None, D("99000.01"), None), set())

    def test_discount_started_with_regular_change_is_one_event(self):
        # Скидка появилась, regular_price одновременно +10 %: одно событие, 100000 → 95000.
        prices = (D("100000"), None, D("110000"), D("95000"))
        self.assertEqual(price_changes(*prices), {"discount started"})
        self.assertEqual(event_transition(*prices), (D("100000"), D("95000")))

    def test_discount_ended_with_regular_change_is_one_event(self):
        # Скидка закончилась, regular_price одновременно −10 %: одно событие, 95000 → 99000.
        for new_regular in ("99000", "110000", "100000"):
            with self.subTest(new_regular=new_regular):
                prices = (D("110000"), D("95000"), D(new_regular), None)
                self.assertEqual(price_changes(*prices), {"discount ended"})
                self.assertEqual(event_transition(*prices), (D("95000"), D(new_regular)))

    def test_discount_events_always_significant(self):
        self.assertEqual(price_changes(D("100000"), None, D("100000"), D("99999.99")), {"discount started"})
        self.assertEqual(price_changes(D("100000"), D("99999.99"), D("100000"), None), {"discount ended"})


class TrackerDoesNotDuplicateRulesTest(unittest.TestCase):
    def test_tracker_points_to_knowledge(self):
        text = TRACKER.read_text(encoding="utf-8")
        self.assertIn("KNOWLEDGE.md", text)
        self.assertIsNone(
            re.search(r"(?<![\d.,])1\s?%", text), "порог не должен быть захардкожен в tracker"
        )

    def test_tracker_discount_events_show_purchase_price(self):
        text = TRACKER.read_text(encoding="utf-8")
        self.assertIn("| `discount started` | old current price | new `sale_price` |", text)
        self.assertIn("| `discount ended` | old `sale_price` | new current price |", text)
        self.assertIn("| discount started | 289990.00 | 259990.00 |", text)


def D(text):
    return Decimal(text)


if __name__ == "__main__":
    unittest.main()
