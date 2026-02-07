import re
import logging
from datetime import datetime
from typing import List
from models.scam import AgentState

logger = logging.getLogger("scamshield.agents.watcher")


def extract_urls(text: str) -> List[str]:
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    short_patterns = [
        r'\bbit\.ly/[a-zA-Z0-9]+',
        r'\bgoo\.gl/[a-zA-Z0-9]+',
        r'\bt\.co/[a-zA-Z0-9]+',
        r'\btinyurl\.com/[a-zA-Z0-9]+',
    ]
    
    urls = re.findall(url_pattern, text)
    for pattern in short_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        urls.extend(['https://' + m for m in matches])
    
    seen = set()
    unique_urls = []
    for url in urls:
        if url.lower() not in seen:
            seen.add(url.lower())
            unique_urls.append(url)
    return unique_urls


def extract_phone_numbers(text: str) -> List[str]:
    patterns = [
        r'\+?1?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}',
        r'\b\d{10}\b',
    ]
    phones = []
    for pattern in patterns:
        phones.extend(re.findall(pattern, text))
    return list(set(phones))


def clean_content(text: str, urls: List[str]) -> str:
    content = text
    for url in urls:
        content = content.replace(url, '[URL]')
    content = ' '.join(content.split())
    return content.strip()


async def watcher_agent(state: AgentState) -> AgentState:
    logger.info(f"Watcher Agent: Processing message from {state['sender']}")
    
    message = state.get('message', '')
    urls = extract_urls(message)
    content_cleaned = clean_content(message, urls)
    
    return {
        **state,
        "urls": urls,
        "content_cleaned": content_cleaned,
        "processing_start": datetime.utcnow()
    }
