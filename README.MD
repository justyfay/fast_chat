# Сервис обмена мгновенными сообщениями
## Стэк
![Static Badge](https://img.shields.io/badge/https%3A%2F%2Fimg.shields.io%2Fbadge%2Fany_text-0.115.2-blue?style=for-the-badge&label=FastApi&labelColor=%2397E8C0&color=black)
![SqlAlchemy](https://img.shields.io/badge/https%3A%2F%2Fimg.shields.io%2Fbadge%2Fany_text-2.0.36-blue?style=for-the-badge&label=SqlAlchemy&labelColor=orange&color=black)
![Uvicorm](https://img.shields.io/badge/https%3A%2F%2Fimg.shields.io%2Fbadge%2Fany_text-0.32.0-blue?style=for-the-badge&label=Uvicorn&labelColor=%23665248&color=black)
![Alembic](https://img.shields.io/badge/https%3A%2F%2Fimg.shields.io%2Fbadge%2Fany_text-1.13.3-blue?style=for-the-badge&label=Alembic&labelColor=%236c5068&color=black)
![Postgres](https://img.shields.io/badge/postgresql-4169e1?style=for-the-badge&logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white)
![Aiogram](https://img.shields.io/badge/https%3A%2F%2Fimg.shields.io%2Fbadge%2Fany_text-3.13.1-blue?style=for-the-badge&label=Aiogram&labelColor=%232878AF&color=black)
![Pydantic](https://img.shields.io/badge/https%3A%2F%2Fimg.shields.io%2Fbadge%2Fany_text-2.9.2-blue?style=for-the-badge&label=Pydantic&labelColor=brown&color=black)
![Docker](https://img.shields.io/badge/https%3A%2F%2Fimg.shields.io%2Fbadge%2Fany_text-24.0.6-blue?style=for-the-badge&label=Docker&labelColor=blue&color=grey)


## О сервисе
> **_NOTE:_** Сервис позволяет обмениваться сообщениями в режиме реального времени и получать нотификации в Telegramm, если пользователь оффлайн.

## Задачи

- Регистрация и аутентификация пользователей:
- [x] Реализовать возможность регистрации новых пользователей.
- [x] Обеспечить аутентификацию и авторизацию при работе с API.
- Отправка и получение сообщений:
- [x] Пользователи могут отправлять сообщения друг другу.
- [x] Реализовать получение новых сообщений в реальном времени.
- Сохранение истории сообщений:
- [x] Все сообщения должны сохраняться в базе данных.
- [x] Предусмотреть возможность получения истории переписки между пользователями.
- Уведомления через Telegram-бота:
- [x] Создать простого Telegram-бота с помощью Aiogram.
- [x] Бот должен уведомлять пользователя о новом сообщении, если он офлайн.
- Веб-интерфейс для тестирования:
- [x] Разработать простую веб-страницу для взаимодействия с сервисом. Дизайн не важен — можно использовать любые готовые шаблоны.
- [x] Веб-интерфейс может быть реализован на любом языке и стеке по выбору.

## Технические требования:
- <b>Язык программирования:</b> Python 3.10 или новее.
- <b>Фреймворк:</b> FastAPI для разработки RESTful API.
- <b>Асинхронность</b>
- [x] Использовать async/await для обработки запросов.
- [x] Реализовать отправку и получение сообщений в реальном времени с помощью WebSockets или другой технологии по твоему выбору.
- <b>Многопоточность</b>
- [ ] Использовать многопоточность, где это необходимо для повышения производительности.
- <b>Базы данных</b>
- [x] PostgreSQL для хранения пользователей и сообщений.
- [x] Redis для кэширования и хранения сессий.
- <b>ORM и миграции</b>
- [x] SQLAlchemy для работы с базой данных.
- [x] Alembic для управления миграциями.
- <b>Фоновые задачи</b>
- [x] Celery для обработки фоновых задач (например, отправка уведомлений через бота).
- <b>Контейнеризация</b>
- [x] Docker для контейнеризации приложения.
- <b>Сервер</b>
- [ ] Nginx для обратного проксирования (можно использовать простой конфигурационный файл).

## Установка:
1. Клонировать проект
    ```
    git clone https://github.com/justyfay/fast_chat.git
    ```
2. В корневой папке скопировать `.env.template` и переименовать `.env`. Заполнить переменные.
    ```
    cp .env.template .env 
    ```
3. В папке `/bot` создать отдельный `.env` файл и вставить в него переменную `BOT_TOKEN`. Про создание бота можно узнать в [статье](https://journal.tinkoff.ru/guide/howto-telegram-bot/), раздел "Как зарегистрировать нового бота".
4. Запустить приложение
   ```
   docker compose up -d --build
   ```
   После запуска должно быть доступно приложение по адресу http://127.0.0.1:8000 и документация http://127.0.0.1:8000/docs.

