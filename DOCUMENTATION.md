# ScamShield - Complete Code Documentation

This document explains every file in the ScamShield project in detail.

---

## Table of Contents
1. [Root Files](#root-files)
2. [Config Module](#config-module)
3. [Models Module](#models-module)
4. [Services Module](#services-module)
5. [Agents Module](#agents-module)
6. [API Module](#api-module)
7. [Scripts](#scripts)
8. [Frontend](#frontend)
9. [Tests](#tests)
10. [Data Flow](#data-flow)

---

## Root Files

### `main.py`
The all-in-one version containing everything in a single 33KB file. Useful for hackathons or quick demos. Contains:
- FastAPI application setup
- All 5 LangGraph agents inline
- Database connection code
- JWT authentication
- WebSocket handler
- All API routes

### `main_modular.py`
The production version that imports from organized modules:

```python
from config.settings import settings              # Load config
from services.database import init_postgres       # DB connection
from agents.watcher import watcher_agent          # Import agents
from api.routes import router                     # API routes

def create_scam_detection_workflow():
    # Builds LangGraph: Watcher -> Analyzer -> Pattern -> Alerter -> Blocker
    workflow = StateGraph(AgentState)
    workflow.add_node("watcher", watcher_agent)
    workflow.add_node("analyzer", analyzer_agent)
    # ... add remaining nodes and edges
    return workflow.compile()

async def lifespan(app):
    # Startup: Initialize all connections
    await init_postgres()
    await init_elasticsearch()
    await init_redis()
    init_llm()
    # Shutdown: Close all connections
```

### `requirements.txt`
Python dependencies:
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `langgraph` - Agent orchestration
- `langchain-openai` - GPT-4o integration
- `asyncpg` - Async PostgreSQL driver
- `elasticsearch` - Elasticsearch client
- `redis` - Redis client
- `pydantic` - Data validation
- `python-jose` - JWT tokens
- `passlib` - Password hashing

### `.env.example`
Environment variables template:
```
OPENAI_API_KEY=sk-...           # Required for GPT-4o
DATABASE_URL=postgresql://...    # PostgreSQL connection
ES_CLOUD_ID=...                  # Elasticsearch cloud
ES_API_KEY=...                   # Elasticsearch auth
REDIS_URL=redis://localhost:6379 # Redis connection
JWT_SECRET=your-secret-key       # For signing tokens
```

---

## Config Module

### `config/__init__.py`
Exports the settings object:
```python
from .settings import settings, Settings
```

### `config/settings.py`
Centralized configuration using Pydantic Settings:

```python
class Settings(BaseSettings):
    # App info
    APP_NAME: str = "ScamShield"
    APP_VERSION: str = "1.0.0"
    
    # OpenAI
    OPENAI_API_KEY: str              # Required
    OPENAI_MODEL: str = "gpt-4o"     # Default model
    OPENAI_TEMPERATURE: float = 0.1  # Low = more deterministic
    
    # PostgreSQL
    DATABASE_URL: str = "postgresql://..."
    DB_POOL_MIN_SIZE: int = 5
    DB_POOL_MAX_SIZE: int = 20
    
    # Elasticsearch
    ES_CLOUD_ID: Optional[str] = None
    ES_API_KEY: Optional[str] = None
    ES_URL: str = "http://localhost:9200"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    
    # JWT Auth
    JWT_SECRET: str = "change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_MINUTES: int = 15
    
    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 100
    
    # Risk thresholds
    RISK_SCORE_BLOCK_THRESHOLD: int = 70   # Score > 70 = BLOCK
    RISK_SCORE_WARN_THRESHOLD: int = 40    # Score 40-70 = WARN
```

**How it works**: Pydantic automatically reads values from `.env` file and validates types.

---

## Models Module

### `models/__init__.py`
Exports all models:
```python
from .user import UserCreate, UserLogin, TokenResponse
from .message import MessageAnalyzeRequest
from .scam import AgentState, AnalysisResponse
```

### `models/user.py`
User-related Pydantic models:

```python
class UserCreate(BaseModel):
    email: EmailStr           # Must be valid email
    phone: Optional[str]      # Optional phone number
    password: str = Field(..., min_length=8)  # Min 8 chars

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str         # JWT token
    token_type: str = "bearer"
    expires_in: int = 900     # 15 minutes
```

### `models/message.py`
Message analysis models:

```python
class MessageAnalyzeRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000)
    sender: str               # Phone number or email

class ExtractedData(BaseModel):
    urls: List[str]           # Found URLs
    phone_numbers: List[str]  # Found phone numbers
    email_addresses: List[str]
```

### `models/scam.py`
Core scam detection models:

```python
class AgentState(TypedDict):
    """State that flows through all 5 agents"""
    
    # INPUT (from user request)
    message: str              # Original message text
    sender: str               # Who sent it
    user_id: str              # Logged-in user
    timestamp: datetime
    
    # WATCHER OUTPUT
    urls: List[str]           # Extracted URLs
    content_cleaned: str      # Message with URLs replaced
    
    # ANALYZER OUTPUT (GPT-4o)
    risk_score: int           # 0-100
    analysis: Dict            # Detailed breakdown
    detected_tactics: List[str]  # ["URGENCY", "AUTHORITY", etc]
    confidence: float         # 0.0-1.0
    
    # PATTERN OUTPUT (Elasticsearch)
    known_scammer: bool       # Sender in database?
    previous_reports: int     # How many times reported
    similar_patterns: List    # Similar scam messages found
    url_malicious: bool       # URL in blacklist?
    pattern_confidence: int   # 0-100
    
    # ALERTER OUTPUT
    alerted: bool             # Was user notified?
    channels_used: List[str]  # ["websocket", "email"]
    family_notified: bool
    
    # BLOCKER OUTPUT (final)
    blocked: bool             # Was sender blocked?
    logged: bool              # Was incident logged?
    community_updated: bool   # Was scammer added to DB?
    final_decision: str       # "BLOCK" | "WARN" | "PASS"
    actions_taken: List[str]  # ["sender_blocked", "incident_logged"]

class AnalysisResponse(BaseModel):
    """API response for /api/v1/analyze"""
    risk_score: int           # 0-100
    decision: str             # BLOCK, WARN, or PASS
    analysis: Dict            # Detailed info
    actions_taken: List[str]
    processing_time_ms: int
```

---

## Services Module

### `services/__init__.py`
Exports all service clients and functions.

### `services/database.py`
PostgreSQL connection using asyncpg:

```python
db_pool: Optional[asyncpg.Pool] = None  # Global connection pool

async def init_postgres():
    """Create connection pool on startup"""
    global db_pool
    db_pool = await asyncpg.create_pool(
        settings.DATABASE_URL,
        min_size=5,      # Always keep 5 connections ready
        max_size=20      # Max 20 concurrent connections
    )

async def close_postgres():
    """Close pool on shutdown"""
    await db_pool.close()

async def fetch_one(query, *args):
    """Execute query, return single row"""
    async with db_pool.acquire() as conn:
        return await conn.fetchrow(query, *args)
```

### `services/elasticsearch_client.py`
Elasticsearch operations:

```python
async def search_scam_number(phone_number):
    """Check if phone number is known scammer"""
    result = await es_client.search(
        index="scam_numbers",
        query={"term": {"phone_number": phone_number}}
    )
    if result['hits']['total']['value'] > 0:
        return result['hits']['hits'][0]['_source']  # Found!
    return None  # Not in database

async def search_malicious_url(url):
    """Check if URL is in blacklist"""
    result = await es_client.search(
        index="reported_urls",
        query={"term": {"url": url}}
    )
    return result['hits']['total']['value'] > 0

async def search_similar_patterns(message):
    """Fuzzy search for similar scam messages"""
    result = await es_client.search(
        index="scam_patterns",
        query={"match": {"pattern_text": {"query": message, "fuzziness": "AUTO"}}}
    )
    return [hit['_source'] for hit in result['hits']['hits']]

async def log_incident(incident_data):
    """Save detection event for analytics"""
    await es_client.index(index="incident_logs", document=incident_data)
```

### `services/redis_client.py`
Redis for rate limiting and caching:

```python
async def check_rate_limit(user_id, limit=100):
    """Check if user exceeded 100 requests/minute"""
    key = f"rate_limit:{user_id}"
    current = await redis_client.incr(key)  # Increment counter
    if current == 1:
        await redis_client.expire(key, 60)  # Set 60 second expiry
    return current <= limit  # True = allowed, False = blocked

async def cache_set(key, value, ttl=300):
    """Cache data for 5 minutes"""
    await redis_client.setex(f"cache:{key}", ttl, json.dumps(value))

async def cache_get(key):
    """Retrieve cached data"""
    value = await redis_client.get(f"cache:{key}")
    return json.loads(value) if value else None
```

### `services/openai_client.py`
GPT-4o configuration:

```python
def init_llm():
    """Initialize ChatOpenAI client"""
    global llm
    llm = ChatOpenAI(
        model="gpt-4o",
        api_key=settings.OPENAI_API_KEY,
        temperature=0.1  # Low = consistent responses
    )

SCAM_ANALYSIS_SYSTEM_PROMPT = """
You are an expert scam detection AI. Analyze for these tactics:
1. URGENCY: "ACT NOW", "LIMITED TIME"
2. AUTHORITY: Claims from "IRS", "Bank", "Police"
3. THREATS: "arrested", "account suspended"
4. TOO_GOOD: "You won!", "Free money"
5. SUSPICIOUS_URLS: Shortened links, misspellings
6. EMOTIONAL: "Family emergency"
7. INFO_REQUEST: Asking for SSN, passwords

Respond in JSON format:
{
    "risk_score": 0-100,
    "detected_tactics": ["URGENCY", "THREATS"],
    "confidence": 0.0-1.0
}
"""
```

---

## Agents Module

### `agents/watcher.py` (Agent 1 - Preprocessing)

```python
def extract_urls(text):
    """Find all URLs using regex"""
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    urls = re.findall(url_pattern, text)
    # Also find bit.ly, t.co, etc.
    return urls

def clean_content(text, urls):
    """Replace URLs with [URL] placeholder"""
    content = text
    for url in urls:
        content = content.replace(url, '[URL]')
    return content

async def watcher_agent(state):
    """
    Agent 1: Capture and preprocess message
    
    Input: state with 'message', 'sender'
    Output: state + 'urls', 'content_cleaned'
    """
    urls = extract_urls(state['message'])
    cleaned = clean_content(state['message'], urls)
    
    return {
        **state,
        "urls": urls,
        "content_cleaned": cleaned
    }
```

### `agents/analyzer.py` (Agent 2 - GPT-4o Analysis)

```python
def parse_llm_response(response_text):
    """Parse JSON from GPT response"""
    # Handle markdown code blocks
    if response_text.startswith('```'):
        lines = response_text.split('\n')
        response_text = '\n'.join(lines[1:-1])
    return json.loads(response_text)

async def analyzer_agent(state):
    """
    Agent 2: Analyze message with GPT-4o
    
    Input: state with 'content_cleaned', 'urls'
    Output: state + 'risk_score', 'detected_tactics', 'confidence'
    """
    response = await llm.ainvoke([
        SystemMessage(content=SCAM_ANALYSIS_SYSTEM_PROMPT),
        HumanMessage(content=f"Analyze: {state['message']}")
    ])
    
    result = parse_llm_response(response.content)
    
    return {
        **state,
        "risk_score": result['risk_score'],      # 0-100
        "detected_tactics": result['detected_tactics'],
        "confidence": result['confidence']
    }
```

### `agents/pattern.py` (Agent 3 - Elasticsearch Matching)

```python
def calculate_pattern_confidence(known_scammer, reports, url_malicious, patterns):
    """Calculate confidence score 0-100"""
    confidence = 0
    if known_scammer: confidence += 40    # Big red flag
    if url_malicious: confidence += 30    # Bad URL
    confidence += min(30, len(patterns) * 10)  # Similar patterns
    return min(100, confidence)

async def pattern_agent(state):
    """
    Agent 3: Search Elasticsearch for known patterns
    
    Input: state with 'sender', 'urls', 'message'
    Output: state + 'known_scammer', 'similar_patterns', etc.
    """
    # Check if sender is known scammer
    scammer = await search_scam_number(state['sender'])
    known_scammer = scammer is not None
    
    # Check if any URL is malicious
    url_malicious = False
    for url in state['urls']:
        if await search_malicious_url(url):
            url_malicious = True
            break
    
    # Find similar scam patterns
    patterns = await search_similar_patterns(state['message'])
    
    return {
        **state,
        "known_scammer": known_scammer,
        "previous_reports": scammer['report_count'] if scammer else 0,
        "similar_patterns": patterns,
        "url_malicious": url_malicious,
        "pattern_confidence": calculate_pattern_confidence(...)
    }
```

### `agents/alerter.py` (Agent 4 - Notifications)

```python
def should_alert(state):
    """True if message is high-risk"""
    return (
        state['risk_score'] > 70 or
        state['known_scammer'] or
        state['url_malicious']
    )

async def alerter_agent(state):
    """
    Agent 4: Send real-time notifications
    
    Input: state with risk analysis
    Output: state + 'alerted', 'channels_used'
    """
    if should_alert(state):
        alert_data = {
            "type": "SCAM_BLOCKED",
            "sender": state['sender'],
            "risk_score": state['risk_score'],
            "detected_tactics": state['detected_tactics']
        }
        
        # Send via WebSocket
        await websocket_manager.send_personal_message(
            json.dumps(alert_data),
            state['user_id']
        )
        
        return {**state, "alerted": True, "channels_used": ["websocket"]}
    
    return {**state, "alerted": False, "channels_used": []}
```

### `agents/blocker.py` (Agent 5 - Protective Actions)

```python
def determine_decision(state):
    """Decide: BLOCK, WARN, or PASS"""
    if state['risk_score'] > 70 or state['known_scammer']:
        return "BLOCK"
    elif state['risk_score'] > 40:
        return "WARN"
    return "PASS"

async def blocker_agent(state):
    """
    Agent 5: Take protective actions
    
    Input: state with all analysis
    Output: state + 'final_decision', 'actions_taken'
    """
    decision = determine_decision(state)
    actions = []
    
    if decision == "BLOCK":
        # Add sender to user's blocklist (PostgreSQL)
        await db.execute(
            "INSERT INTO user_blocklist (user_id, blocked_identifier) VALUES ($1, $2)",
            state['user_id'], state['sender']
        )
        actions.append("sender_blocked")
        
        # Log incident (Elasticsearch)
        await log_incident({
            "user_id": state['user_id'],
            "sender": state['sender'],
            "risk_score": state['risk_score'],
            "decision": "BLOCK"
        })
        actions.append("incident_logged")
        
        # Update community database
        await update_scam_number(state['sender'], state['detected_tactics'])
        actions.append("community_database_updated")
    
    return {
        **state,
        "final_decision": decision,
        "actions_taken": actions
    }
```

---

## API Module

### `api/routes.py`
FastAPI REST endpoints:

```python
# Authentication helpers
def hash_password(password):
    return pwd_context.hash(password)  # bcrypt

def create_access_token(data):
    expire = datetime.utcnow() + timedelta(minutes=15)
    return jwt.encode({**data, "exp": expire}, JWT_SECRET)

# ENDPOINTS

@router.get("/")
async def health_check():
    return {"status": "online", "service": "ScamShield"}

@router.post("/api/v1/auth/register")
async def register(user: UserCreate):
    # Check if email exists
    # Hash password
    # Insert into PostgreSQL
    # Return JWT token

@router.post("/api/v1/auth/login")
async def login(creds: UserLogin):
    # Verify password
    # Return JWT token

@router.post("/api/v1/analyze")
async def analyze_message(request: MessageAnalyzeRequest, user = Depends(get_current_user)):
    """MAIN ENDPOINT - Run scam detection pipeline"""
    
    # 1. Rate limit check
    if not await check_rate_limit(user['user_id']):
        raise HTTPException(429, "Rate limit exceeded")
    
    # 2. Create initial state
    state = {
        "message": request.message,
        "sender": request.sender,
        "user_id": user['user_id'],
        ...
    }
    
    # 3. Run LangGraph workflow
    result = await scam_workflow.ainvoke(state)
    
    # 4. Return response
    return {
        "risk_score": result['risk_score'],
        "decision": result['final_decision'],
        "actions_taken": result['actions_taken']
    }

@router.get("/api/v1/scams")
async def get_blocked_scams(user = Depends(get_current_user)):
    # Query PostgreSQL for user's blocked list

@router.get("/api/v1/stats")
async def get_stats(user = Depends(get_current_user)):
    # Return: total_blocked, blocked_today, protection_score
```

### `api/websocket.py`
Real-time WebSocket connections:

```python
class WebSocketManager:
    def __init__(self):
        self.active_connections = {}  # {user_id: WebSocket}
    
    async def connect(self, websocket, user_id):
        await websocket.accept()
        self.active_connections[user_id] = websocket
    
    async def send_personal_message(self, message, user_id):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_text(message)

# Endpoint handler
async def websocket_endpoint(websocket, user_id):
    await manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(user_id)
```

---

## Scripts

### `scripts/init_database.py`
Creates PostgreSQL tables:

```python
TABLES = [
    """CREATE TABLE users (
        id UUID PRIMARY KEY,
        email VARCHAR(255) UNIQUE NOT NULL,
        password_hash VARCHAR(255) NOT NULL
    )""",
    
    """CREATE TABLE user_blocklist (
        id UUID PRIMARY KEY,
        user_id UUID REFERENCES users(id),
        blocked_identifier VARCHAR(255),
        reason TEXT,
        blocked_at TIMESTAMP DEFAULT NOW()
    )""",
    
    # ... more tables
]

async def init_database():
    conn = await asyncpg.connect(DATABASE_URL)
    for sql in TABLES:
        await conn.execute(sql)
```

### `scripts/init_elasticsearch.py`
Creates ES indices:

```python
INDICES = {
    "scam_numbers": {
        "mappings": {
            "properties": {
                "phone_number": {"type": "keyword"},
                "report_count": {"type": "integer"},
                "scam_types": {"type": "keyword"}
            }
        }
    },
    "scam_patterns": {
        "mappings": {
            "properties": {
                "pattern_text": {"type": "text"},  # Full-text search
                "category": {"type": "keyword"},
                "risk_score": {"type": "float"}
            }
        }
    }
}

# Also seeds sample data
SEED_DATA = {
    "scam_patterns": [
        {"pattern_text": "URGENT: Your account suspended", "risk_score": 95},
        {"pattern_text": "You've won $1,000,000!", "risk_score": 98}
    ]
}
```

---

## Frontend

### `frontend/index.html`
Dashboard structure:
- Login form with email/password
- Stats cards showing blocked count
- Live alerts section (WebSocket)
- Test message analyzer
- Blocked scammers list

### `frontend/styles.css`
Dark theme with:
- Purple gradient accents
- Card-based layout
- CSS Grid for responsiveness
- Animations for alerts

### `frontend/app.js`
JavaScript logic:
- `init()` - Check auth state, show login or dashboard
- `login()` - POST to /api/v1/auth/login, store JWT
- `connectWebSocket()` - Connect to /ws/{user_id}
- `loadStats()` - GET /api/v1/stats
- `analyzeMessage()` - POST to /api/v1/analyze

---

## Tests

### `tests/test_agents.py`
Unit tests for agent functions:
- URL extraction regex
- Content cleaning
- LLM response parsing
- Confidence calculation
- Decision logic (BLOCK/WARN/PASS)

### `tests/test_api.py`
API tests:
- Password hashing/verification
- JWT token creation
- Request validation

### `tests/test_elasticsearch.py`
ES tests with mocked client.

---

## Data Flow

```
1. User sends message via POST /api/v1/analyze
   {message: "You won $1M! Click here", sender: "+1-800-SCAM"}

2. Rate limiting check (Redis)
   - Increment counter for user
   - Block if > 100/minute

3. LangGraph Pipeline executes:

   WATCHER (Agent 1)
   ├─ Extract URLs: ["http://scam.link"]
   └─ Clean: "You won $1M! Click [URL]"

   ANALYZER (Agent 2)
   ├─ Send to GPT-4o
   └─ Result: risk_score=95, tactics=["TOO_GOOD", "URGENCY"]

   PATTERN (Agent 3)
   ├─ Search ES for +1-800-SCAM → known_scammer=true
   ├─ Search ES for scam.link → url_malicious=true
   └─ Search ES for similar patterns → 3 matches

   ALERTER (Agent 4)
   └─ Send WebSocket alert to user

   BLOCKER (Agent 5)
   ├─ decision = "BLOCK" (risk > 70)
   ├─ Add +1-800-SCAM to user's blocklist
   ├─ Log incident to ES
   └─ Update community scammer database

4. Return response:
   {
     risk_score: 95,
     decision: "BLOCK",
     actions_taken: ["sender_blocked", "incident_logged"]
   }
```
