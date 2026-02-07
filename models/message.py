from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


class MessageAnalyzeRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000)
    sender: str


class MessageResponse(BaseModel):
    id: str
    sender: str
    content: str
    received_at: datetime
    is_scam: bool
    risk_score: int


class ExtractedData(BaseModel):
    urls: List[str] = Field(default_factory=list)
    phone_numbers: List[str] = Field(default_factory=list)
    email_addresses: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)


class WatcherOutput(BaseModel):
    sender: str
    content: str
    content_cleaned: str
    urls: List[str]
    timestamp: datetime
    extracted_data: Optional[ExtractedData] = None
