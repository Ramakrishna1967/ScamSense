# ScamShield

Multi-Agent AI Scam Detection System using FastAPI, LangGraph, OpenAI GPT-4o, Elasticsearch, PostgreSQL, and Redis.

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
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql://...
ES_CLOUD_ID=...
ES_API_KEY=...
REDIS_URL=redis://...
JWT_SECRET=...
```
