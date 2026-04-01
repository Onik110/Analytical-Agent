# Спецификация: Tools / APIs 

## Контракты

### Connection String

```
Srvr="{COM_SERVER}:port";Ref="{COM_BASE}";Usr="{COM_USER}";Pwd="{COM_PASSWORD}"
```

### Query Format

```1c
ВЫБРАТЬ
    <Поля> КАК <Алиас>,
    ...
ИЗ
    <Таблица> КАК <Алиас>
ГДЕ
    <Условия>
    И <Таблица>.Ссылка.Дата МЕЖДУ &нач И &кон
```

### Result Format

```python
[
    {
        "Ткач": "Иванов И.И.",
        "Терминал": "T1",
        "ВРЦ": "Цех 1",
        "Количество": 10,
        "Длительность": 30,
        "Дата": datetime(2000, 1, 15)
    },
    ...
]
```

## Ошибки

| Ошибка | Причина | Обработка |
|--------|---------|-----------|
| `RuntimeError` | COM-соединение не установлено | Log error, return to agent |
| `Exception` | 1С недоступен (network, auth) | Log error, propagate |
| `ValueError` | Синтаксическая ошибка в запросе | Return to agent (retry loop) |
| `Timeout` | Превышено время ожидания | Log warning, propagate |

## Timeout

| Операция | Значение | Статус |
|----------|----------|--------|
| **COM Connection** | ~2-3 мин (первое подключение) |  Реализовано |
| **Query Execution** | Не реализован явно |  Зависит от 1С |
| **Рекомендация** | 30 сек | Future |

---

## Side Effects

| Эффект | Описание |
|--------|----------|
| **Global Connection** | Singleton `_connection` (разделяется между запросами) |
| **COM Initialization** | `pythoncom.CoInitialize()` (один раз для процесса) |
| **Logging** | Логирование подключения, выполнения, ошибок |
| **Thread Blocking** | Lock при подключении (`_connection_lock`) |

---

## Защита (Guardrails)

### Query Restrictions

```python
# Только SELECT-запросы (ВЫБРАТЬ)
if not query_text.upper().startswith("ВЫБРАТЬ"):
    raise ValueError("Разрешены только запросы типа ВЫБРАТЬ")
```

### Row Limit

```python
COM_MAX_ROWS = 1000  # Ограничение на количество возвращаемых строк
```

### Parameter Binding

```python
# Защита от SQL-инъекций через параметры
if date_range and "&нач" in query_text and "&кон" in query_text:
    query.SetParameter("нач", start_date)
    query.SetParameter("кон", end_date)
```

### Column Extraction

```python
# Извлечение только явных алиасов (защита от неожиданных полей)
aliases = re.findall(r'КАК\s+([А-Яа-яA-Za-z_][А-Яа-яA-Za-z0-9_]*)', select_block)
```

---

## Конфигурация

| Параметр | .env | Default | Описание |
|----------|------|---------|----------|
| `COM_SERVER` | Опциональный | `localhost` | Хост 1С |
| `COM_BASE` | Опциональный | `ProductionBase` | Имя базы |
| `COM_USER` | Опциональный | `Admin` | Пользователь |
| `COM_PASSWORD` | Опциональный | `""` | Пароль |
| `COM_MAX_ROWS` | Опциональный | `1000` | Лимит строк |

---


## Зависимости

```python
import pythoncom        # COM initialization
import win32com.client  # COM connector
```

**Установка:**
```bash
pip install pywin32
```