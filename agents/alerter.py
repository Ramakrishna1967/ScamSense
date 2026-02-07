import json
import logging
from datetime import datetime
from typing import List
from models.scam import AgentState
from config.settings import settings

logger = logging.getLogger("scamshield.agents.alerter")

websocket_manager = None


def set_websocket_manager(manager):
    global websocket_manager
    websocket_manager = manager


def should_alert(state: AgentState) -> bool:
    return (
        state.get('risk_score', 0) > settings.RISK_SCORE_BLOCK_THRESHOLD or
        state.get('pattern_confidence', 0) > settings.RISK_SCORE_BLOCK_THRESHOLD or
        state.get('known_scammer', False) or
        state.get('url_malicious', False)
    )


def should_warn(state: AgentState) -> bool:
    return (
        max(state.get('risk_score', 0), state.get('pattern_confidence', 0)) > settings.RISK_SCORE_WARN_THRESHOLD and
        not should_alert(state)
    )


async def send_websocket_alert(user_id: str, alert_data: dict) -> bool:
    if websocket_manager is None:
        return False
    try:
        if user_id in websocket_manager.active_connections:
            await websocket_manager.send_personal_message(json.dumps(alert_data), user_id)
            return True
    except Exception as e:
        logger.error(f"WebSocket send failed: {e}")
    return False


async def alerter_agent(state: AgentState) -> AgentState:
    logger.info("Alerter Agent: Checking if alerts needed")
    
    user_id = state.get('user_id', '')
    alerted = False
    channels_used: List[str] = []
    family_notified = False
    
    if should_alert(state):
        alert_type = "SCAM_BLOCKED"
    elif should_warn(state):
        alert_type = "SCAM_WARNING"
    else:
        return {
            **state,
            "alerted": False,
            "channels_used": [],
            "family_notified": False
        }
    
    alert_data = {
        "type": alert_type,
        "sender": state.get('sender', 'Unknown'),
        "risk_score": max(state.get('risk_score', 0), state.get('pattern_confidence', 0)),
        "detected_tactics": state.get('detected_tactics', []),
        "timestamp": datetime.utcnow().isoformat()
    }
    
    ws_sent = await send_websocket_alert(user_id, alert_data)
    if ws_sent:
        channels_used.append("websocket")
        alerted = True
    
    return {
        **state,
        "alerted": alerted,
        "channels_used": channels_used,
        "family_notified": family_notified
    }
