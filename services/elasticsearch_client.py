import logging
from typing import Optional, List, Dict, Any
from elasticsearch import AsyncElasticsearch
from config.settings import settings

logger = logging.getLogger("scamshield.elasticsearch")

es_client: Optional[AsyncElasticsearch] = None


async def init_elasticsearch() -> AsyncElasticsearch:
    global es_client
    try:
        if settings.ES_URL and settings.ES_API_KEY:
            es_client = AsyncElasticsearch(
                [settings.ES_URL],
                api_key=settings.ES_API_KEY,
                verify_certs=True
            )
        elif settings.ES_CLOUD_ID and settings.ES_API_KEY:
            es_client = AsyncElasticsearch(
                cloud_id=settings.ES_CLOUD_ID,
                api_key=settings.ES_API_KEY
            )
        else:
            es_client = AsyncElasticsearch([settings.ES_URL])
        
        info = await es_client.info()
        logger.info(f"Elasticsearch connected: v{info['version']['number']}")
        return es_client
    except Exception as e:
        logger.error(f"Elasticsearch connection failed (Continuing without ES): {e}")
        return None


async def close_elasticsearch():
    global es_client
    if es_client:
        await es_client.close()
        es_client = None
        logger.info("Elasticsearch client closed")


async def search_scam_number(phone_number: str) -> Optional[Dict[str, Any]]:
    try:
        result = await es_client.search(
            index="scam_numbers",
            query={"term": {"phone_number": phone_number}},
            size=1
        )
        if result['hits']['total']['value'] > 0:
            return result['hits']['hits'][0]['_source']
        return None
    except Exception as e:
        logger.error(f"Error searching scam number: {e}")
        return None


async def search_malicious_url(url: str) -> bool:
    try:
        result = await es_client.search(
            index="reported_urls",
            query={"term": {"url": url}},
            size=1
        )
        return result['hits']['total']['value'] > 0
    except Exception as e:
        logger.error(f"Error searching URL: {e}")
        return False


async def search_similar_patterns(message: str, size: int = 5) -> List[Dict[str, Any]]:
    try:
        result = await es_client.search(
            index="scam_patterns",
            query={"match": {"pattern_text": {"query": message, "fuzziness": "AUTO"}}},
            size=size
        )
        patterns = []
        for hit in result['hits']['hits']:
            patterns.append({
                "pattern": hit['_source'].get('pattern_text', '')[:100],
                "score": hit['_score'],
                "category": hit['_source'].get('category', 'unknown'),
                "risk_score": hit['_source'].get('risk_score', 0)
            })
        return patterns
    except Exception as e:
        logger.error(f"Error searching patterns: {e}")
        return []


async def log_incident(incident: Dict[str, Any]) -> bool:
    try:
        await es_client.index(index="incident_logs", document=incident)
        return True
    except Exception as e:
        logger.error(f"Error logging incident: {e}")
        return False


async def update_scam_number(phone_number: str, scam_types: List[str], risk_score: float) -> bool:
    from datetime import datetime
    try:
        await es_client.update(
            index="scam_numbers",
            id=phone_number,
            body={
                "script": {
                    "source": "ctx._source.report_count++; ctx._source.last_reported = params.now; ctx._source.blocked_by_users++",
                    "params": {"now": datetime.utcnow().isoformat()}
                },
                "upsert": {
                    "phone_number": phone_number,
                    "report_count": 1,
                    "first_reported": datetime.utcnow().isoformat(),
                    "last_reported": datetime.utcnow().isoformat(),
                    "confidence_score": risk_score,
                    "scam_types": scam_types,
                    "blocked_by_users": 1
                }
            }
        )
        return True
    except Exception as e:
        logger.error(f"Error updating scam number: {e}")
        return False


async def get_user_stats_aggregation(user_id: str) -> Dict[str, Any]:
    try:
        result = await es_client.search(
            index="incident_logs",
            query={"term": {"user_id": user_id}},
            aggs={
                "scam_types": {"terms": {"field": "decision", "size": 5}},
                "avg_risk": {"avg": {"field": "risk_score"}}
            },
            size=0
        )
        return {
            "scam_types": result["aggregations"]["scam_types"]["buckets"],
            "avg_risk": result["aggregations"]["avg_risk"]["value"]
        }
    except Exception as e:
        logger.error(f"Error getting user stats: {e}")
        return {"scam_types": [], "avg_risk": 0}
