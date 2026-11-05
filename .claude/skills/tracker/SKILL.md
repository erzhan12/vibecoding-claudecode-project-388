---
name: tracker
description: Runs a full price check over the hard-coded list of Kaspi.kz product URLs, returns one price table for all products, compares it with the previous run read from tracker-data (diff by URL on regular_price, sale_price, has_credit), keeps only the changes that are significant under the rules in KNOWLEDGE.md and writes the run snapshot as YYYY-MM-DD.json (Asia/Almaty date) to the root of the private erzhan12/tracker-data repository through GitHub MCP tools (mcp__github__*): in a cloud session the built-in session GitHub integration, with tracker-data added to the session with write access; locally, the github server from .mcp.json with GITHUB_PAT. Use when asked to run the tracker or check prices of all tracked laptops. Later this skill will also notify via Telegram.
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

Then compare the run with the previous run and print only significant changes (see "Compare with previous run"), save the snapshot (see "Save snapshot to tracker-data") and finish with the saved file path and the commit SHA and link.

## Compare with previous run

Compare this run with the previous run stored in `erzhan12/tracker-data` (same repository and GitHub MCP tools as in "Save snapshot to tracker-data"), then keep only the significant changes. Three stages: find the previous run, compute the diff, filter it with the rules from [`KNOWLEDGE.md`](../../../KNOWLEDGE.md).

Do all of it **before** saving the new snapshot: saving can overwrite the file that is the previous run.

### 1. Find the previous run

1. List the repository root with `get_file_contents` (path `/`, `main`).
2. Keep only files named exactly `YYYY-MM-DD.json` (other files such as `README.md` are ignored).
3. Take the one with the **latest date** and read it with `get_file_contents`. This is the previous run. It can be today's file from an earlier run today: it is read before this run overwrites it.
4. If that file is unreadable or not valid JSON in the snapshot format, try the next latest one.
5. If there are no snapshot files at all, this is the **first run**: print `Previous run: none (first run, nothing to compare)`, skip stages 2 and 3, and go on to saving.

### 2. Compute the diff

Match products by `url` (exact string). Then, for each URL:

- in this run but not in the previous one → change `new product`;
- in the previous run but not in this one → change `removed from list`;
- in both → compare field by field:
  - `error`: ok → error, error → ok, or error in both;
  - if neither row has an `error`, compare `regular_price`, `sale_price` and `has_credit`, each on its own. For each field that differs, record `field`, `old`, `new`; for prices also `Δ = new − old` and `Δ % = Δ / old × 100`.

The diff is the full list of field changes per product, before any filtering. Never fill an error row with guessed or old values.

### 3. Apply the significance rules

Read [`KNOWLEDGE.md`](../../../KNOWLEDGE.md) (project root) and apply its rules to every change in the diff: price threshold, discount started / ended, credit changed, availability, new / removed product. Do not hard-code the rules or the threshold in this skill: `KNOWLEDGE.md` is the single source; if it changes, follow the new version.

Keep only the changes the rules call significant and **drop everything else**: changes under the price threshold (for example kopeck-level fluctuations), `has_credit` going to or from `null`, error in both runs, and so on.

### Output

After the run table and its summary line, print only the significant changes, never the full price list again:

```markdown
Previous run: 2026-11-04.json (run_at 2026-11-04T18:20:11+05:00)

| product | change | old | new | Δ |
|---------|--------|-----|-----|---|
| [142645394](https://kaspi.kz/shop/p/...-142645394/?c=750000000) | discount started | null | 259990.00 | |
| [115019992](https://kaspi.kz/shop/p/...-115019992/?c=750000000) | regular_price down | 160000.00 | 155000.00 | −5000.00 (−3.1 %) |
| [108345103](https://kaspi.kz/shop/p/...-108345103/?c=750000000) | back in stock | error: product unavailable (out of stock) | 199990.00 / null | |
| [107333284](https://kaspi.kz/shop/p/...-107333284/?c=750000000) | credit lost | true | false | |

Significant changes: 4 (in 4 products). Dropped as insignificant: 2.
```

(Numbers are illustrative.)

- `product`: the product ID from the URL, linked to the full URL.
- `change`: what happened, in the words of `KNOWLEDGE.md`: `regular_price up/down`, `sale_price up/down`, `discount started`, `discount ended`, `credit gained`, `credit lost`, `back in stock`, `became unavailable`, `new product`, `removed from list`.
- `old` / `new`: the values of that field; for availability changes, the error reason or `regular_price / sale_price`.
- Rows in the order of the tracked URL list, removed products last. A product can have several rows.
- If nothing is significant, print `No significant changes since <previous file>.` instead of the table, still followed by the `Dropped as insignificant: M` count.

Only these significant changes will be sent to Telegram in a later step; this skill does not send anything yet.

The comparison is output only: it does not change the run table or the snapshot format. A failed comparison (previous snapshot unreadable, GitHub MCP unavailable) never blocks saving the snapshot: report `Previous run: comparison failed: <reason>` and continue.

## Save snapshot to tracker-data

After the run table is complete, store it in the private repository `erzhan12/tracker-data` with the GitHub MCP tools `mcp__github__get_file_contents` and `mcp__github__create_or_update_file`. Which server answers those tools depends on where the skill runs:

- **Cloud session (main path).** The tools come from the session's built-in GitHub integration. It only reaches repositories attached to the session, so `erzhan12/tracker-data` must be added to the session **with write access** (selected when the session starts, or attached with `add_repo` and `access: push`). If it is not attached, the call fails with `Access denied: repository "erzhan12/tracker-data" is not configured for this session`: ask the user to attach it, do not work around it.
- **Local run, or a cloud environment that allows `api.githubcopilot.com` (fallback).** The tools come from the `github` server in the project's [`.mcp.json`](../../../.mcp.json), authenticated with the `GITHUB_PAT` environment variable. The server must be approved for the project (for example `"enabledMcpjsonServers": ["github"]` in the uncommitted `.claude/settings.local.json`). In the cloud this server currently stays in "Pending approval", and the session proxy only lets GitHub calls reach repositories attached to the session, so it does not replace the main path there.

The steps and calls below are the same on both paths.

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

If neither path is available (no `mcp__github__*` tools, repository not attached, server not approved or not reachable) or the write fails, still return the run table, then state clearly that the snapshot was NOT saved and quote the error. Do not fall back to `gh`, `git` with a token, or raw API calls, and never print, log or write the token anywhere.

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

A later step of the project will send the significant changes found in "Compare with previous run" to Telegram; this skill does not do that yet.
