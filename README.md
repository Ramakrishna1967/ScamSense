# ScamSense

Multi-Agent AI Scam Detection System using FastAPI, LangGraph, Google Gemini 1.5 Pro, Elasticsearch, PostgreSQL, and Redis.

## Project Structure

```
scamshield/
├── main.py                 # All-in-one version
├── main_modular.py         # Modular version
├── requirements.txt
├── .env.example
├── config/                 # Settings
├── models/                 # Pydantic models
├── services/               # Database clients
├── agents/                 # LangGraph agents
├── api/                    # FastAPI routes
├── scripts/                # Setup scripts
├── frontend/               # Dashboard
└── tests/                  # Test files
```

## Quick Start

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python scripts/init_database.py
python scripts/init_elasticsearch.py
python main.py
```

## Agent Pipeline

Watcher -> Analyzer -> Pattern -> Alerter -> Blocker

## API Endpoints

- POST /api/v1/auth/register
- POST /api/v1/auth/login
- POST /api/v1/analyze
- GET /api/v1/scams
- GET /api/v1/stats
- POST /api/v1/report
- WS /ws/{user_id}

## Environment Variables

```
GEMINI_API_KEY=AIza...
DATABASE_URL=postgresql://...
ES_CLOUD_ID=...
ES_API_KEY=...
REDIS_URL=redis://...
JWT_SECRET=...
```

---

# 🛡️ System Architecture & Documentation

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
        Orchestrator --> Watcher["👁️ Watcher Agent"]
        Orchestrator --> Analyzer["🧠 Analyzer Agent (Gemini 1.5 Pro)"]
        Orchestrator --> Pattern["📊 Pattern Agent"]
        Orchestrator --> Alerter["🚨 Alerter Agent"]
        Orchestrator --> Blocker["🛡️ Blocker Agent"]
        
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

## 2. The Analysis Workflow (Sequence Diagram)

This diagram shows exactly what happens when a user receives a suspicious message. The entire process completes in **under 2 seconds**.

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

## 3. Deployment Topology

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

