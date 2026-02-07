import logging
from typing import Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from config.settings import settings

logger = logging.getLogger("scamshield.gemini")

llm: Optional[ChatGoogleGenerativeAI] = None


def init_llm() -> ChatGoogleGenerativeAI:
    """Initialize Gemini LLM with retry-friendly settings."""
    global llm
    
    try:
        llm = ChatGoogleGenerativeAI(
            model=settings.GEMINI_MODEL,
            google_api_key=settings.GEMINI_API_KEY,
            temperature=settings.GEMINI_TEMPERATURE,
            max_output_tokens=settings.GEMINI_MAX_TOKENS,
            request_timeout=60,  # Longer timeout for rate limiting
            max_retries=3,  # Retry on transient errors
        )
        logger.info(f"Gemini {settings.GEMINI_MODEL} initialized successfully")
        return llm
    except Exception as e:
        logger.error(f"Failed to initialize Gemini (Continuing without LLM): {type(e).__name__}: {e}")
        return None


def get_llm() -> ChatGoogleGenerativeAI:
    if llm is None:
        return init_llm()
    return llm
 

SCAM_ANALYSIS_SYSTEM_PROMPT = """You are an expert scam detection AI. Analyze the following message for scam indicators.

Check for these manipulation tactics:
1. URGENCY: Words like "URGENT", "ACT NOW", "IMMEDIATELY", "LIMITED TIME"
2. AUTHORITY: Claims from "IRS", "Bank", "Police", "Government", "Social Security"
3. THREATS: "suspended", "arrested", "legal action", "account closed"
4. TOO_GOOD: "You won!", "Free money", "Selected winner", "Inheritance"
5. SUSPICIOUS_URLS: Shortened URLs, misspellings, unusual domains
6. EMOTIONAL: "Your grandson needs help", "Family emergency"
7. INFO_REQUEST: Asking for SSN, passwords, OTP, bank details

Respond ONLY in valid JSON format. Do not use markdown code blocks or backticks:
{
    "risk_score": <0-100 integer>,
    "detected_tactics": [<list of tactics found from above>],
    "analysis": {
        "urgency_indicators": [<phrases that create urgency>],
        "authority_claims": [<entities being impersonated>],
        "threats_found": [<threatening language>],
        "suspicious_elements": [<other suspicious elements>]
    },
    "confidence": <0.0-1.0 float>,
    "explanation": "<brief one-line explanation>"
}"""


def get_analysis_prompt(sender: str, message: str, urls: list) -> str:
    return f"""Analyze this message for scam indicators:

SENDER: {sender}
MESSAGE: {message}
URLS FOUND: {urls if urls else "None"}

Respond with JSON only."""
