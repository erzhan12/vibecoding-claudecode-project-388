#!/usr/bin/env python3
"""Расчёт regular_price и sale_price из полей карточки Kaspi.

Запуск:
    python3 compute_prices.py <price> <unitPriceBeforeDiscount>

Печатает JSON {"regular_price": ..., "sale_price": ...} или {"error": ...}.
Правило описано в SKILL.md (раздел "Compute the fields") и в контракте TASK.md.

Только стандартная библиотека Python.
"""

import json
import sys
from decimal import Decimal, InvalidOperation

CENT = Decimal("0.01")


class PriceError(ValueError):
    """Цену нельзя посчитать: в карточке нет корректной цены."""


def normalize(value):
    """'289 990 ₸', 289990, '289990.5', None -> Decimal с 2 знаками или None.

    0, отрицательные и пустые значения считаются отсутствующими (None):
    Kaspi присылает unitPriceBeforeDiscount: 0, когда скидки нет.
    """
    if value is None or isinstance(value, bool):
        return None
    text = str(value).replace(" ", "").replace(" ", "").replace("₸", "")
    if text in ("", "null", "undefined"):
        return None
    try:
        number = Decimal(text)
    except InvalidOperation:
        return None
    if not number.is_finite() or number <= 0:
        return None
    return number.quantize(CENT)


def compute_prices(price, unit_price_before_discount):
    """Возвращает (regular_price, sale_price) как Decimal / None.

    - price — цена, по которой товар продаётся сейчас (фактическая цена покупки).
    - unitPriceBeforeDiscount — цена до скидки; 0 / null — скидки нет.

    Скидка есть, только если unitPriceBeforeDiscount строго больше price.
    Иначе (поля нет, оно равно price или меньше price — устаревшее значение)
    скидки нет и regular_price = price. Поэтому текущая цена
    (sale_price, а если его нет — regular_price) всегда равна price и никогда
    не занижается.
    """
    current = normalize(price)
    if current is None:
        raise PriceError("prices not found in page data")
    before = normalize(unit_price_before_discount)
    if before is not None and before > current:
        return before, current
    return current, None


def main(argv):
    if len(argv) != 3:
        print("usage: compute_prices.py <price> <unitPriceBeforeDiscount>", file=sys.stderr)
        return 2
    try:
        regular, sale = compute_prices(argv[1], argv[2])
    except PriceError as exc:
        print(json.dumps({"error": str(exc)}))
        return 1
    print(json.dumps({"regular_price": f"{regular:.2f}", "sale_price": None if sale is None else f"{sale:.2f}"}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
