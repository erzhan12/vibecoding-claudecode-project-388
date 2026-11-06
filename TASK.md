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
- Карточка не в наличии (для проверки ошибки, ASUS X515EA): https://kaspi.kz/shop/p/asus-15-6-16-gb-ssd-512-gb-dos-x515ea-bq970-90nb0ty2-m02zn0-108345103/?c=750000000

## Отслеживаемые ноутбуки

Полный список карточек, по которым ходит трекер (Алматы, `c=750000000`):

1. ASUS VivoBook 15 X1502VA-BQ1274 (в наличии, со скидкой): https://kaspi.kz/shop/p/asus-vivobook-15-x1502va-bq1274-15-6-intel-core-i5-13420h-16-gb-ssd-512-gb-uhd-graphics-bez-os-90nb10t2-m01th0-serebristyi-142645394/?c=750000000
2. ASUS X515EA (не в наличии, пример ошибки): https://kaspi.kz/shop/p/asus-15-6-16-gb-ssd-512-gb-dos-x515ea-bq970-90nb0ty2-m02zn0-108345103/?c=750000000
3. Rynex NT1805: https://kaspi.kz/shop/p/rynex-nt1805-15-6-intel-celeron-j3455-12-gb-ssd-512-gb-intel-arc-graphics-140v-win-11-nt1805-serebristyi-176721925/?c=750000000
4. HYDRA Home H20: https://kaspi.kz/shop/p/hydra-home-h20-15-6-intel-pentium-n4200-12-gb-ssd-512-gb-hd-graphics-500-win-10-mkii-serebristyi-115019992/?c=750000000
5. Lenovo IdeaPad 3 15IGL05 (Celeron N4020, 8 ГБ / SSD 256 ГБ): https://kaspi.kz/shop/p/lenovo-ideapad-3-15-6-intel-celeron-n4020-8-gb-ssd-256-gb-uhd-graphics-600-bez-os-15igl05-81wq00errk-seryi-102715483/?c=750000000
6. Lenovo IdeaPad 3 15IAU7 (Core i3-1215U, 8 ГБ / SSD 512 ГБ): https://kaspi.kz/shop/p/lenovo-ideapad-3-15-6-intel-core-i3-1215u-8-gb-ssd-512-gb-uhd-graphics-win-11-15iau7-82rk00ewrk-seryi-107333284/?c=750000000
7. Acer Aspire 3 A325-45 (Celeron N4500, 8 ГБ / SSD 256 ГБ): https://kaspi.kz/shop/p/acer-aspire-3-15-6-intel-celeron-n4500-8-gb-ssd-256-gb-uhd-graphics-win-11-pro-a325-45-zn-n01si-03k-serebristyi-136300221/?c=750000000
