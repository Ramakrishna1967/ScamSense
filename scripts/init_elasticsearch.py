import asyncio
from datetime import datetime
from elasticsearch import AsyncElasticsearch
from dotenv import load_dotenv
import os

load_dotenv()

ES_URL = os.getenv("ES_URL", "http://localhost:9200")
ES_API_KEY = os.getenv("ES_API_KEY")

INDICES = {
    "scam_numbers": {
        "mappings": {
            "properties": {
                "phone_number": {"type": "keyword"},
                "country_code": {"type": "keyword"},
                "report_count": {"type": "integer"},
                "first_reported": {"type": "date"},
                "last_reported": {"type": "date"},
                "confidence_score": {"type": "float"},
                "scam_types": {"type": "keyword"},
                "blocked_by_users": {"type": "integer"}
            }
        }
    },
    "scam_patterns": {
        "mappings": {
            "properties": {
                "pattern_text": {"type": "text", "analyzer": "english"},
                "keywords": {"type": "keyword"},
                "risk_score": {"type": "float"},
                "category": {"type": "keyword"},
                "detection_count": {"type": "integer"},
                "last_seen": {"type": "date"}
            }
        }
    },
    "incident_logs": {
        "mappings": {
            "properties": {
                "timestamp": {"type": "date"},
                "user_id": {"type": "keyword"},
                "sender": {"type": "keyword"},
                "message_hash": {"type": "keyword"},
                "risk_score": {"type": "integer"},
                "decision": {"type": "keyword"},
                "agents_involved": {"type": "keyword"},
                "actions_taken": {"type": "keyword"},
                "processing_time_ms": {"type": "integer"}
            }
        }
    },
    "reported_urls": {
        "mappings": {
            "properties": {
                "url": {"type": "keyword"},
                "domain": {"type": "keyword"},
                "is_malicious": {"type": "boolean"},
                "report_count": {"type": "integer"},
                "first_seen": {"type": "date"},
                "last_active": {"type": "date"},
                "phishing_score": {"type": "float"},
                "categories": {"type": "keyword"}
            }
        }
    }
}

SEED_DATA = {
    "scam_patterns": [
        {"pattern_text": "URGENT: Your account has been suspended. Click here to verify.", "keywords": ["urgent", "suspended", "verify"], "risk_score": 95.0, "category": "bank_fraud"},
        {"pattern_text": "You've won $1,000,000! Claim your prize now!", "keywords": ["won", "prize", "claim"], "risk_score": 98.0, "category": "lottery_scam"},
        {"pattern_text": "IRS notice: You owe back taxes. Pay immediately or face arrest.", "keywords": ["irs", "taxes", "arrest"], "risk_score": 99.0, "category": "irs_impersonation"}
    ],
    "scam_numbers": [
        {"phone_number": "+1-800-SCAMMER", "report_count": 100, "confidence_score": 99.0, "scam_types": ["irs_impersonation"]},
        {"phone_number": "+1-888-FRAUD01", "report_count": 50, "confidence_score": 95.0, "scam_types": ["tech_support"]}
    ]
}


async def init_elasticsearch():
    print("Connecting to Elasticsearch...")
    print(f"URL: {ES_URL}")
    
    if ES_API_KEY:
        es = AsyncElasticsearch(
            [ES_URL],
            api_key=ES_API_KEY,
            verify_certs=True
        )
    else:
        es = AsyncElasticsearch([ES_URL])
    
    try:
        info = await es.info()
        print(f"Connected to Elasticsearch v{info['version']['number']}")
        
        for index_name, index_config in INDICES.items():
            if not await es.indices.exists(index=index_name):
                await es.indices.create(index=index_name, body=index_config)
                print(f"Created index: {index_name}")
            else:
                print(f"Index exists: {index_name}")
        
        for pattern in SEED_DATA["scam_patterns"]:
            await es.index(index="scam_patterns", document={**pattern, "detection_count": 0, "last_seen": datetime.utcnow().isoformat()})
        
        for number in SEED_DATA["scam_numbers"]:
            await es.index(index="scam_numbers", id=number["phone_number"], document={**number, "first_reported": datetime.utcnow().isoformat(), "last_reported": datetime.utcnow().isoformat()})
        
        print("Seed data added")
        print("Elasticsearch initialized successfully")
    except Exception as e:
        print(f"Error: {e}")
        raise
    finally:
        await es.close()


if __name__ == "__main__":
    asyncio.run(init_elasticsearch())
