# Охрана труда

Начальный Django-проект: `manage.py`, настройки и ASGI/WSGI в `config/`,
единственный маршрут — `/admin/`. Собственных предметных приложений пока нет.

Стек: Python 3.12, Django 5.2.8, Poetry 2.2.1, SQLite.
Зависимости закреплены в `poetry.lock`. В зависимостях также присутствуют
psycopg, Redis, Celery и Gunicorn, но внешние сервисы пока не настроены.
Docker Compose, Docker и CI пока не используются.

## Установка

Установите Python 3.12 и Poetry 2.2.1. Из корня существующего checkout:

```sh
poetry --version
poetry env use python3.12
poetry check --lock
poetry install --no-root
cp .env.example .env
poetry run python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

Вставьте сгенерированный ключ в `SECRET_KEY` локального `.env`, заключив значение
в одинарные кавычки. Не коммитьте файл и не используйте production-секреты.
`--no-root` устанавливает зависимости без упаковки проекта.

Настройки загружают `.env` из корня проекта; переменные процесса имеют приоритет:

| Переменная | Поведение |
| --- | --- |
| `SECRET_KEY` | Обязательный непустой ключ, без фиксированного значения по умолчанию |
| `DEBUG` | По умолчанию `false`; допустимы true/false, 1/0, yes/no, on/off |
| `ALLOWED_HOSTS` | Хосты через запятую, без схем и портов; при DEBUG=true по умолчанию только loopback-хосты, иначе обязательна |

Отсутствие обязательных настроек и неверный `DEBUG` приводят к понятной ошибке
при старте. Production-развёртывание требует отдельной проверки безопасности;
эта инструкция предназначена для локальной разработки.

## Локальный запуск

Проверьте локальные настройки. База — только `db.sqlite3` в корне checkout.

```sh
poetry run python manage.py check
poetry run python manage.py migrate --noinput
poetry run python manage.py runserver 127.0.0.1:8000
```

Форма администратора доступна по пути `/admin/`. Для ручной работы при
необходимости создайте локального пользователя: `poetry run python manage.py createsuperuser`.
Не подключайтесь к production-БД и не выполняйте самостоятельный деплой.

## Проверки и тесты

После настройки `.env`:

```sh
poetry check --lock
poetry run python manage.py check
poetry run python manage.py test --noinput
```

Тесты в `config/tests.py` проверяют разбор настроек, приоритет окружения,
ограничения хостов, страницу входа администратора и работу ORM с сессиями.
Django создаёт отдельную тестовую SQLite-базу в памяти и удаляет её после тестов.
PostgreSQL, Redis, Celery и реальные секреты не требуются.
Правила автономной разработки находятся в `AGENTS.md`.
