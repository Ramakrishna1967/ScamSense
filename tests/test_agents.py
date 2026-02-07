import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch
import sys
sys.path.insert(0, '..')
from models.scam import AgentState


def create_test_state(message: str = "Test message", sender: str = "+1-555-123-4567", user_id: str = "test-user-123") -> AgentState:
    return AgentState(
        message=message,
        sender=sender,
        user_id=user_id,
        timestamp=datetime.utcnow(),
        urls=[],
        content_cleaned="",
        risk_score=0,
        analysis={},
        detected_tactics=[],
        confidence=0.0,
        known_scammer=False,
        previous_reports=0,
        similar_patterns=[],
        url_malicious=False,
        pattern_confidence=0,
        alerted=False,
        channels_used=[],
        family_notified=False,
        blocked=False,
        logged=False,
        community_updated=False,
        final_decision="PASS",
        actions_taken=[],
        processing_start=datetime.utcnow()
    )


class TestWatcherAgent:
    def test_extract_urls(self):
        from agents.watcher import extract_urls
        text = "Click here: https://example.com/login"
        urls = extract_urls(text)
        assert len(urls) == 1
        assert "https://example.com/login" in urls
    
    def test_clean_content(self):
        from agents.watcher import clean_content
        text = "Click https://scam.com to win!"
        urls = ["https://scam.com"]
        cleaned = clean_content(text, urls)
        assert "[URL]" in cleaned
        assert "https://scam.com" not in cleaned


class TestAnalyzerAgent:
    def test_parse_llm_response(self):
        from agents.analyzer import parse_llm_response
        response = '{"risk_score": 85, "detected_tactics": ["URGENCY"], "analysis": {}, "confidence": 0.9}'
        parsed = parse_llm_response(response)
        assert parsed['risk_score'] == 85
        assert 'URGENCY' in parsed['detected_tactics']


class TestPatternAgent:
    def test_calculate_pattern_confidence(self):
        from agents.pattern import calculate_pattern_confidence
        confidence = calculate_pattern_confidence(known_scammer=True, previous_reports=0, url_malicious=False, similar_patterns=[])
        assert confidence == 40
        confidence = calculate_pattern_confidence(known_scammer=True, previous_reports=0, url_malicious=True, similar_patterns=[])
        assert confidence == 70


class TestBlockerAgent:
    def test_determine_decision(self):
        from agents.blocker import determine_decision
        state = create_test_state()
        state['risk_score'] = 85
        assert determine_decision(state) == "BLOCK"
        state['risk_score'] = 50
        state['known_scammer'] = False
        assert determine_decision(state) == "WARN"
        state['risk_score'] = 20
        assert determine_decision(state) == "PASS"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
