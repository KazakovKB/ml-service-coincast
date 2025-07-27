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
│       │   └── ml_service.py         # Фасад веб-сервиса
│       │
│       ├── api/                  # Слой взаимодействия с пользователем
│       │   ├── __init__.py
│       │   └── ...
│       │
│       ├── infra/             
│       │   ├── __init__.py
│       │   ├── db.py
│       │   └── models.py         
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

