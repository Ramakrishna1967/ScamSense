import pytest
from unittest.mock import AsyncMock, patch
import sys
sys.path.insert(0, '..')


class TestElasticsearchClient:
    @pytest.mark.asyncio
    async def test_search_scam_number_found(self):
        mock_result = {'hits': {'total': {'value': 1}, 'hits': [{'_source': {'phone_number': '+1-555-SCAM', 'report_count': 50}}]}}
        with patch('services.elasticsearch_client.es_client') as mock_es:
            mock_es.search = AsyncMock(return_value=mock_result)
            from services.elasticsearch_client import search_scam_number
            result = await search_scam_number('+1-555-SCAM')
            assert result is not None
            assert result['phone_number'] == '+1-555-SCAM'


class TestElasticsearchIndexMappings:
    def test_scam_numbers_mapping(self):
        from scripts.init_elasticsearch import INDICES
        mapping = INDICES['scam_numbers']['mappings']['properties']
        assert 'phone_number' in mapping
        assert mapping['phone_number']['type'] == 'keyword'
    
    def test_scam_patterns_mapping(self):
        from scripts.init_elasticsearch import INDICES
        mapping = INDICES['scam_patterns']['mappings']['properties']
        assert 'pattern_text' in mapping
        assert mapping['pattern_text']['type'] == 'text'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
