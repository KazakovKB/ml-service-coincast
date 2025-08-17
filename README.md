# ML-Service-Coincast

Платёжный ML-сервис с личным кабинетом: пользователи пополняют баланс и отправляют датасеты на прогноз.  
Ядро — FastAPI, асинхронная обработка через RabbitMQ (FastStream), UI — SSR + HTMX, Telegram-бот на aiogram.

---

## Содержание

- [Архитектура репозитория](#архитектура-репозитория)
- [Как это работает](#как-это-работает)
- [Быстрый старт](#быстрый-старт)
- [Эндпоинты API](#эндпоинты-api)
- [Web UI](#web-ui)
- [Telegram-бот](#telegram-бот)
- [Формат данных для предикта](#формат-данных-для-предикта)

---
## Архитектура репозитория

```
ml-service-coincast/
├── src/
│   └── app/
│       ├── __init__.py
│       ├── domain/               # Чистая предметная область
│       │   ├── __init__.py
│       │   ├── enums.py              
│       │   ├── user.py               
│       │   ├── account.py            
│       │   ├── ml_model.py           # Интерфейс ML-модели
│       │   ├── prediction.py         
│       │   └── validation.py         # Валидация датасетов
│       │
│       ├── services/             # Оркестрация бизнес-сценариев
│       │   ├── __init__.py
│       │   ├── account_service.py
│       │   ├── auth_service.py
│       │   ├── prediction_service.py
│       │   └── model_gateway.py      # Cлой вызова зарегистрированных моделей
│       │
│       ├── api/                  # FastAPI-роуты, схемы
│       │   ├── __init__.py          
│       │   ├── deps.py           
│       │   ├── auth.py              
│       │   ├── account.py           
│       │   ├── prediction.py        
│       │   ├── models.py
│       │   └── schemas.py           
│       │
│       ├── infra/                 # Инфраструктура: DB, брокер, модели
│       │   ├── __init__.py
│       │   ├── ml/ 
│       │   │   ├── __init__.py
│       │   │   ├── demo_ar.py
│       │   │   ├── lintrend.py
│       │   │   └── registry.py
│       │   ├── db.py
│       │   ├── mq.py
│       │   ├── repositories.py.py
│       │   └── models.py        
│       │
│       ├── worker/        
│       │   ├── __init__.py
│       │   └── worker.py        
│       │
│       ├── bot/                    # Telegram-бот
│       │   ├── __init__.py      
│       │   ├── Dockerfile
│       │   ├── requirements.txt
│       │   ├── keyboards.py
│       │   ├── parsers.py
│       │   ├── client.py               # REST-клиент -> FastAPI
│       │   └── main.py                 # aiogram-бот
│       │
│       ├── web/                    # WebUI: SSR + HTMX
│       │   ├── __init__.py      
│       │   ├── router.py
│       │   └── templates
│       │       ├── account
│       │       │   ├── balance.html
│       │       │   └── history.html
│       │       │  
│       │       ├── auth
│       │       │   ├── login.html
│       │       │   └── register.html
│       │       │  
│       │       ├── partials
│       │       │   └── _alert.html
│       │       │  
│       │       ├── predict
│       │       │   ├── _job_card.html
│       │       │   ├── _job_rows.html
│       │       │   ├── form.html
│       │       │   ├── history.html
│       │       │   └── show.html
│       │       │  
│       │       ├── static
│       │       ├── layout.html
│       │       └── index.html
│       │
│       ├── Dockerfile
│       ├── main.py                # Точка входа FastAPI
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

---

## Как это работает

1. Пользователь регистрируется/логинится -> получает `access_token`.
2. Пополняет баланс (ручка `/api/account/top-up` или в UI/боте).
3. Отправляет датасет на предикт (через UI — загрузка файла; через API — JSON).
4. API создаёт **PENDING**-джобу и ставит задачу в RabbitMQ (FastStream).
5. `worker` валидирует входные строки, запускает модель, списывает кредиты и помечает джобу **OK**/**ERROR**.
6. UI (HTMX) авто-обновляет карточку джобы; бот показывает статус по команде `/job`.

---

## Быстрый старт

```bash
# 1) Перенесите переменные окружения
cp .env.template .env

# 2) Поднимите всё окружение
make up

# 3) Инициализируйте демо-пользователей/счета
make init-db

# 4) (опционально) Прогоните интеграционные тесты
make tests
```

**Откройте:**
- Web UI: http://localhost/
- Swagger UI (REST API): http://localhost/docs
- RabbitMQ Management: http://localhost:15672 (логин/пароль — см. .env)

---

## Эндпоинты API

- POST /api/auth/register -> { access_token }
- POST /api/auth/login -> { access_token }
- GET  /api/account/balance
- POST /api/account/top-up — { amount, reason }
- GET  /api/account/transactions
- GET  /api/models/ — доступные модели (по env AVAILABLE_MODELS)
- POST /api/predict/ — асинхронный запуск; ответ 202 Accepted + { id, status: "PENDING", ... }
- GET  /api/predict/{job_id} — статус/результат (PENDING | OK | ERROR)
- GET  /api/predict/history — список последних джоб (короткая форма)

---

## Web UI
- SSR на Jinja2 (шаблоны в web/templates), динамика — HTMX.
- Авторизация через cookie access_token.
- Разделы:
  - Balance — текущий баланс + пополнение
  - Transactions — история операций
  - Predict — загрузка файла (CSV/JSON/XLSX/Parquet), выбор модели
  - History — список джоб с авто-обновлением
  - Job — карточка конкретной джобы (авто-refresh для PENDING)
- Ошибки авторизации/недостатка средств отображаются дружелюбными баннерами и редиректами.

---

## Telegram-бот
- Команды: /register, /login, /balance, /topup, /tx, /predict, /ph, /job.
- Inline-клавиатуры для навигации, пошаговый сценарий предикта (ввод JSON или загрузка файла).
- Работает поверх REST API (API_BASE должен указывать на /api).

---

## Формат данных для предикта

Текущая логика (валидатор и простые модели) требует:
1. Временную колонку — любое из: timestamp, ts, date, datetime, time
2. Ценовую колонку — любое из: price, close, value, target, y

Остальные признаки допустимы, но игнорируются текущими моделями.

Прогноз строится на N будущих точек, где N = число строк в датасете.
Стоимость списания: len(valid_rows) * COST_PER_ROW.

**Пример JSON**
```JSON
[
  {"timestamp": "2024-01-01T00:00:00Z", "price": 100},
  {"timestamp": "2024-01-02T00:00:00Z", "price": 101},
  {"timestamp": "2024-01-03T00:00:00Z", "price": 103}
]
```
Файл-загрузка (UI) поддерживает: CSV / JSON / XLSX / Parquet.