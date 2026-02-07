from typing import TypedDict, Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class AgentState(TypedDict):
    message: str
    sender: str
    user_id: str
    timestamp: datetime
    urls: List[str]
    content_cleaned: str
    risk_score: int
    analysis: Dict[str, Any]
    detected_tactics: List[str]
    confidence: float
    known_scammer: bool
    previous_reports: int
    similar_patterns: List[Dict[str, Any]]
    url_malicious: bool
    pattern_confidence: int
    alerted: bool
    channels_used: List[str]
    family_notified: bool
    blocked: bool
    logged: bool
    community_updated: bool
    final_decision: str
    actions_taken: List[str]
    processing_start: datetime


class LLMAnalysis(BaseModel):
    urgency_indicators: List[str] = Field(default_factory=list)
    authority_claims: List[str] = Field(default_factory=list)
    threats_found: List[str] = Field(default_factory=list)
    suspicious_elements: List[str] = Field(default_factory=list)
    explanation: Optional[str] = None


class PatternMatch(BaseModel):
    pattern: str
    score: float
    category: str


class AnalysisResponse(BaseModel):
    risk_score: int = Field(..., ge=0, le=100)
    decision: str = Field(..., pattern="^(BLOCK|WARN|PASS)$")
    analysis: Dict[str, Any]
    actions_taken: List[str] = Field(default_factory=list)
    processing_time_ms: int


class ScamReport(BaseModel):
    sender: str
    message: str
    scam_type: Optional[str] = None


class ScamTypeCount(BaseModel):
    type: str
    count: int


class StatsResponse(BaseModel):
    total_blocked: int
    blocked_today: int
    top_scam_types: List[Dict[str, Any]] = Field(default_factory=list)
    protection_score: float = Field(..., ge=0, le=100)


class BlockedScam(BaseModel):
    blocked_identifier: str
    identifier_type: str
    reason: Optional[str]
    blocked_at: datetime
    auto_blocked: bool


class BlockedScamsResponse(BaseModel):
    scams: List[BlockedScam]
    limit: int
    offset: int
    total: Optional[int] = None
