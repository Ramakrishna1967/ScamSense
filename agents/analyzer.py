import json
import logging
from typing import Dict, Any
from langchain_core.messages import HumanMessage, SystemMessage
from models.scam import AgentState
from services.gemini_client import get_llm, SCAM_ANALYSIS_SYSTEM_PROMPT, get_analysis_prompt

logger = logging.getLogger("scamshield.agents.analyzer")


def parse_llm_response(response_text: str) -> Dict[str, Any]:
    import re
    import ast
    
    text = response_text.strip()
    
    # robust markdown cleanup
    if "```" in text:
        # extract content between code blocks
        match = re.search(r"```(?:\w+)?\n?(.*?)```", text, re.DOTALL)
        if match:
            text = match.group(1).strip()
            
    # Try to find JSON block if still not clean
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        text = json_match.group(0)
    
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        try:
            # Fallback for Python-style dicts (single quotes)
            return ast.literal_eval(text)
        except (ValueError, SyntaxError):
            logger.error(f"Failed to parse LLM response: {response_text[:200]}")
            return None


def get_default_analysis() -> Dict[str, Any]:
    return {
        "risk_score": 50,
        "detected_tactics": [],
        "analysis": {},
        "confidence": 0.0,
        "explanation": "Analysis failed - defaulting to medium risk"
    }


def fallback_analyze(message: str, sender: str) -> Dict[str, Any]:
    """
    Keyword-based fallback analyzer when Gemini API is unavailable.
    This ensures the system ALWAYS provides a meaningful score.
    """
    message_lower = message.lower()
    score = 0
    tactics = []
    analysis = {
        "urgency_indicators": [],
        "authority_claims": [],
        "threats_found": [],
        "suspicious_elements": []
    }
    
    # URGENCY detection (+20 points)
    urgency_words = ["urgent", "immediately", "act now", "limited time", "expires", "hurry", "asap", "right now"]
    for word in urgency_words:
        if word in message_lower:
            score += 20
            tactics.append("URGENCY")
            analysis["urgency_indicators"].append(word)
            break
    
    # AUTHORITY detection (+25 points)
    authority_words = ["irs", "bank", "police", "government", "social security", "fbi", "ssa", "tax", "citibank", "chase", "wells fargo"]
    for word in authority_words:
        if word in message_lower:
            score += 25
            tactics.append("AUTHORITY")
            analysis["authority_claims"].append(word)
            break
    
    # THREATS detection (+25 points)
    threat_words = ["suspended", "arrested", "legal action", "account closed", "warrant", "jail", "prosecute", "terminate"]
    for word in threat_words:
        if word in message_lower:
            score += 25
            tactics.append("THREATS")
            analysis["threats_found"].append(word)
            break
    
    # TOO_GOOD detection (+20 points)
    too_good_words = ["you won", "winner", "lottery", "free money", "inheritance", "million", "prize", "congratulations"]
    for word in too_good_words:
        if word in message_lower:
            score += 20
            tactics.append("TOO_GOOD")
            analysis["suspicious_elements"].append(word)
            break
    
    # INFO_REQUEST detection (+20 points)
    info_words = ["ssn", "social security", "password", "otp", "bank details", "credit card", "account number", "pin"]
    for word in info_words:
        if word in message_lower:
            score += 20
            tactics.append("INFO_REQUEST")
            analysis["suspicious_elements"].append(f"Requests: {word}")
            break
    
    # SUSPICIOUS URLs (+15 points)
    suspicious_url_patterns = ["bit.ly", "tinyurl", "goo.gl", "t.co", "-verify", "-secure", "-login"]
    for pattern in suspicious_url_patterns:
        if pattern in message_lower:
            score += 15
            tactics.append("SUSPICIOUS_URLS")
            analysis["suspicious_elements"].append(f"Suspicious URL: {pattern}")
            break
    
    # Cap at 100
    score = min(100, score)
    
    return {
        "risk_score": score,
        "detected_tactics": list(set(tactics)),
        "analysis": analysis,
        "confidence": 0.8 if score > 50 else 0.5,
        "explanation": f"Fallback analysis: detected {len(tactics)} scam indicators"
    }


async def analyzer_agent(state: AgentState) -> AgentState:
    """Analyze message with Gemini LLM, with retry logic for rate limiting."""
    import asyncio
    
    logger.info("Analyzer Agent: Analyzing message with Gemini")
    
    llm = get_llm()
    user_prompt = get_analysis_prompt(
        sender=state['sender'],
        message=state['message'],
        urls=state.get('urls', [])
    )
    
    max_retries = 3
    retry_delay = 5  # seconds
    
    for attempt in range(max_retries):
        try:
            response = await llm.ainvoke([
                SystemMessage(content=SCAM_ANALYSIS_SYSTEM_PROMPT),
                HumanMessage(content=user_prompt)
            ])
            
            raw_content = response.content
            logger.info(f"Gemini response received (attempt {attempt + 1})")

            
            result = parse_llm_response(raw_content)
            if result is None:
                logger.error(f"Failed to parse LLM response")
                result = get_default_analysis()
            
            return {
                **state,
                "risk_score": result.get("risk_score", 50),
                "analysis": result.get("analysis", {}),
                "detected_tactics": result.get("detected_tactics", []),
                "confidence": result.get("confidence", 0.5)
            }
            
        except Exception as e:
            error_str = str(e).lower()
            
            # Check for rate limiting errors
            if "429" in error_str or "rate" in error_str or "quota" in error_str or "resource" in error_str:
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"Rate limited. Retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})")
                    logger.warning(f"Rate limited by Gemini API. Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)
                    continue
            
            # Log the error
            import traceback
            traceback.print_exc()
            logger.error(f"Analyzer error (attempt {attempt + 1}): {type(e).__name__}: {str(e)}")
            
            # On final attempt, use FALLBACK ANALYZER instead of 50%
            if attempt == max_retries - 1:
                logger.info("Using fallback keyword-based analyzer")
                logger.info("Gemini unavailable - using fallback keyword analyzer")
                fallback_result = fallback_analyze(state['message'], state['sender'])
                return {
                    **state,
                    "risk_score": fallback_result["risk_score"],
                    "analysis": fallback_result["analysis"],
                    "detected_tactics": fallback_result["detected_tactics"],
                    "confidence": fallback_result["confidence"]
                }
    
    # Should not reach here, but use fallback just in case
    logger.info("Using fallback keyword-based analyzer (loop exit)")
    fallback_result = fallback_analyze(state['message'], state['sender'])
    return {
        **state,
        "risk_score": fallback_result["risk_score"],
        "analysis": fallback_result["analysis"],
        "detected_tactics": fallback_result["detected_tactics"],
        "confidence": fallback_result["confidence"]
    }
