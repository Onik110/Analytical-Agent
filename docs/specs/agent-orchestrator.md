# Спецификация: Agent / Orchestrator

## Шаги (Nodes)

| Шаг | Функция | Описание |
|-----|---------|----------|
| **1. Sanitize** | `_sanitize_query_node` | Очистка ФИО из запроса (regex) |
| **2. DetectDate** | `_detect_date_range_node` | Извлечение диапазона дат |
| **3. Generate** | `_generate_query_node` | Генерация запроса 1С через LLM |
| **4. Validate** | `_validate_query_node` | Статическая валидация (blacklist) |
| **5. Execute** | `_execute_query_node` | Выполнение запроса через COM |
| **6. CheckError** | `_check_error_node` | Проверка ошибки, детекция циклов |
| **7. Fix** | `_fix_query_node` | Подготовка к повторной генерации |
| **8. Anonymize** | `_anonymize_data_node` | Анонимизация данных |
| **9. Analyze** | `_analyze_data_node` | Генерация сводки (без LLM) |
| **10. Format** | `_format_result_node` | Форматирование в HTML таблицу |

---

## Таблица переходов

| От | До | Тип | Условие |
|----|----|-----|---------|
| sanitize_query | detect_date_range | Unconditional | — |
| detect_date_range | generate_query | Unconditional | — |
| generate_query | validate_query | Unconditional | — |
| validate_query | execute_query | Unconditional | — |
| execute_query | check_error | Unconditional | — |
| check_error | anonymize_data | Conditional | success=True |
| check_error | fix_query | Conditional | error detected, fix_attempts < MAX |
| check_error | END | Conditional | fix_attempts >= MAX или цикл |
| fix_query | generate_query | Unconditional | — |
| anonymize_data | analyze_data | Unconditional | — |
| analyze_data | format_result | Unconditional | — |
| format_result | END | Unconditional | — |

---

## Stop Conditions

| Условие | Описание | Действие |
|---------|----------|----------|
| **success=True** | Запрос выполнен без ошибок | Переход к anonymize → format → END |
| **fix_attempts >= MAX** | Превышен лимит попыток (5) | Возврат ошибки пользователю |
| **Cycle Detected** | Повторяющаяся ошибка (2 раза подряд) | Прерывание цикла, возврат ошибки |
| **Validation Error** | Запрос не прошёл валидацию | Retry генерации (без увеличения fix_attempts) |
| **Critical Exception** | Необработанное исключение | Возврат ошибки с сообщением |

---

## Fallback Strategy

| Сценарий | Fallback |
|----------|----------|
| LLM недоступен | Возврат ошибки "Сервис временно недоступен" |
| 1С недоступен | Возврат ошибки "Соединение с 1С разорвано" |
| Query не выполняется | Auto-fix (5 попыток) → Ошибка пользователю |
| Валидация не прошла | Retry генерации (без увеличения fix_attempts) |
| Cycle detected | Немедленный возврат ошибки |

---

