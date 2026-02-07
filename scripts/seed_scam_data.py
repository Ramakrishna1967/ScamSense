import asyncio
from datetime import datetime
from elasticsearch import AsyncElasticsearch
from dotenv import load_dotenv
import os

load_dotenv()

ES_CLOUD_ID = os.getenv("ES_CLOUD_ID")
ES_API_KEY = os.getenv("ES_API_KEY")
ES_URL = os.getenv("ES_URL", "http://localhost:9200")

SCAM_PATTERNS = [
    {"pattern_text": "Your Chase account has been locked due to suspicious activity.", "keywords": ["chase", "locked", "suspicious"], "risk_score": 95.0, "category": "bank_fraud"},
    {"pattern_text": "Wells Fargo Alert: Unusual sign-in detected.", "keywords": ["wells fargo", "unusual", "sign-in"], "risk_score": 92.0, "category": "bank_fraud"},
    {"pattern_text": "Your PayPal account will be suspended in 24 hours.", "keywords": ["paypal", "suspended", "24 hours"], "risk_score": 94.0, "category": "bank_fraud"},
    {"pattern_text": "FINAL WARNING: You owe the IRS $3,500.", "keywords": ["irs", "arrest warrant", "final warning"], "risk_score": 98.0, "category": "irs_impersonation"},
    {"pattern_text": "Social Security Administration: Your SSN has been suspended.", "keywords": ["social security", "ssn", "suspended"], "risk_score": 97.0, "category": "government_impersonation"},
    {"pattern_text": "Congratulations! You've been selected to receive a $5,000 gift card.", "keywords": ["congratulations", "selected", "gift card"], "risk_score": 96.0, "category": "lottery_scam"},
    {"pattern_text": "Amazon Shopper: You're today's lucky winner!", "keywords": ["amazon", "lucky winner", "claim"], "risk_score": 95.0, "category": "lottery_scam"},
    {"pattern_text": "VIRUS DETECTED on your device! Call Microsoft Support immediately.", "keywords": ["virus", "microsoft", "call"], "risk_score": 93.0, "category": "tech_support_scam"},
    {"pattern_text": "USPS: Your package could not be delivered.", "keywords": ["usps", "package", "delivered"], "risk_score": 89.0, "category": "delivery_scam"},
    {"pattern_text": "Double your Bitcoin! Send 0.1 BTC and receive 0.2 BTC back.", "keywords": ["double", "bitcoin", "send"], "risk_score": 99.0, "category": "crypto_scam"}
]

SCAM_NUMBERS = [
    {"_id": "+1-800-SCAM-001", "phone_number": "+1-800-SCAM-001", "report_count": 245, "confidence_score": 99.0, "scam_types": ["irs_impersonation"]},
    {"_id": "+1-888-FAKE-IRS", "phone_number": "+1-888-FAKE-IRS", "report_count": 178, "confidence_score": 98.5, "scam_types": ["irs_impersonation"]},
    {"_id": "+1-900-LOTTERY", "phone_number": "+1-900-LOTTERY", "report_count": 312, "confidence_score": 99.5, "scam_types": ["lottery_scam"]}
]

MALICIOUS_URLS = [
    {"_id": "secure-bank-verify.com", "url": "secure-bank-verify.com", "domain": "secure-bank-verify.com", "is_malicious": True, "report_count": 567, "phishing_score": 99.0, "categories": ["phishing"]},
    {"_id": "amazo-n-deals.net", "url": "amazo-n-deals.net", "domain": "amazo-n-deals.net", "is_malicious": True, "report_count": 234, "phishing_score": 97.5, "categories": ["phishing"]},
    {"_id": "free-iphone-winner.com", "url": "free-iphone-winner.com", "domain": "free-iphone-winner.com", "is_malicious": True, "report_count": 891, "phishing_score": 98.0, "categories": ["lottery_scam"]}
]


async def main():
    print("Seeding scam data...")
    
    if ES_CLOUD_ID and ES_API_KEY:
        es = AsyncElasticsearch(cloud_id=ES_CLOUD_ID, api_key=ES_API_KEY)
    else:
        es = AsyncElasticsearch([ES_URL])
    
    try:
        for pattern in SCAM_PATTERNS:
            await es.index(index="scam_patterns", document={**pattern, "detection_count": 0, "last_seen": datetime.utcnow().isoformat()})
        print(f"Seeded {len(SCAM_PATTERNS)} patterns")
        
        for number in SCAM_NUMBERS:
            doc_id = number.pop("_id")
            await es.index(index="scam_numbers", id=doc_id, document={**number, "first_reported": datetime.utcnow().isoformat(), "last_reported": datetime.utcnow().isoformat()})
        print(f"Seeded {len(SCAM_NUMBERS)} numbers")
        
        for url_data in MALICIOUS_URLS:
            doc_id = url_data.pop("_id")
            await es.index(index="reported_urls", id=doc_id, document={**url_data, "first_seen": datetime.utcnow().isoformat(), "last_active": datetime.utcnow().isoformat()})
        print(f"Seeded {len(MALICIOUS_URLS)} URLs")
        
        print("Seeding complete")
    finally:
        await es.close()


if __name__ == "__main__":
    asyncio.run(main())
