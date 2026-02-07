import hashlib
import logging
import uuid
from datetime import datetime
from typing import List
from models.scam import AgentState
from services import database
from services.elasticsearch_client import log_incident, update_scam_number
from config.settings import settings

logger = logging.getLogger("scamshield.agents.blocker")


def determine_decision(state: AgentState) -> str:
    risk_score = state.get('risk_score', 0)
    pattern_confidence = state.get('pattern_confidence', 0)
    final_score = max(risk_score, pattern_confidence)
    
    known_scammer = state.get('known_scammer', False)
    url_malicious = state.get('url_malicious', False)
    
    if final_score > settings.RISK_SCORE_BLOCK_THRESHOLD or known_scammer or url_malicious:
        return "BLOCK"
    elif final_score > settings.RISK_SCORE_WARN_THRESHOLD:
        return "WARN"
    else:
        return "PASS"


def hash_message(message: str) -> str:
    return hashlib.sha256(message.encode()).hexdigest()


async def add_to_blocklist(user_id: str, sender: str, reason: str) -> bool:
    try:
        async with database.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO user_blocklist 
                (user_id, blocked_identifier, identifier_type, reason, auto_blocked)
                VALUES ($1, $2, $3, $4, true)
                ON CONFLICT (user_id, blocked_identifier) DO UPDATE 
                SET reason = $4, blocked_at = NOW()
            """,
                uuid.UUID(user_id),
                sender,
                'phone' if sender.startswith('+') or sender[0].isdigit() else 'email',
                reason
            )
        return True
    except Exception as e:
        logger.error(f"Failed to add to blocklist: {e}")
        return False


async def log_incident_to_es(state: AgentState, decision: str) -> bool:
    processing_time = 0
    if state.get('processing_start'):
        processing_time = int((datetime.utcnow() - state['processing_start']).total_seconds() * 1000)
    
    incident = {
        "timestamp": datetime.utcnow().isoformat(),
        "user_id": state.get('user_id', ''),
        "sender": state.get('sender', ''),
        "message_hash": hash_message(state.get('message', '')),
        "risk_score": state.get('risk_score', 0),
        "decision": decision,
        "agents_involved": ["watcher", "analyzer", "pattern", "alerter", "blocker"],
        "actions_taken": state.get('actions_taken', []),
        "processing_time_ms": processing_time
    }
    return await log_incident(incident)


async def blocker_agent(state: AgentState) -> AgentState:
    logger.info("Blocker Agent: Taking protective actions")
    
    actions_taken: List[str] = []
    blocked = False
    logged = False
    community_updated = False
    
    final_decision = determine_decision(state)
    
    if final_decision == "BLOCK":
        reason = f"Auto-blocked: Risk score {state.get('risk_score', 0)}"
        blocked = await add_to_blocklist(
            user_id=state.get('user_id', ''),
            sender=state.get('sender', ''),
            reason=reason
        )
        if blocked:
            actions_taken.append("sender_blocked")
        
        logged = await log_incident_to_es(state, final_decision)
        if logged:
            actions_taken.append("incident_logged")
        
        community_updated = await update_scam_number(
            phone_number=state.get('sender', ''),
            scam_types=state.get('detected_tactics', ['unknown']),
            risk_score=state.get('risk_score', 0)
        )
        if community_updated:
            actions_taken.append("community_database_updated")
    
    elif final_decision == "WARN":
        logged = await log_incident_to_es(state, final_decision)
        if logged:
            actions_taken.append("warning_logged")
    else:
        actions_taken.append("passed")
    
    return {
        **state,
        "final_decision": final_decision,
        "blocked": blocked,
        "logged": logged,
        "community_updated": community_updated,
        "actions_taken": actions_taken
    }
