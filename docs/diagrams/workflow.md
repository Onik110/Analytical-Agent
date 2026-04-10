# Workflow Diagram — Agent 1C

**Описание:** Workflow — пошаговое выполнение запроса, включая ветки ошибок

```mermaid
flowchart TD
    subgraph Input["📥 INPUT"]
        U[User Query<br>Natural Language]
    end

    subgraph P0["Process 0: Input Validation ⚠️"]
        V0{Query empty<br>or length < 3?}
    end

    subgraph P1["Process 1: Sanitization 🔒"]
        S1[Remove FIO from query<br>regex: 2-3 words capitalized]
    end

    subgraph P2["Process 2: Date Detection 📅"]
        S2[Extract date range<br>keywords: месяц, год, неделя]
    end

    subgraph P3["Process 3: Query Generation 🤖"]
        S3[Mistral API call<br>SYSTEM_PROMPT + query]
    end

    subgraph P4["Process 4: Validation ✅"]
        S4[Check forbidden words<br>Only SELECT allowed]
    end

    subgraph P5["Process 5: Execution 🔌"]
        S5[COM connection to 1C<br>Execute query]
    end

    subgraph P6["Process 6: Anonymization 🔒"]
        S6[Replace PII with<br>pseudonyms #1, #2, ...]
    end

    subgraph P7["Process 7: Analysis 📊"]
        S7[Generate summary<br>row count, unique values]
    end

    subgraph P8["Process 8: Formatting 🎨"]
        S8[HTML table with<br>sortable columns]
    end

    subgraph Output["📤 OUTPUT"]
        R[Response to User<br>HTML + Summary]
    end

    subgraph Storage["💾 File Storage"]
        FS[("(data/raw/<br>data/anonymized/)")]
    end

    U --> V0
    V0 -->|Empty / too short| REJ["❌ Rejected<br>Введите вопрос"]
    V0 -->|Valid| S1
    S1 --> S2
    S2 --> S3
    S3 --> S4
    S4 -->|Valid| S5
    S4 -->|Invalid| S3
    S5 -->|Success| S6
    S5 -->|Error| FIX["Fix Query Node<br>🔄 Retry"]
    FIX -->|Attempts < 5| S3
    FIX -->|Attempts ≥ 5| ERR[Error Response]
    S6 --> S7
    S7 --> S8
    S8 --> R
    S6 -->|save=true| FS
    REJ --> R

    style Input fill:#e3f2fd
    style Output fill:#e8f5e9
    style Storage fill:#f3e5f5
    style ERR fill:#ffebee
    style REJ fill:#fff3e0
```

### Ключевые моменты:
* **Валидация ввода (Process 0):** пустые запросы и строки < 3 символов отклоняются немедленно, без вызова LLM/COM
* Двухуровневая защита ПнД: санитизация входа + анонимизация выхода
* Автоисправление ошибок с лимитом 5 попыток для защиты от бесконечных циклов
* Опциональное сохранение: сырые данные (только админ) + анонимизированные (все пользователи)