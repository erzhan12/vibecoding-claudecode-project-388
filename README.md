# Трекер цен с Claude


[![hexlet-check](https://github.com/erzhan12/vibecoding-claudecode-project-388/actions/workflows/hexlet-check.yml/badge.svg)](https://github.com/erzhan12/vibecoding-claudecode-project-388/actions)

Соберите на Claude-скиллах трекер цен: он сам следит за товарами и присылает в Telegram только значимые изменения.

Учебный проект Хекслета: https://ru.hexlet.io/programs/vibecoding-claudecode


## Стек

- Python 3 — скрипты только на стандартной библиотеке, тесты через `unittest`
- Claude Code — скиллы `tracker` и `extract-price`, сабагент `telegram-summary` (Haiku)
- Telegram Bot API — отправка сводки (`send.py`)
- Kaspi.kz — HTML карточки товара и каталожный API (`curl`)
- GitHub — снимки цен в `erzhan12/tracker-data`, MCP GitHub для локального запуска

## Установка

<!-- Опишите установку: клонирование, зависимости, переменные окружения -->

```bash
git clone https://github.com/erzhan12/vibecoding-claudecode-project-388.git
cd vibecoding-claudecode-project-388
```

## Использование

<!-- Добавьте примеры запуска и запись asciinema — именно это смотрит работодатель -->

Структура проекта и правила для ИИ-агентов — в [`AGENTS.md`](AGENTS.md).
Скилл `tracker` после сравнения цен отправляет сводку значимых изменений через `send.py`.

### Отправка в Telegram: `send.py`

Скрипт без внешних зависимостей (только стандартная библиотека Python).
Настройки берутся из переменных окружения, а если их нет — из файла `.env`
рядом со скриптом (окружение важнее). Файл `.env` в `.gitignore`, не коммитьте его.

```dotenv
TELEGRAM_BOT_TOKEN=<токен бота>
TELEGRAM_CHAT_ID=<id чата>
```

```bash
python3 send.py "текст сообщения"
```

При успехе печатает `Отправлено.`; при отсутствии текста или настроек — ошибку
и код выхода 2; при ошибке сети или Telegram API — ошибку и код 1. Токен в
сообщения об ошибках не попадает.

Тесты (без реальной отправки): `python3 -m unittest discover -s tests -v`

---

<details>
<summary>Автоматические тесты Хекслета</summary>

Тесты запускаются на каждый коммит. За запуск отвечает файл `.github/workflows/hexlet-check.yml` — не удаляйте и не переименовывайте ни его, ни репозиторий.

</details>

## О Хекслете

[Хекслет](https://ru.hexlet.io/) — школа программирования: авторские программы обучения с практикой, поддержкой наставников и реальными проектами, которые остаются в резюме. Этот репозиторий — один из таких проектов.
