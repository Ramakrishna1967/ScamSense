import logging
from typing import Dict, Any, List
from models.scam import AgentState
from services.elasticsearch_client import (
    search_scam_number,
    search_malicious_url,
    search_similar_patterns
)

logger = logging.getLogger("scamshield.agents.pattern")


def calculate_pattern_confidence(
    known_scammer: bool,
    previous_reports: int,
    url_malicious: bool,
    similar_patterns: List[Dict[str, Any]]
) -> int:
    confidence = 0
    if known_scammer:
        confidence += 40
    if url_malicious:
        confidence += 30
    confidence += min(30, len(similar_patterns) * 10)
    confidence += min(20, previous_reports * 0.5)
    return min(100, int(confidence))


async def pattern_agent(state: AgentState) -> AgentState:
    logger.info("Pattern Agent: Searching Elasticsearch for matches")
    
    known_scammer = False
    previous_reports = 0
    similar_patterns = []
    url_malicious = False
    
    sender_result = await search_scam_number(state['sender'])
    if sender_result:
        known_scammer = True
        previous_reports = sender_result.get('report_count', 0)
    
    urls = state.get('urls', [])
    for url in urls:
        if await search_malicious_url(url):
            url_malicious = True
            break
    
    message = state.get('message', '')
    if message:
        similar_patterns = await search_similar_patterns(message, size=5)
    
    pattern_confidence = calculate_pattern_confidence(
        known_scammer=known_scammer,
        previous_reports=previous_reports,
        url_malicious=url_malicious,
        similar_patterns=similar_patterns
    )
    
    return {
        **state,
        "known_scammer": known_scammer,
        "previous_reports": previous_reports,
        "similar_patterns": similar_patterns,
        "url_malicious": url_malicious,
        "pattern_confidence": pattern_confidence
    }
