# AUTORADAR PRO v2

Полная B2C + B2B версия.

## Что добавлено
- каждое объявление хранится отдельно;
- акции дилеров отделены от физического склада;
- история цен;
- события: новое объявление / снижение / повышение / снятие;
- Days on Market;
- позиция цены в сопоставимой группе;
- медиана рынка и отклонение;
- ориентир для TOP-3 по цене;
- матрица склада конкурентов;
- сводка по дилерам;
- Battlecards;
- CSV экспорт;
- status/coverage;
- опциональный Telegram brief;
- GitHub Actions каждые ~15 минут;
- GitHub Pages без отдельного платного сервера.

## Как обновить существующий репозиторий
Самый надёжный способ:
1. Скачать этот архив.
2. Распаковать.
3. Загрузить всё содержимое поверх текущего `autoradar-tyumen`.
4. Убедиться, что `.github/workflows/autoradar.yml` заменён.
5. Commit changes.
6. Actions → AUTORADAR PRO Collector and Pages → Run workflow.
7. Для первого запуска detail_budget = 60.

## Telegram (необязательно)
Repository → Settings → Secrets and variables → Actions → New repository secret:
- TELEGRAM_BOT_TOKEN
- TELEGRAM_CHAT_ID

Без этих секретов workflow просто пропускает уведомление.

## Важно
Avito / 2ГИС / VK пока обозначены как не подключённые источники. Проект не обходит CAPTCHA или закрытые страницы.
