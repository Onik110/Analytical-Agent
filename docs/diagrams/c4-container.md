# C4 Container — frontend/backend, orchestrator, retriever, tool layer, storage, observability

```mermaid
flowchart TB
    Frontend[Frontend<br>HTML/JS]
    
    subgraph Backend [Backend]
        API[API Gateway<br>FastAPI]
        Orch[Orchestrator<br>LangGraph]
        LLMClient[Query Generator<br>Mistral Client]
        COMClient[1С Tool Layer<br>COM Client]
        Anon[Anonymizer]
        Validator[Validator]
        Storage[File Storage]
    end
    
    Frontend --> API
    API --> Orch
    Orch --> LLMClient
    Orch --> COMClient
    Orch --> Anon
    Orch --> Validator
    Orch --> Storage
    
    LLMClient --> Mistral[🌐 Mistral API]
    COMClient --> Ones[💾 1С:Предприятие]
    Storage --> Disk[(Local FS<br>JSON/Parquet)]
    
    classDef container fill:#e8f5e9,stroke:#388e3c
    classDef external fill:#ffe0b2,stroke:#ff9800
    classDef storage fill:#f3e5f5,stroke:#9c27b0
    
    class Frontend,API,Orch,LLMClient,COMClient,Anon,Validator,Storage container
    class Mistral,Ones external
    class Disk storage
```

### Ключевые моменты:
* Оркестратор (LangGraph) координирует все сервисы через явные ноды
* Два внешних клиента: LLM для генерации, COM для выполнения
* Три критических сервиса безопасности: анонимизатор, валидатор, хранилище
* Локальное хранилище с разделением на сырые и анонимизированные данные