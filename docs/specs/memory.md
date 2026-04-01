# Спецификация: Memory / Context

## Session State (AgentState)

### Структура

```python
class AgentState(TypedDict):
    # === Входные данные ===
    user_query: str           # Исходный запрос пользователя
    sanitized_query: str      # После очистки ФИО
    
    # === Генерация запроса ===
    generated_query: str      # Сгенерированный запрос 1С
    validation_passed: bool   # Флаг валидации
    validation_errors: List[str]
    
    # === Выполнение ===
    execution_result: List[Dict]  # Данные из 1С
    error: Optional[str]          # Текущая ошибка
    
    # === Анонимизация и результат ===
    anonymized_data: List[Dict]   # Анонимизированные данные
    html_table: str               # HTML для отображения
    analysis: str                 # Текстовая сводка
    
    # === Контроль попыток ===
    fix_attempts: int         # Текущие попытки исправления
    max_attempts: int         # Лимит (5)
    seen_errors: List[str]    # История ошибок (детекция циклов)
    
    # === Параметры ===
    date_range: tuple         # (start_date, end_date)
    
    # === Флаг успеха ===
    success: bool
```

### Жизненный цикл

```
START → Initial State → [Sanitize → DetectDate → Generate → 
Validate → Execute → CheckError → Anonymize → Analyze → Format] → Final State → Discard
```

**Время жизни:** До конца запроса (in-memory only)

---

## Memory Policy

| Тип | Хранение | Время жизни | Изоляция | Сброс |
|-----|----------|-------------|----------|-------|
| **AgentState** | In-memory (TypedDict) | До конца запроса | Per-request | Автоматически |
| **Anonymizer Maps** | In-memory (dict) | До перезапуска сервера | Global | При рестарте |
| **COM Connection** | Singleton (global) | До остановки сервера | Global | При рестарте |
| **File Storage** | Disk (JSON) | 30 дней (TTL) | Per-file | Автоматически (cleanup) |

## Context Budget

### LLM Context

| Параметр | Значение |
|----------|----------|
| **SYSTEM_PROMPT** | ~500 токенов |
| **User Query** | ~50-100 токенов |
| **Error Context** | ~100 токенов (для retry) |
| **Max Output** | 500 токенов |
| **Total Input** | ~700 токенов |
| **Total Cost** | Бесплатно (текущий тариф) |

### In-Memory Budget

| Компонент | Размер (оценка) |
|-----------|-----------------|
| **AgentState** | ~10 KB (1000 строк данных) |
| **Anonymizer Maps** | ~100 KB (1000 уникальных значений) |
| **COM Connection** | ~1 MB (1С client) |
| **Total** | ~1.1 MB на запрос |

---

