---
name: extract-price
description: Extracts regular price, sale price and credit availability (has_credit) from a single Kaspi.kz product page URL. Use when asked to check a product's price or discount on Kaspi.
---

# extract-price

Takes one Kaspi.kz product page URL and returns its prices and installment availability as JSON.

## Contract

Input: a single Kaspi.kz product page URL (`kaspi.kz/shop/p/...`).

Output (JSON only, no free-form text before or after):

```json
{ "regular_price": <positive decimal, KZT>, "sale_price": <positive decimal, KZT> | null, "has_credit": <boolean> }
```

- `regular_price`: price before discount, from `unitPriceBeforeDiscount` (if absent, use `price`).
- `sale_price`: current price from `price` if it is lower than `regular_price`, otherwise `null` (no discount).
- `has_credit`: `true` if installments (рассрочка / Kaspi Red / кредит) are offered on the page, otherwise `false`.

## Extraction logic

1. Fetch the page HTML with a normal browser User-Agent. Default city code is `750000000` (Almaty): if the URL has no `c=` parameter, add `?c=750000000`; if it has one, keep it.

   ```bash
   curl -sSL --compressed -m 30 \
     -A "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36" \
     -H "Accept-Language: ru-RU,ru;q=0.9" \
     "<url>"
   ```

2. Prices are not in visible text: search the embedded JSON/data inside the HTML (`<script>` blocks, inline state objects) for `unitPriceBeforeDiscount` and `price`. Use the values that belong to the product itself, not to recommended or similar products or to other offers.
3. Normalize: remove spaces, non-breaking spaces and `₸`, then convert to a number with 2 decimals (`"289 990 ₸"` becomes `289990.00`).
4. Compute the fields:
   - `regular_price` = `unitPriceBeforeDiscount`, or `price` if it is absent;
   - `sale_price` = `price` only if `price < regular_price`, otherwise `null`;
   - `has_credit` = `true` if the page data or text mentions installments (рассрочка, Kaspi Red, кредит) as an available option for this product.
5. Check the result: both prices must be positive numbers. Otherwise treat it as a failure.
6. On failure (page not loaded, product unavailable, prices not found) return only:

   ```json
   { "error": "<short reason>", "url": "<input url>" }
   ```

   Never invent or estimate prices to fill the fields. Reject any input that is not a single `kaspi.kz/shop/p/...` URL with the same error shape.

## Examples

The numbers below are illustrative, not real Kaspi data.

Success, with a discount and installments:

```json
{ "regular_price": 289990.00, "sale_price": 259990.00, "has_credit": true }
```

Success, no discount (`sale_price` is `null`):

```json
{ "regular_price": 259990.00, "sale_price": null, "has_credit": true }
```

Error:

```json
{ "error": "prices not found in page data", "url": "https://kaspi.kz/shop/p/example-108345103/?c=750000000" }
```
