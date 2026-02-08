import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext

from config.settings import settings
from models.user import UserCreate, UserLogin, TokenResponse
from models.message import MessageAnalyzeRequest
from models.scam import AnalysisResponse, ScamReport, StatsResponse, AgentState
from services import database
from services.redis_client import check_rate_limit
from services.elasticsearch_client import es_client, get_user_stats_aggregation

logger = logging.getLogger("scamshield.api")

router = APIRouter()
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
security = HTTPBearer()

scam_workflow = None


def set_workflow(workflow):
    global scam_workflow
    scam_workflow = workflow


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRY_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(credentials.credentials, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        return {"user_id": user_id, "email": payload.get("email")}
    except JWTError:
        raise credentials_exception


@router.get("/", tags=["Health"])
async def root():
    return {
        "status": "online",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/api/v1/auth/register", response_model=TokenResponse, tags=["Auth"])
async def register(user: UserCreate):
    if database.db_pool is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database connection unavailable")
    try:
        async with database.db_pool.acquire() as conn:
            existing = await conn.fetchrow("SELECT id FROM users WHERE email = $1", user.email)
            if existing:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
            
            user_id = uuid.uuid4()
            await conn.execute(
                "INSERT INTO users (id, email, phone, password_hash) VALUES ($1, $2, $3, $4)",
                user_id, user.email, user.phone, hash_password(user.password)
            )
            await conn.execute("INSERT INTO user_settings (user_id) VALUES ($1)", user_id)
        
        token = create_access_token({"sub": str(user_id), "email": user.email})
        logger.info(f"New user registered: {user.email}")
        return TokenResponse(access_token=token)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/api/v1/auth/login", response_model=TokenResponse, tags=["Auth"])
async def login(credentials: UserLogin):
    if database.db_pool is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database connection unavailable")
    async with database.db_pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT id, email, password_hash FROM users WHERE email = $1",
            credentials.email
        )
        if not user or not verify_password(credentials.password, user['password_hash']):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    
    token = create_access_token({"sub": str(user['id']), "email": user['email']})
    logger.info(f"User logged in: {credentials.email}")
    return TokenResponse(access_token=token)


@router.post("/api/v1/analyze", response_model=AnalysisResponse, tags=["Detection"])
async def analyze_message(request: MessageAnalyzeRequest, current_user: dict = Depends(get_current_user)):
    user_id = current_user["user_id"]
    
    if not await check_rate_limit(user_id):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")
    
    if scam_workflow is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Workflow not initialized")
    
    initial_state: AgentState = {
        "message": request.message,
        "sender": request.sender,
        "user_id": user_id,
        "timestamp": datetime.utcnow(),
        "urls": [],
        "content_cleaned": "",
        "risk_score": 0,
        "analysis": {},
        "detected_tactics": [],
        "confidence": 0.0,
        "known_scammer": False,
        "previous_reports": 0,
        "similar_patterns": [],
        "url_malicious": False,
        "pattern_confidence": 0,
        "alerted": False,
        "channels_used": [],
        "family_notified": False,
        "blocked": False,
        "logged": False,
        "community_updated": False,
        "final_decision": "PASS",
        "actions_taken": [],
        "processing_start": datetime.utcnow()
    }
    
    start_time = datetime.utcnow()
    result = await scam_workflow.ainvoke(initial_state)
    processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
    
    logger.info(f"Analysis: {result['final_decision']} (risk: {result['risk_score']}, time: {processing_time}ms)")
    
    return AnalysisResponse(
        risk_score=result['risk_score'],
        decision=result['final_decision'],
        analysis={
            "llm_analysis": result['analysis'],
            "detected_tactics": result['detected_tactics'],
            "known_scammer": result['known_scammer'],
            "previous_reports": result['previous_reports'],
            "similar_patterns": result['similar_patterns'][:3],
            "url_malicious": result['url_malicious']
        },
        actions_taken=result['actions_taken'],
        processing_time_ms=processing_time
    )


@router.get("/api/v1/scams", tags=["Detection"])
async def get_blocked_scams(limit: int = 50, offset: int = 0, current_user: dict = Depends(get_current_user)):
    user_id = current_user["user_id"]
    async with database.db_pool.acquire() as conn:
        scams = await conn.fetch(
            """SELECT blocked_identifier, identifier_type, reason, blocked_at, auto_blocked
               FROM user_blocklist WHERE user_id = $1 ORDER BY blocked_at DESC LIMIT $2 OFFSET $3""",
            uuid.UUID(user_id), limit, offset
        )
        total = await conn.fetchval("SELECT COUNT(*) FROM user_blocklist WHERE user_id = $1", uuid.UUID(user_id))
    return {"scams": [dict(s) for s in scams], "limit": limit, "offset": offset, "total": total}


@router.get("/api/v1/stats", response_model=StatsResponse, tags=["Detection"])
async def get_stats(current_user: dict = Depends(get_current_user)):
    user_id = current_user["user_id"]
    async with database.db_pool.acquire() as conn:
        total_blocked = await conn.fetchval("SELECT COUNT(*) FROM user_blocklist WHERE user_id = $1", uuid.UUID(user_id)) or 0
        blocked_today = await conn.fetchval(
            "SELECT COUNT(*) FROM user_blocklist WHERE user_id = $1 AND blocked_at >= CURRENT_DATE",
            uuid.UUID(user_id)
        ) or 0
    
    try:
        stats = await get_user_stats_aggregation(user_id)
        top_scam_types = [{"type": b["key"], "count": b["doc_count"]} for b in stats.get("scam_types", [])]
    except Exception:
        top_scam_types = []
    
    protection_score = min(100.0, 50.0 + (total_blocked * 2))
    return StatsResponse(total_blocked=total_blocked, blocked_today=blocked_today, top_scam_types=top_scam_types, protection_score=protection_score)


@router.post("/api/v1/report", tags=["Detection"])
async def report_scam(report: ScamReport, current_user: dict = Depends(get_current_user)):
    user_id = current_user["user_id"]
    try:
        await es_client.index(
            index="scam_numbers",
            id=report.sender,
            document={
                "phone_number": report.sender,
                "report_count": 1,
                "first_reported": datetime.utcnow().isoformat(),
                "last_reported": datetime.utcnow().isoformat(),
                "scam_types": [report.scam_type] if report.scam_type else ["unknown"],
                "blocked_by_users": 1,
                "reported_by": user_id
            },
            op_type="create"
        )
    except Exception:
        await es_client.update(
            index="scam_numbers",
            id=report.sender,
            body={"script": {"source": "ctx._source.report_count++; ctx._source.last_reported = params.now", "params": {"now": datetime.utcnow().isoformat()}}}
        )
    logger.info(f"Scam reported by {user_id}: {report.sender}")
    return {"status": "reported", "sender": report.sender}

