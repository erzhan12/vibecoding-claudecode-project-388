# AGENTS.md

Инструкции для ИИ-агентов (Claude Code и других), работающих с этим репозиторием.

Проект — трекер цен на ноутбуки в Kaspi.kz: проверяет цены по списку товаров,
сравнивает с прошлым прогоном, оставляет только значимые изменения и присылает
их в Telegram. Цель и контракт полей — в [`TASK.md`](TASK.md), список товаров — в скилле `tracker`.

## Где что лежит

| Файл | Назначение |
|---|---|
| [`.claude/skills/tracker/SKILL.md`](.claude/skills/tracker/SKILL.md) | Скилл `tracker`: единственный список отслеживаемых товаров («Tracked URLs»), последовательный прогон по нему с паузой 2 с между товарами, сравнение с прошлым снимком, сводка в Telegram, сохранение снимка в `erzhan12/tracker-data` |
| [`.claude/skills/extract-price/SKILL.md`](.claude/skills/extract-price/SKILL.md) | Скилл `extract-price`: цены и рассрочка по одной ссылке на карточку |
| [`.claude/agents/telegram-summary.md`](.claude/agents/telegram-summary.md) | Сабагент `telegram-summary` (`model: haiku`, `tools: []` — без инструментов): из готового списка значимых изменений пишет текст сводки для Telegram; правила оформления сводки — только здесь |
| [`KNOWLEDGE.md`](KNOWLEDGE.md) | Правила значимости изменений (порог цены, скидка, рассрочка, наличие) |
| [`send.py`](send.py) | Отправка текста в Telegram: `python3 send.py "текст"` |
| [`.claude/skills/extract-price/compute_prices.py`](.claude/skills/extract-price/compute_prices.py) | Расчёт `regular_price` / `sale_price` из `price` и `unitPriceBeforeDiscount` (правило скилла `extract-price`) |
| [`tests/test_send.py`](tests/test_send.py) | Тесты `send.py` без сети |
| [`tests/test_compute_prices.py`](tests/test_compute_prices.py) | Тесты расчёта цен: скидка, равные цены, `price` выше `unitPriceBeforeDiscount`, ошибки |
| [`tests/test_significance.py`](tests/test_significance.py) | Проверка таблицы «Примеры на границах» из `KNOWLEDGE.md` (порог, скидка, зачёркнутая цена) и того, что `tracker` не хардкодит правила |
| [`tests/test_telegram_summary.py`](tests/test_telegram_summary.py) | Проверка формата Telegram-сводки: эталон, фикстуры с ответами Haiku (`tests/fixtures/telegram_summary/`), проверка ответа перед отправкой; живой вызов агента — только с `RUN_HAIKU_SUMMARY=1` |
| [`TASK.md`](TASK.md) | Цель, контракт полей, пример карточки; список товаров здесь не ведётся |
| [`.mcp.json`](.mcp.json) | MCP-сервер GitHub для локального запуска (`GITHUB_PAT`) |

Инструкции скиллов и правила значимости живут только в файлах выше. Не копируйте
их сюда и в другие места: меняйте исходный файл.

## Правила

- Скиллы не дублируют друг друга: `tracker` только оркестрирует, всё извлечение цен — в `extract-price`; пороги и правила значимости — только в `KNOWLEDGE.md`; оформление Telegram-сводки — только в агенте `telegram-summary` (он не решает значимость, не собирает цены и ничего не отправляет).
- Список товаров ведётся в одном месте — раздел «Tracked URLs» в [`.claude/skills/tracker/SKILL.md`](.claude/skills/tracker/SKILL.md). Не копируйте URL в `TASK.md`, `README.md` и другие файлы: чтобы добавить или убрать товар, меняйте только скилл.
- Секреты (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `GITHUB_PAT`) берутся из переменных окружения или `.env` (он в `.gitignore`). Не выводите их, не передавайте в аргументах команд, не пишите в файлы и коммиты. В Telegram отправляет только `send.py`.
- Не удаляйте и не меняйте `.github/workflows/hexlet-check.yml`: на нём держатся автотесты Хекслета.

## Проверки

```bash
python3 -m unittest discover -s tests -v
```

Живая проверка агента `telegram-summary` на Haiku (платно, нужен залогиненный `claude`, в Telegram ничего не отправляет):

```bash
RUN_HAIKU_SUMMARY=1 python3 -m unittest tests.test_telegram_summary -v
```

## Как добавить скилл

1. Папка `.claude/skills/<имя-скилла>/` (имя в kebab-case) с файлом `SKILL.md`.
2. `SKILL.md` начинается с frontmatter с полями `name` и `description` (по `description` агент решает, когда вызывать скилл).
3. Вспомогательные скрипты кладите в ту же папку и ссылайтесь на них из `SKILL.md`.
4. Добавьте ссылку на новый `SKILL.md` в таблицу «Где что лежит» выше.

Документация по скиллам Claude Code: https://code.claude.com/docs/en/skills
