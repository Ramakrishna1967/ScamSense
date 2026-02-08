# 🛡️ ScamShield System Documentation

An in-depth technical overview of the ScamShield system, featuring architecture diagrams, data flows, and component breakdowns.

---

## 1. High-Level Architecture

ScamShield follows a **Microservices-inspired Monolith** pattern, designed for high throughput and modularity.

```mermaid
flowchart TD
    User["User (Mobile/Web)"] -->|HTTPS/WSS| GlobalLB["Global Load Balancer (Render)"]
    
    subgraph BackendCore ["Backend Core (FastAPI)"]
        GlobalLB --> API["API Gateway"]
        API --> Auth["Authentication Service (JWT)"]
        API --> WSS["WebSocket Manager"]
        
        API --> Orchestrator["LangGraph Orchestrator"]
    end
    
    subgraph AIAgentLayer ["AI Agent Layer"]
        Orchestrator --> Watcher["eye_icon Watcher Agent"]
        Orchestrator --> Analyzer["brain_icon Analyzer Agent (Gemini 1.5 Pro)"]
        Orchestrator --> Pattern["chart_icon Pattern Agent"]
        Orchestrator --> Alerter["siren_icon Alerter Agent"]
        Orchestrator --> Blocker["shield_icon Blocker Agent"]
        
        Analyzer -.-> Gemini["Google Gemini API"]
    end
    
    subgraph DataLayer ["Data Layer"]
        Auth --> Postgres["PostgreSQL (Supabase)"]
        Blocker --> Postgres
        Pattern --> Elastic["Elasticsearch (Vector DB)"]
        WSS -.-> Redis["Redis (Cache & Pub/Sub)"]
    end
    
    style User fill:#f9f,stroke:#333,stroke-width:2px
    style BackendCore fill:#e1f5fe,stroke:#0277bd,stroke-width:2px
    style AIAgentLayer fill:#fff3e0,stroke:#ef6c00,stroke-width:2px
    style DataLayer fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
```

---

## 2. The Analysis Workflow (Sequence Diagram)

This diagram shows exactly### ⚡ Why FastAPI?
We need **asynchronous** processing to handle thousands of messages per second without blocking. Python's `asyncio` combined with FastAPI gives us Node.js-like concurrency with Python's AI ecosystem (Google Generative AI SDK, LangChain).
The entire process completes in **under 2 seconds**.

```mermaid
sequenceDiagram
    participant User
    participant API as FastAPI Backend
    participant Agent as AI Agents
    participant LLM as Google Gemini (1.5 Pro)
    participant DB as Database/Elasticsearch
    participant Family as Family Contacts

    User->>API: 1. POST /analyze (Message Content)
    API->>Agent: 2. Initialize Workflow
    
    rect rgb(240, 248, 255)
        Note right of API: Parallel Execution
        Agent->>Agent: 3. Watcher (Extract Metadata)
        par AI Analysis & Pattern Matching
            Agent->>LLM: 4a. Analyze Intent & Tone
            LLM-->>Agent: Risk Score + Tactics
        and Database Check
            Agent->>DB: 4b. Check Blacklist/Vector Search
            DB-->>Agent: Known Scammer? Similar Patterns?
        end
    end
    
    Agent->>Agent: 5. Aggregation (Combine Signals)
    
    alt Risk Score > 75 (High Danger)
        Agent->>DB: 6. Block Number & Log Incident
        Agent->>Family: 7. Email/SMS Alert to Next of Kin
        Agent-->>API: 8. Return BLOCK Decision
    else Risk Score < 75 (Suspicious)
        Agent-->>API: 8. Return WARN Decision
    else Safe
        Agent-->>API: 8. Return PASS Decision
    end

    API-->>User: 9. JSON Response (Risk, Analysis, Actions)
```

---

## 3. Database Schema (Entity Relationship)

ScamShield uses **PostgreSQL** for relational data (users, settings) and **Elasticsearch** for unstructured data and vector search.

```mermaid
erDiagram
    Users ||--o{ UserSettings : has
    Users ||--o{ UserBlocklist : manages
    Users ||--o{ TrustedContacts : defines
    
    Users {
        uuid id PK
        string email
        string password_hash
        timestamp created_at
    }
    
    UserSettings {
        uuid user_id FK
        boolean enable_ai_scanning
        boolean auto_block_high_risk
        boolean family_alerts_enabled
        int sensitivity_level
    }
    
    UserBlocklist {
        uuid id PK
        uuid user_id FK
        string blocked_identifier
        string reason
        float risk_score
        timestamp blocked_at
    }
    
    TrustedContacts {
        uuid id PK
        uuid user_id FK
        string name
        string email
        string relation
    }
```

---

## 4. Agent State Machine (LangGraph)

The AI logic isn't just a straight line; it's a state machine that can loop or branch based on findings.

```mermaid
stateDiagram-v2
    [*] --> Watcher: New Message
    
    state Watcher {
        ExtactMetadata
        CheckURLs
    }
    
    Watcher --> Router
    
    Router --> QuickPass: Trusted Sender?
    Router --> Analyzer: Unknown Sender
    
    state Analyzer {
        Gemini_Analysis
        DetectUrgency
        ScoreRisk
    }
    
    Analyzer --> PatternMatcher
    
    state PatternMatcher {
        CheckBlacklist
        VectorSearchSimilarScams
    }
    
    PatternMatcher --> DecisionEngine
    
    state DecisionEngine {
        CalculateFinalConfidence
    }
    
    DecisionEngine --> Blocker: Risk > 85%
    DecisionEngine --> Alerter: Risk > 50%
    DecisionEngine --> Logger: Risk < 50%
    
    Blocker --> Alerter: Block & Notify
    Alerter --> [*]: Alert Sent
    Logger --> [*]: Logged
    QuickPass --> [*]: Allowed
```

---

## 5. Deployment Topology

How the system is actually hosted and connected online.

```mermaid
flowchart LR
    subgraph ClientSide ["Client Side"]
        Browser["Chrome/Safari"] 
    end
    
    subgraph Vercel ["Vercel (Frontend)"]
        ReactApp["React SPA"]
    end
    
    subgraph Render ["Render (Backend)"]
        PythonServer["FastAPI Server"]
        EnvVars["ENV Configuration"]
    end
    
    subgraph Supabase ["Supabase (Database)"]
        Pooler["Transaction Pooler :6543"]
        PostgresDB[("PostgreSQL DB")]
    end
    
    subgraph ExternalServices ["External Services"]
        Gemini["Google Gemini API"]
        Elastic["Elastic Cloud"]
    end

    Browser -->|HTTPS| ReactApp
    ReactApp -->|REST/WSS| PythonServer
    
    PythonServer -->|"IPv4 :6543"| Pooler
    Pooler --> PostgresDB
    
    PythonServer -->|HTTPS| Gemini
    PythonServer -->|HTTPS| Elastic
```

---

**Generated by Antigravity for ScamShield**
