# Спецификация: Serving / Config

## Запуск

### Команда запуска

```bash
# Из корня проекта
python backend/main.py

# Или через uvicorn
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### Последовательность запуска

```
1. Загрузка .env (dotenv)
         │
         ▼
2. Импорт конфигурации (config.py)
         │
         ▼
3. Создание FastAPI app с lifespan
         │
         ▼
4. Добавление middleware (CORS)
         │
         ▼
5. Регистрация роутеров (/api/insights)
         │
         ▼
6. Lifespan: Инициализация
   - Очистка старых файлов (TTL)
   - Создание COMClient (singleton)
   - Асинхронный warmup OneCAgent
         │
         ▼
7. Uvicorn запускает сервер
         │
         ▼
READY: Приём запросов
```

---

## Конфигурация

### Переменные окружения (.env)

```bash
# === 1С COM Connection ===
COM_SERVER=localhost
COM_BASE=ProductionBase
COM_USER=Admin
COM_PASSWORD=
COM_MAX_ROWS=1000

# === Mistral API ===
MISTRAL_API_KEY=your_api_key_here
MISTRAL_MODEL=mistral-large-latest

# === FastAPI Server ===
FASTAPI_HOST=0.0.0.0
FASTAPI_PORT=8000
DEBUG_MODE=True

# === Security & Anonymization ===
ANONYMIZE_FIO=True
ANONYMIZE_TERMINALS=True
ANONYMIZE_VRC=True
ANONYMIZE_REASONS=True
ENABLE_QUERY_VALIDATION=True
MAX_FIX_ATTEMPTS=5
LOG_QUERIES=False

# === File Storage ===
DATA_DIR=data
RAW_DATA_DIR=data/raw
ANONYMIZED_DATA_DIR=data/anonymized
PANDASAI_MAX_ROWS=1000
FILE_TTL_DAYS=30

# === Admin Access ===
ADMIN_API_KEY=your_secret_admin_key
```

## Версии моделей

| Компонент | Версия | Конфигурация |
|-----------|--------|--------------|
| **Mistral LLM** | `mistral-large-latest` | `MISTRAL_MODEL` в .env |
| **1С:Предприятие** | 8.3.x | Не конфигурируется |
| **LangGraph** | latest | Через requirements.txt |
| **FastAPI** | latest | Через requirements.txt |
| **Python** | 3.10+ | Требуется для langgraph |

### Зависимости (requirements.txt)

```txt
langgraph==0.1.1 
langchain==0.2.0 
langchain-core==0.2.0
fastapi==0.110.0 
uvicorn==0.29.0 0
mistralai==1.12.4 
pydantic==2.10.3
```
