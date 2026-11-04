# Трекер цен: ноутбуки на Kaspi.kz

## Зачем

Хочу купить ноутбук и поймать момент, когда на Kaspi будет скидка.

## Контракт

- regular_price — unitPriceBeforeDiscount (если нет — price)
- sale_price — price, если он ниже regular_price; иначе null (скидки нет)
- has_credit — есть ли рассрочка (рассрочка / Kaspi Red / кредит) на карточке товара; boolean.

## Ссылки

- Каталог ноутбуков в Kaspi Магазине: https://kaspi.kz/shop/c/notebooks/
- Пример карточки товара (ASUS X515EA, 15.6", 16 ГБ / SSD 512 ГБ): https://kaspi.kz/shop/p/asus-15-6-16-gb-ssd-512-gb-dos-x515ea-bq970-90nb0ty2-m02zn0-108345103/?c=750000000
  - `108345103` — ID товара (последнее число в URL)
  - `c=750000000` — код города (Алматы)
