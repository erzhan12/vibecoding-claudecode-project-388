"""Тесты правила regular_price / sale_price из скилла extract-price (без сети)."""

import importlib.util
import json
import subprocess
import sys
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / ".claude" / "skills" / "extract-price" / "compute_prices.py"

_spec = importlib.util.spec_from_file_location("compute_prices", SCRIPT)
compute_prices_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(compute_prices_module)
compute_prices = compute_prices_module.compute_prices
PriceError = compute_prices_module.PriceError


def D(text):
    return Decimal(text)


def current_price(regular, sale):
    """Текущая цена по контракту TASK.md: sale_price, а если его нет — regular_price."""
    return sale if sale is not None else regular


class DiscountTest(unittest.TestCase):
    def test_discount_when_before_discount_is_higher(self):
        # Rynex NT1805, 2026-11-06: price 149900, unitPriceBeforeDiscount 400000.
        self.assertEqual(compute_prices(149900, 400000), (D("400000.00"), D("149900.00")))

    def test_discount_with_kopecks_and_strings(self):
        self.assertEqual(
            compute_prices("238 570 ₸", "270 217 ₸"),
            (D("270217.00"), D("238570.00")),
        )

    def test_discount_by_one_kopeck(self):
        self.assertEqual(compute_prices("99999.99", "100000"), (D("100000.00"), D("99999.99")))


class EqualPricesTest(unittest.TestCase):
    def test_equal_prices_mean_no_discount(self):
        self.assertEqual(compute_prices(160000, 160000), (D("160000.00"), None))

    def test_zero_before_discount_means_no_discount(self):
        # Kaspi sends unitPriceBeforeDiscount: 0 when there is no discount (HYDRA Home H20).
        self.assertEqual(compute_prices(160000, 0), (D("160000.00"), None))

    def test_missing_before_discount_means_no_discount(self):
        for missing in (None, "", "null", "undefined", -5):
            with self.subTest(missing=missing):
                self.assertEqual(compute_prices(239898, missing), (D("239898.00"), None))


class PriceAboveBeforeDiscountTest(unittest.TestCase):
    def test_stale_lower_before_discount_is_ignored(self):
        # ASUS VivoBook 15 X1502VA, 2026-11-06: price 449997, unitPriceBeforeDiscount 449477,
        # Kaspi shows discount 0. The buyer pays 449997: it must not become 449477.
        regular, sale = compute_prices(449997, 449477)
        self.assertEqual((regular, sale), (D("449997.00"), None))

    def test_much_lower_before_discount_is_ignored(self):
        self.assertEqual(compute_prices(200000, 1), (D("200000.00"), None))


class InvariantTest(unittest.TestCase):
    CASES = [
        (149900, 400000),
        (160000, 160000),
        (160000, 0),
        (239898, None),
        (449997, 449477),
        ("99999.99", "100000"),
        ("259990.50", "289990"),
    ]

    def test_current_price_always_equals_price(self):
        for price, before in self.CASES:
            with self.subTest(price=price, before=before):
                regular, sale = compute_prices(price, before)
                self.assertEqual(current_price(regular, sale), Decimal(str(price)).quantize(D("0.01")))

    def test_sale_is_below_regular_when_present(self):
        for price, before in self.CASES:
            with self.subTest(price=price, before=before):
                regular, sale = compute_prices(price, before)
                if sale is not None:
                    self.assertLess(sale, regular)


class ErrorTest(unittest.TestCase):
    def test_missing_or_invalid_price_is_error(self):
        # ASUS X515EA, out of stock: no price in the card, unitPriceBeforeDiscount 0.
        for price in (None, 0, "undefined", "abc", -1, True):
            with self.subTest(price=price):
                with self.assertRaises(PriceError):
                    compute_prices(price, 0)


class CliTest(unittest.TestCase):
    def run_cli(self, *args):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), *args], capture_output=True, text=True, check=False
        )
        return result.returncode, json.loads(result.stdout)

    def test_cli_discount(self):
        self.assertEqual(
            self.run_cli("149900", "400000"),
            (0, {"regular_price": "400000.00", "sale_price": "149900.00"}),
        )

    def test_cli_price_above_before_discount(self):
        self.assertEqual(
            self.run_cli("449997", "449477"),
            (0, {"regular_price": "449997.00", "sale_price": None}),
        )

    def test_cli_error(self):
        self.assertEqual(self.run_cli("null", "0"), (1, {"error": "prices not found in page data"}))


if __name__ == "__main__":
    unittest.main()
