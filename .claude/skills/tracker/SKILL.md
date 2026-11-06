---
name: tracker
description: Runs a full price check over the hard-coded list of Kaspi.kz product URLs, returns one price table for all products, compares it with the previous run read from tracker-data (diff by URL on regular_price, sale_price, has_credit), keeps only the changes that are significant under the rules in KNOWLEDGE.md and writes the run snapshot as YYYY-MM-DD.json (Asia/Almaty date) to the root of the private erzhan12/tracker-data repository through GitHub MCP tools (mcp__github__*): in a cloud session the built-in session GitHub integration, with tracker-data added to the session with write access; locally, the github server from .mcp.json with GITHUB_PAT. If there are significant changes, has the telegram-summary sub-agent (.claude/agents/telegram-summary.md, Haiku) format a short summary (one line per change: product name, old and new price, link) and sends that text to Telegram with send.py from the project root; when there are none, calls neither the agent nor send.py. Use when asked to run the tracker or check prices of all tracked laptops.
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

Then compare the run with the previous run and print only significant changes (see "Compare with previous run"), send them to Telegram if there are any (see "Notify via Telegram"), save the snapshot (see "Save snapshot to tracker-data") and finish with the Telegram status, the saved file path and the commit SHA and link.

To track another product, give it a short name in the list above too: the Telegram summary uses it (as `name` in the `telegram-summary` input).

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

Exactly these significant changes, and nothing else, go to Telegram (see "Notify via Telegram").

The comparison does not change the run table or the snapshot format. A failed comparison (previous snapshot unreadable, GitHub MCP unavailable) never blocks saving the snapshot: report `Previous run: comparison failed: <reason>` and continue.

## Notify via Telegram

Right after "Compare with previous run" and **before** saving the snapshot, send the significant changes to Telegram with [`send.py`](../../../send.py) from the project root.

### When to send

- Send only if the comparison finished and found **at least one** significant change.
- Send **nothing** if there are no significant changes, on the first run (no previous snapshot), or if the comparison failed. In these cases do not call the `telegram-summary` agent either. Do not send "no changes" or error messages.
- Send once per run. Never resend because of a retry of another step.

### Summary text: the `telegram-summary` agent

The message text is written by the sub-agent [`telegram-summary`](../../agents/telegram-summary.md) (`model: haiku`, `tools: []`: no tools at all). All formatting rules (header, line format, price format, Russian change wording) live only in that file: do not repeat or change them here.

The agent only formats. Significance, the order of changes and every value are decided here, in the tracker; the agent never sees the run table, the snapshots or `KNOWLEDGE.md`, and never sends anything.

1. **Skip it when there is nothing to send.** If the comparison found no significant changes, was the first run or failed, do not call the agent and do not run `send.py` (see "When to send").
2. **Build the input** — one JSON object, nothing else in the prompt:

   ```json
   {
     "run_at": "2026-11-06 18:00",
     "changes": [
       {"name": "ASUS VivoBook 15 X1502VA-BQ1274", "url": "https://kaspi.kz/shop/p/...-142645394/?c=750000000", "change": "discount started", "old": 289990.00, "new": 259990.00, "delta_pct": null, "reason": null}
     ]
   }
   ```

   - `run_at`: the run time, Asia/Almaty, `YYYY-MM-DD HH:MM`.
   - `changes`: exactly the significant changes, one element per row of the comparison table, in the same order.
   - `name`: the short name from "Tracked URLs" (the text in parentheses up to the first comma, for example `Lenovo IdeaPad 3 15IGL05`); for a product removed from the list, its product ID.
   - `url`: the full tracked URL (for a removed product, the URL from the previous snapshot).
   - `change`: the `change` value from the comparison table.
   - `old` / `new`: numbers copied from the run and the previous snapshot (never recomputed or rounded), or `"unavailable"` (error row), or `"none"` (no value). Which value goes where:

     | `change` | `old` | `new` |
     |---|---|---|
     | `regular_price up` / `down` | old `regular_price` | new `regular_price` |
     | `sale_price up` / `down` | old `sale_price` | new `sale_price` |
     | `discount started` | old current price | new `sale_price` |
     | `discount ended` | old `sale_price` | new current price |
     | `credit gained` / `credit lost` | old current price | new current price |
     | `back in stock` | `"unavailable"` | new current price |
     | `became unavailable` | old current price | `"unavailable"` |
     | `new product` | `"none"` | current price, or `"unavailable"` if its row is an error |
     | `removed from list` | old current price, or `"unavailable"` | `"none"` |

     The current price of a product is `sale_price` if it is not `null`, otherwise `regular_price`.
   - `delta_pct`: for `regular_price` / `sale_price up/down`, the `Δ %` from the comparison table rounded to 1 decimal (a number, negative for a drop); otherwise `null`.
   - `reason`: for `became unavailable`, the `error` reason from the run; otherwise `null`.
3. **Call the agent** with the Agent tool, `subagent_type: "telegram-summary"`, the JSON above as the whole prompt, in the foreground (the next step needs the result). Do not override its model.
4. **Check the text before sending.** Take the agent's reply as is and verify:
   - it does not start with `ERROR:`;
   - it has exactly `N + 2` lines: the header, one empty line, then `N` change lines, where `N` is the number of `changes`;
   - line `i` contains the `url` of change `i` exactly, and its `name`;
   - with spaces removed, line `i` contains the integer digits of every numeric `old` / `new` of change `i` (for example `259990` for `259990.00`), and the kopecks when they are not zero.

   The same check is implemented in `check_reply` in `tests/test_telegram_summary.py`.

   If any check fails, do not send and do not "fix" the text yourself: report `Telegram: not sent: summary check failed: <what failed>`. If the agent cannot be called (no Agent tool, the agent is not found, an error), report `Telegram: not sent: summary agent failed: <reason>`. Neither blocks saving the snapshot.
5. **Split if too long.** Telegram accepts up to 4096 characters per message. If the text is longer than 4000 characters, split it **between lines** into several messages, repeat the header in each with `(1/2)`, `(2/2)`, … at the end, and send them in order.

Then send the text exactly as the agent returned it (except for splitting), as described below.

### How to send

Run from the project root, passing the text returned by `telegram-summary` through a heredoc with a **quoted** delimiter, so that quotes, `$` and backticks in error reasons reach Telegram unchanged:

```bash
python3 send.py "$(cat <<'EOF'
Kaspi: значимые изменения цен (2026-11-06 18:00, Алматы)

ASUS VivoBook 15 X1502VA-BQ1274 — скидка появилась: 289 990 ₸ → 259 990 ₸ — https://kaspi.kz/shop/p/...
EOF
)"
```

- `send.py` takes `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` from the environment, or from `.env` next to it (environment wins). In a cloud session they are environment variables of the cloud environment, and its network must allow `api.telegram.org`.
- **Secrets.** Never print, echo, check by printing, pass on the command line, or write to a file the token or chat ID; never create or commit `.env`; never call the Telegram API directly (curl, Python one-liners). Only `send.py` sends.
- Success: exit code 0 and the output `Отправлено.`.
- Failure (non-zero exit code: missing settings, no network, Telegram API error): the error line from `send.py` is already free of secrets. Report `Telegram: not sent: <that line>` and continue: a failed send never blocks saving the snapshot. Do not retry in a loop and do not fall back to other ways of sending.

### Report

In the final report, add one line:

- `Telegram: sent N message(s), K change(s).`
- `Telegram: nothing to send (no significant changes).` (also on the first run and when the comparison failed: then say why)
- `Telegram: not sent: <error from send.py>`

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
