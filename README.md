# Онлайн-школа — курсовая работа

## Запуск (локально)

```bash
cd project_morozov
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py setup_roles
python manage.py runserver
```

## Запуск (Docker)

```bash
docker-compose up --build
```

Сервисы:
- **Web:** http://127.0.0.1:8000
- **Mailhog UI:** http://127.0.0.1:8025
- **Silk (профилирование):** http://127.0.0.1:8000/silk/
- **Production (Gunicorn):** `docker-compose --profile production up web-prod` → http://127.0.0.1:8080

## Документация

- Техническое задание: [docs/TZ.md](docs/TZ.md)
- Postman-коллекция: [postman/School_API.postman_collection.json](postman/School_API.postman_collection.json)

## Переменные окружения (.env)

Скопируйте `.env.example` в `.env` и заполните:

| Переменная | Описание |
|------------|----------|
| `SENTRY_DSN` | DSN проекта Sentry (sentry.io) |
| `SOCIAL_AUTH_GOOGLE_OAUTH2_KEY` | Google OAuth2 Client ID |
| `SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET` | Google OAuth2 Secret |
| `SOCIAL_AUTH_VK_OAUTH2_KEY` | VK App ID |
| `SOCIAL_AUTH_VK_OAUTH2_SECRET` | VK Secure Key |

## Тесты

```bash
ENABLE_SILK=False python manage.py test school
```

## OAuth2

После настройки ключей вход через:
- Google: http://127.0.0.1:8000/oauth/login/google-oauth2/
- VK: http://127.0.0.1:8000/oauth/login/vk-oauth2/
