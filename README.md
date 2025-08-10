# ml-service-coincast

ML-сервис с личным кабинетом, который позволяет пользователям делать платные запросы к
модели машинного обучения для получения прогнозов или рекомендаций
по криптовалютному рынку.

## Архитектура

```
ml-service-coincast/
├── src/
│   └── app/
│       ├── __init__.py
│       ├── domain/               # Чистая предметная область
│       │   ├── __init__.py
│       │   ├── enums.py              # Доменные перечисления
│       │   ├── user.py               # Сущности пользователей
│       │   ├── account.py            # Финансовый блок
│       │   ├── ml_model.py           # Модели машинного обучения
│       │   ├── prediction.py         # История запросов
│       │   └── validation.py         # Валидация данных
│       │
│       ├── services/             # Оркестрация бизнес-сценариев
│       │   ├── __init__.py
│       │   ├── account_service.py
│       │   ├── auth_service.py
│       │   ├── prediction_service.py
│       │   └── ml_service.py         # Фасад веб-сервиса
│       │
│       ├── api/                  # Слой взаимодействия с пользователем
│       │   ├── __init__.py          # включает все роутеры
│       │   ├── deps.py              # DI-зависимости (DB, current_user)
│       │   ├── auth.py              # регистрация / авторизация
│       │   ├── account.py           # баланс, пополнение
│       │   ├── prediction.py        # отправка данных и история
│       │   └── schemas.py           # Pydantic
│       │
│       ├── infra/             
│       │   ├── __init__.py
│       │   ├── db.py
│       │   ├── mq.py
│       │   ├── repositories.py.py
│       │   └── models.py        
│       │
│       ├── worker/             
│       │   ├── __init__.py
│       │   └── worker.py        
│       │
│       ├── bot/
│       │   ├── __init__.py      
│       │   ├── Dockerfile
│       │   ├── requirements.txt
│       │   ├── client.py            # REST-клиент -> FastAPI
│       │   └── main.py              # aiogram-бот
│       │
│       ├── Dockerfile
│       ├── main.py
│       ├── test_integration.py
│       ├── init_db.py
│       └── requirements.txt
│       ... ...
│
├── nginx
│   └── nginx.conf
│
├── README.md
├── Makefile
├── .env.template
├── docker-compose.yml
└── .gitignore
```

