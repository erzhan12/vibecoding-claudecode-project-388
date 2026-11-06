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
{ "regular_price": <positive decimal, KZT>, "sale_price": <positive decimal, KZT> | null, "has_credit": <boolean> | null }
```

Field meaning in the Kaspi card: `price` is the price the product is sold for **now** (what the buyer pays); `unitPriceBeforeDiscount` is the price before a discount, `0` / absent when there is none.

- `regular_price`: `unitPriceBeforeDiscount` if it is **greater than** `price` (there is a discount), otherwise `price`.
- `sale_price`: `price` if `unitPriceBeforeDiscount` is greater than `price`, otherwise `null` (no discount).
- Invariant: the current price, `sale_price` if it is not `null`, otherwise `regular_price`, always equals `price`. The purchase price is never understated, even when `unitPriceBeforeDiscount` is stale and lower than `price`.
- `has_credit`: `loanAvailable` of this product from the Kaspi catalog API (installments / рассрочка / Kaspi Red). `null` if that request fails or the product is not found there. This never turns the result into an error: the prices are still returned.

## Extraction logic

1. Fetch the page HTML with a normal browser User-Agent. Default city code is `750000000` (Almaty): if the URL has no `c=` parameter, add `?c=750000000`; if it has one, keep it.

   ```bash
   curl -sSL --compressed -m 30 \
     -A "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36" \
     -H "Accept-Language: ru-RU,ru;q=0.9" \
     "<url>"
   ```

2. Prices are not in visible text: take them from the product object embedded in the page's inline state, the `"card":{"id":"<product id>", ...}` object, fields `price` (number) and `unitPriceBeforeDiscount`. Do not use the JSON-LD `"price"` (it is a string and is `"undefined"` when the product is out of stock) or values of recommended products and other offers.
3. Normalize: remove spaces, non-breaking spaces and `₸`, then convert to a number with 2 decimals (`"289 990 ₸"` becomes `289990.00`).
4. Compute the fields with [`compute_prices.py`](compute_prices.py) (same folder), passing the two raw values from the card:

   ```bash
   python3 .claude/skills/extract-price/compute_prices.py <price> <unitPriceBeforeDiscount>
   ```

   It prints `{"regular_price": "...", "sale_price": "..." | null}` or `{"error": "prices not found in page data"}` (exit code 1). The rule it implements:
   - treat `unitPriceBeforeDiscount` of `0`, `null` or absent as missing (Kaspi sends `0` when there is no discount);
   - **discount** (`unitPriceBeforeDiscount > price`): `regular_price` = `unitPriceBeforeDiscount`, `sale_price` = `price`;
   - **no discount** (missing, or `unitPriceBeforeDiscount == price`): `regular_price` = `price`, `sale_price` = `null`;
   - **`unitPriceBeforeDiscount < price`** (stale value; Kaspi itself shows `discount: 0` for such cards): there is no discount, `regular_price` = `price`, `sale_price` = `null`. Never put the lower stale value into `regular_price`: that would understate what the buyer pays.

   Do not recompute these by hand. Tests: `tests/test_compute_prices.py`.
   - `has_credit`: see "has_credit source" below. Do this step only after both prices are valid.
5. Check the result: both prices must be positive numbers. Otherwise treat it as a failure. If the JSON-LD says `"availability": "OutOfStock"` and the card has no valid `price`, the reason is `product unavailable (out of stock)`.
6. On failure (page not loaded, product unavailable, prices not found) return only:

   ```json
   { "error": "<short reason>", "url": "<input url>" }
   ```

   Never invent or estimate prices to fill the fields. Reject any input that is not a single `kaspi.kz/shop/p/...` URL with the same error shape.

## has_credit source

The product page HTML has **no per-product installment field**. The words рассрочка / кредит / Kaspi Red appear only in the generic SEO text of `<head>` (`<meta name="description">`, `og:*`), identically on every page, including out-of-stock ones. **Never derive `has_credit` from `<head>`/meta text**: it would always be `true`.

Instead, use the `loanAvailable` flag from the Kaspi catalog API, looked up by product ID.

> **Unofficial endpoint.** `/yml/product-view/pl/results` is not a documented public API. It is the endpoint Kaspi's own catalog front end calls, and it may change, require other headers or be rate-limited at any time. That is why a failure here yields `has_credit: null` and not an error.

1. Product ID = the last number in the URL path (`.../...-142645394/?c=...` gives `142645394`). City = the `c=` value of the URL (default `750000000`).
2. Request (note: no category filter; `q` is empty and the ID goes into `text`):

   ```bash
   curl -sS --compressed -m 20 \
     -A "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36" \
     -H "Accept: application/json, text/*" \
     -H "Referer: https://kaspi.kz/shop/c/notebooks/" \
     -H "X-KS-City: <city>" \
     "https://kaspi.kz/yml/product-view/pl/results?page=0&q=&text=<product id>&sort=relevance&qs=&ui=d&i=-1&c=<city>"
   ```

3. In the JSON `data` array, find the item whose `id` **equals** the product ID exactly (the search is fuzzy and may return other products when the ID is not found). `has_credit` = its `loanAvailable` (boolean).
4. If the request fails (non-200, timeout, invalid JSON), `data` has no exact match, or `loanAvailable` is not a boolean, set `has_credit: null`. Keep `regular_price` and `sale_price` as they are.

Observed so far: `loanAvailable` was `true` for all 48 laptops checked in the catalog. It has not been observed as `false` yet.

## Examples

The numbers below are illustrative, not real Kaspi data.

Success, with a discount and installments:

```json
{ "regular_price": 289990.00, "sale_price": 259990.00, "has_credit": true }
```

Success, `unitPriceBeforeDiscount` (449477) is lower than `price` (449997): no discount, the current price is `price`:

```json
{ "regular_price": 449997.00, "sale_price": null, "has_credit": true }
```

Success, no discount (`sale_price` is `null`):

```json
{ "regular_price": 259990.00, "sale_price": null, "has_credit": true }
```

Success, prices found but the catalog API request for `has_credit` failed (`has_credit` is `null`, not an error):

```json
{ "regular_price": 289990.00, "sale_price": 259990.00, "has_credit": null }
```

Error:

```json
{ "error": "prices not found in page data", "url": "https://kaspi.kz/shop/p/example-108345103/?c=750000000" }
```
