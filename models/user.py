from typing import Optional
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime


class UserCreate(BaseModel):
    email: EmailStr
    phone: Optional[str] = None
    password: str = Field(..., min_length=8)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    phone: Optional[str] = None
    created_at: datetime
    subscription_tier: str = "free"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 900


class UserSettings(BaseModel):
    alert_methods: dict = Field(default={"push": True, "email": False})
    aggressive_blocking: bool = False
    family_alerts_enabled: bool = True
    auto_report_to_authorities: bool = False


class TrustedContact(BaseModel):
    name: str = Field(..., max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    relationship: Optional[str] = Field(None, max_length=50)
    notify_on_scam: bool = True
