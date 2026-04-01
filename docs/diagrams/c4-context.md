# C4 Context — система, пользователь, внешние сервисы и границы

```mermaid
flowchart LR
    User[👤 Пользователь]
    Admin[⚙️ Администратор]
    System[Agent 1C]
    Mistral[🌐 Mistral API]
    Ones[💾 1С:Предприятие]
    
    User -->|HTTP запросы| System
    Admin -->|Управление файлами| System
    System -->|Генерация запросов| Mistral
    System -->|Выполнение запросов| Ones
    
    subgraph TrustBoundary [🔒 Trust Boundary]
        System
    end
    
    classDef external fill:#ffe0b2
    classDef trusted fill:#c8e6c9
    classDef user fill:#e3f2fd
    
    class User,Admin,Mistral,Ones external
    class System trusted
```

### Ключевые моменты:
* Два типа пользователей: обычные (менеджеры, аналитики) и администраторы (управление файлами)
* Две внешние зависимости: 1С (локально) и Mistral API (облако)
* Все операции с ПнД происходят внутри доверенной границы