---
name: tracker
description: Runs a full price check over the hard-coded list of Kaspi.kz product URLs, returns one price table for all products and writes the run snapshot as YYYY-MM-DD.json (Asia/Almaty date) to the root of the private erzhan12/tracker-data repository through the GitHub MCP server. Use when asked to run the tracker or check prices of all tracked laptops. Later this skill will also diff against previous runs and notify via Telegram.
---

# tracker

Runs one price check over every tracked Kaspi.kz product and returns a single table for the whole run.

The tracker only orchestrates. All fetching, parsing and price rules live in the [`extract-price`](../extract-price/SKILL.md) skill; this skill must not repeat or change them.

## Tracked URLs

Taken from the "Отслеживаемые ноутбуки" section of [`TASK.md`](../../../TASK.md). Process them in this order:

1. https://kaspi.kz/shop/p/asus-vivobook-15-x1502va-bq1274-15-6-intel-core-i5-13420h-16-gb-ssd-512-gb-uhd-graphics-bez-os-90nb10t2-m01th0-serebristyi-142645394/?c=750000000
   (ASUS VivoBook 15 X1502VA-BQ1274, in stock, with a discount)
2. https://kaspi.kz/shop/p/asus-15-6-16-gb-ssd-512-gb-dos-x515ea-bq970-90nb0ty2-m02zn0-108345103/?c=750000000
   (ASUS X515EA, out of stock: expected to produce an error row, kept on purpose as an error example)
3. https://kaspi.kz/shop/p/rynex-nt1805-15-6-intel-celeron-j3455-12-gb-ssd-512-gb-intel-arc-graphics-140v-win-11-nt1805-serebristyi-176721925/?c=750000000
   (Rynex NT1805)
4. https://kaspi.kz/shop/p/hydra-home-h20-15-6-intel-pentium-n4200-12-gb-ssd-512-gb-hd-graphics-500-win-10-mkii-serebristyi-115019992/?c=750000000
   (HYDRA Home H20)
5. https://kaspi.kz/shop/p/lenovo-ideapad-3-15-6-intel-celeron-n4020-8-gb-ssd-256-gb-uhd-graphics-600-bez-os-15igl05-81wq00errk-seryi-102715483/?c=750000000
   (Lenovo IdeaPad 3 15IGL05, Celeron N4020)
6. https://kaspi.kz/shop/p/lenovo-ideapad-3-15-6-intel-core-i3-1215u-8-gb-ssd-512-gb-uhd-graphics-win-11-15iau7-82rk00ewrk-seryi-107333284/?c=750000000
   (Lenovo IdeaPad 3 15IAU7, Core i3-1215U)
7. https://kaspi.kz/shop/p/acer-aspire-3-15-6-intel-celeron-n4500-8-gb-ssd-256-gb-uhd-graphics-win-11-pro-a325-45-zn-n01si-03k-serebristyi-136300221/?c=750000000
   (Acer Aspire 3 A325-45, Celeron N4500)

To track another product, add its `kaspi.kz/shop/p/...` URL to this list and to `TASK.md`.

## Main scenario

For each URL in the list, in order:

1. Apply the `extract-price` skill to that one URL, exactly as that skill describes.
2. Take its JSON result as is. It is one of:
   - success: `{ "regular_price": ..., "sale_price": ... | null, "has_credit": ... | null }`
   - error: `{ "error": "<reason>", "url": "<url>" }`
3. Turn it into one table row (see "Run table") and move on to the next URL.

Do not fetch pages, call the catalog API or compute prices in this skill. If a value looks wrong, fix `extract-price`, not the tracker.

A failure on one URL (an `extract-price` error, a timeout, an unexpected response) must not stop the run: record it as an error row and continue with the next URL.

## Run table

Collect all results into ONE table, one row per tracked URL, in the order of the list. Columns:

| Column          | On success                          | On error                              |
|-----------------|-------------------------------------|---------------------------------------|
| `url`           | the tracked URL                     | the tracked URL                       |
| `regular_price` | `regular_price` from extract-price  | empty (`null`)                        |
| `sale_price`    | `sale_price`, or `null` if no discount | empty (`null`)                     |
| `has_credit`    | `has_credit` (`true` / `false` / `null`) | empty (`null`)                   |
| `error`         | empty                               | the `error` reason from extract-price |

Rules:

- Every tracked URL gets exactly one row, success or not. The number of rows always equals the number of tracked URLs.
- Copy values from the `extract-price` JSON without recalculating or rounding them. Prices are KZT with 2 decimals.
- Never fill an error row with guessed or old prices.
- If `extract-price` itself could not be completed for a URL, the row is an error row with a short reason (for example `extract-price failed: timeout`).

## Output

Return the full table for all tracked URLs from a single run as Markdown, with a header line giving the run time:

```markdown
Run: 2026-11-04 12:00 (Asia/Almaty)

| url | regular_price | sale_price | has_credit | error |
|-----|---------------|------------|------------|-------|
| https://kaspi.kz/shop/p/...-142645394/?c=750000000 | 289990.00 | 259990.00 | true | |
| https://kaspi.kz/shop/p/...-108345103/?c=750000000 | null | null | null | product unavailable (out of stock) |
```

(Numbers above are illustrative, not real Kaspi data. In the real output use the full URLs.)

After the table, add one summary line: how many URLs were checked, how many succeeded and how many failed.

Then save the snapshot (see "Save snapshot to tracker-data") and finish with the saved file path and the commit SHA and link.

## Save snapshot to tracker-data

After the run table is complete, store it in the private repository `erzhan12/tracker-data` through the **GitHub MCP server** (`github`, configured in the project's [`.mcp.json`](../../../.mcp.json); the token comes from the `GITHUB_PAT` environment variable).

- **Repository:** owner `erzhan12`, repo `tracker-data`, default branch `main`.
- **Path:** `YYYY-MM-DD.json` in the repository root, where the date is the run date in `Asia/Almaty` (UTC+5), for example `2026-11-05.json`.
- **Commit message:** `price run YYYY-MM-DD` (same date).

Steps:

1. Build the JSON document (format below) from the run table. Save it even if some or all URLs failed: error rows are part of the snapshot, one failed URL never cancels saving the others.
2. Call the GitHub MCP `get_file_contents` tool for that path on `main`.
   - If the file exists, take its blob `sha` (a second run on the same day overwrites that day's snapshot).
   - If it does not exist (404 / not found), there is no `sha`.
3. Call the GitHub MCP `create_or_update_file` tool with `owner`, `repo`, `path`, `branch: main`, the commit message, the JSON as plain text `content` (not base64), and `sha` only when updating.
4. Report the path and the commit SHA with its link (`https://github.com/erzhan12/tracker-data/commit/<sha>`).

If the GitHub MCP server is not available or the write fails, still return the run table, then state clearly that the snapshot was NOT saved and quote the error. Do not fall back to `gh`, `git` with a token, or raw API calls, and never print, log or write the token anywhere.

### Snapshot format

UTF-8 JSON, 2-space indent, trailing newline. Rows are in the order of the tracked URL list, with exactly the same values as the run table (numbers as JSON numbers, missing values as `null`, `error` is `null` on success):

```json
{
  "date": "2026-11-05",
  "run_at": "2026-11-05T18:00:00+05:00",
  "timezone": "Asia/Almaty",
  "currency": "KZT",
  "summary": { "checked": 7, "ok": 6, "failed": 1 },
  "items": [
    {
      "url": "https://kaspi.kz/shop/p/...-142645394/?c=750000000",
      "product_id": "142645394",
      "regular_price": 289990.00,
      "sale_price": 259990.00,
      "has_credit": true,
      "error": null
    },
    {
      "url": "https://kaspi.kz/shop/p/...-108345103/?c=750000000",
      "product_id": "108345103",
      "regular_price": null,
      "sale_price": null,
      "has_credit": null,
      "error": "product unavailable (out of stock)"
    }
  ]
}
```

(Numbers are illustrative. Use the full URLs.) `product_id` is the numeric id at the end of the URL path; it is the stable key for comparing snapshots between days.

Later steps of the project will compare the snapshot with the previous one and send significant changes to Telegram; this skill does not do that yet.
