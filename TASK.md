# Трекер цен: ноутбуки на Kaspi.kz

## Зачем

Хочу купить ноутбук и поймать момент, когда на Kaspi будет скидка.

## Контракт

- price — цена, по которой товар продаётся сейчас (фактическая цена покупки); unitPriceBeforeDiscount — цена до скидки (0 или нет поля — скидки нет)
- regular_price — unitPriceBeforeDiscount, если он больше price (есть скидка); иначе price
- sale_price — price, если unitPriceBeforeDiscount больше price; иначе null (скидки нет)
- Текущая цена (sale_price, а если null — regular_price) всегда равна price. Если unitPriceBeforeDiscount равен price или меньше него (устаревшее значение), скидки нет и regular_price = price: фактическая цена не занижается.
- has_credit — есть ли рассрочка; берётся из `loanAvailable` каталожного API Kaspi по ID товара (неофициальный endpoint). boolean, а если запрос не удался — null (цены при этом возвращаются).

## Ссылки

- Каталог ноутбуков в Kaspi Магазине: https://kaspi.kz/shop/c/notebooks/
- Пример карточки товара в наличии, со скидкой (ASUS VivoBook 15 X1502VA-BQ1274, 15.6", 16 ГБ / SSD 512 ГБ): https://kaspi.kz/shop/p/asus-vivobook-15-x1502va-bq1274-15-6-intel-core-i5-13420h-16-gb-ssd-512-gb-uhd-graphics-bez-os-90nb10t2-m01th0-serebristyi-142645394/?c=750000000
  - `142645394` — ID товара (последнее число в URL)
  - `c=750000000` — код города (Алматы)

## Отслеживаемые ноутбуки

Единственный источник списка товаров (семь карточек, Алматы, `c=750000000`) —
раздел «Tracked URLs» скилла [`tracker`](.claude/skills/tracker/SKILL.md). Здесь
список не дублируется: чтобы добавить или убрать товар, меняйте только скилл.
Пример карточки — выше, в разделе «Ссылки».
