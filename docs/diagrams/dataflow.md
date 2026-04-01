# Data Flow Diagram — Agent 1C

**Описание:** Как данные проходят через систему, что хранится, что логируется


```mermaid
flowchart LR
    U[👤 User] -->|Query<br>Natural Language| API[API Gateway]
    
    API -->|State| Orch[Orchestrator<br>LangGraph State]
    Orch -->|Prompt| LLM[Mistral API]
    LLM -->|1C Query<br>text| Orch
    
    Orch -->|Query + Params| COM[1C COM Client]
    COM -->|Raw Data<br>with PII| Orch
    
    Orch -->|Anonymized Data| FS[File Storage]
    FS -->|Raw JSON| FS_R[(data/raw/)]
    FS -->|Anonymized JSON| FS_A[(data/anonymized/)]
    
    Orch -->|Response<br>Anonymized only| API
    API -->|HTML Table + Summary| U
    
    subgraph Logging["📝 Logging"]
        LOG[(Console Logs)]
    end
    
    Orch -.->|Sanitized query,<br>row count,<br>errors| LOG
    COM -.->|Query execution,<br>row count| LOG
    
    classDef pii fill:#ffcdd2,stroke:#f44336
    classDef anon fill:#c8e6c9,stroke:#4caf50
    classDef log fill:#e0e0e0,stroke:#616161
    
    class COM,FS_R pii
    class FS_A,API,U anon
    class LOG log
```

### Ключевые моменты:
* Сырые ПнД никогда не покидают доверенную зону (1С → data/raw/ → анонимизация)
* Логирование содержит только санитизированные данные и метрики (количество строк, ошибки)
* Два уровня хранения: raw/ (админ, 30 дней) и anonymized/ (все пользователи)
* Внешние сервисы (Mistral) получают только санитизированные запросы без ПнД