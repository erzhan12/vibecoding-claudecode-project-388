# Трекер цен: ноутбуки на Kaspi.kz

## Зачем

Хочу купить ноутбук и поймать момент, когда на Kaspi будет скидка.

## Контракт

- regular_price — unitPriceBeforeDiscount (если нет — price)
- sale_price — price, если он ниже regular_price; иначе null (скидки нет)
- has_credit — есть ли рассрочка; берётся из `loanAvailable` каталожного API Kaspi по ID товара (неофициальный endpoint). boolean, а если запрос не удался — null (цены при этом возвращаются).

## Ссылки

- Каталог ноутбуков в Kaspi Магазине: https://kaspi.kz/shop/c/notebooks/
- Пример карточки товара в наличии, со скидкой (ASUS VivoBook 15 X1502VA-BQ1274, 15.6", 16 ГБ / SSD 512 ГБ): https://kaspi.kz/shop/p/asus-vivobook-15-x1502va-bq1274-15-6-intel-core-i5-13420h-16-gb-ssd-512-gb-uhd-graphics-bez-os-90nb10t2-m01th0-serebristyi-142645394/?c=750000000
  - `142645394` — ID товара (последнее число в URL)
  - `c=750000000` — код города (Алматы)
- Карточка не в наличии (для проверки ошибки, ASUS X515EA): https://kaspi.kz/shop/p/asus-15-6-16-gb-ssd-512-gb-dos-x515ea-bq970-90nb0ty2-m02zn0-108345103/?c=750000000
