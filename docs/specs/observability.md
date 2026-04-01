# Спецификация: Observability / Evals

## Метрики

### Ключевые метрики качества

| Метрика | Формула | Цель PoC | Сбор |
|---------|---------|----------|------|
| **Success Rate** | `успешные / все запросы` | ≥ 85% | Счётчик в `/api/query` |
| **Zero-Fix Rate** | `запросы с 0 исправлений / успешные` | ≥ 70% | `fix_attempts == 0` в ответе |
| **PII Leakage Rate** | `запросы с ПнД в ответе / все` | 0% | Регексп-аудит перед возвратом |
| **Query Safety Rate** | `валидные с 1-й попытки / все` | ≥ 95% | `validation_passed` после генерации |
| **End-to-End Latency (p95)** | 95-й перцентиль времени выполнения | < 20 сек | `time.time()` до/после обработки |

### Технические метрики

| Метрика | SLO | p95 | p99 | Сбор |
|---------|-----|-----|-----|------|
| **LLM Generation** | < 10 сек | < 8 сек | < 15 сек | Тайминг вызова `llm_client.chat()` |
| **COM Execution** | < 30 сек | < 20 сек | < 40 сек | Тайминг `com_client.execute_safe_query()` |
| **Anonymization** | < 2 сек | < 1 сек | < 3 сек | Тайминг `anonymizer.anonymize_data()` |
| **Storage Write** | < 500 мс | < 300 мс | < 800 мс | Тайминг `file_storage.save_result()` |

### Health Metrics (endpoint `/api/health`)

| Поле | Значения | Интерпретация |
|------|----------|---------------|
| `status` | `healthy` / `degraded` | `degraded` если `com_connected=false` или `llm_connected=false` |
| `com_connected` | `true` / `false` | Результат `com_client.is_connected()` |
| `llm_connected` | `true` / `false` | Результат тестового вызова Mistral API |
| `storage_ok` | `true` / `false` | Доступность `data/anonymized/` |

## Логи

###  Уровни логирования

| Уровень | Когда | Пример |
|---------|-------|--------|
| **INFO** | Нормальный ход выполнения | "🚀 Инициализация...", "✅ Запрос выполнен: 150 строк" |
| **WARNING** | Предупреждения | "⚠️ Обнаружены ФИО в запросе: Иванова", "⚠️ Разогрев пропущен" |
| **ERROR** | Ошибки выполнения | "❌ Запрос не прошёл валидацию", "❌ Ошибка обработки запроса" |
| **DEBUG** | Детальная отладка | "🧹 Очищенный запрос (длина=...)" |

### Audit Trail

| Событие | Уровень | Данные |
|---------|---------|--------|
| Старт запроса | INFO | `user_query` (sanitized) |
| Очистка ФИО | WARNING | `found_fio` (list) |
| Генерация запроса | INFO | `generated_query` (первые 100 символов) |
| Валидация | INFO/ERROR | `validation_passed`, `errors` |
| Выполнение | INFO | `row_count` |
| Ошибка выполнения | WARNING | `error` (первые 100 символов) |
| Анонимизация | INFO | `row_count` |
| Сохранение файла | INFO | `file_id`, `path` |

---

## Трейсы

### Текущее состояние (PoC)

**Трейсинг не реализован.** Отладка через:
- Логи (logging)
- AgentState (просмотр промежуточных состояний)

###  Future Trace Structure 

```
Trace ID: 550e8400-e29b-41d4-a716-446655440000
├── Span 1: sanitize_query (150ms)
├── Span 2: detect_date_range (50ms)
├── Span 3: generate_query (3200ms) → Mistral API
├── Span 4: validate_query (50ms)
├── Span 5: execute_query (1500ms) → COM
├── Span 6: anonymize_data (100ms)
├── Span 7: analyze_data (50ms)
└── Span 8: format_result (50ms)

Total: 5150ms | Status: Success
```

---

## Проверки (Evals)

### Quality Checks

| Проверка | Метод | Критерий |
|----------|-------|----------|
| **Query Syntax** | 1С выполнение | Запрос выполняется без ошибок |
| **Query Safety** | QueryValidator | Нет запрещённых слов |
| **Response Format** | Regex | Содержит "ВЫБРАТЬ", "ИЗ", "ГДЕ" |
| **Anonymization** | DataAnonymizer | Все ФИО заменены на псевдонимы |
| **Latency** | Timing | < 10 сек (LLM generation) |

### Тестовые наборы

#### Query Generation Tests

```python
TEST_CASES_QUERY = [
    {
        "name": "Простой запрос",
        "query": "Покажи все простои",
        "expected": {"success": True, "has_VYBRAT": True}
    },
    {
        "name": "Запрос с датой",
        "query": "Покажи простои за январь 2026",
        "expected": {"success": True, "has_date_params": True}
    },
    {
        "name": "Запрос с ФИО (анонимизация)",
        "query": "Покажи простои ткача Иванова",
        "expected": {"success": True, "fio_sanitized": True}
    }
]
```

#### Error Handling Tests

```python
TEST_CASES_ERRORS = [
    {
        "name": "Некорректный запрос",
        "query": "абракадабра",
        "expected": {"fix_attempts": ">0"}
    },
    {
        "name": "Запрос с инъекцией",
        "query": "ВЫБРАТЬ * ИЗ Таблица; УДАЛИТЬ Таблица;",
        "expected": {"validation_error": True, "blocked": True}
    },
    {
        "name": "Очень длинный запрос",
        "query": "A" * 15000,
        "expected": {"validation_error": "Запрос слишком длинный"}
    }
]
```

#### Anonymization Tests

```python
TEST_CASES_ANONYMIZATION = [
    {
        "name": "ФИО в запросе",
        "query": "Данные по Иванову И.И.",
        "expected": {"sanitized": "[ФИО_ТКАЧА]", "found_fio": ["Иванову И.И."]}
    },
    {
        "name": "Анонимизация результата",
        "raw_data": [{"Ткач": "Иванов И.И."}],
        "expected": {"anonymized": [{"Ткач": "Ткач #1"}]}
    }
]
```

