import pytest
from unittest.mock import patch, AsyncMock
import sys
sys.path.insert(0, '..')


class TestAuthEndpoints:
    def test_password_hashing(self):
        from api.routes import hash_password, verify_password
        password = "secure123"
        hashed = hash_password(password)
        assert hashed != password
        assert verify_password(password, hashed)
        assert not verify_password("wrong", hashed)
    
    def test_jwt_token_creation(self):
        from api.routes import create_access_token
        from jose import jwt
        from config.settings import settings
        data = {"sub": "user-123", "email": "test@example.com"}
        token = create_access_token(data)
        assert isinstance(token, str)
        assert len(token) > 50
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        assert payload['sub'] == "user-123"


class TestInputValidation:
    def test_message_analyze_request_validation(self):
        from models.message import MessageAnalyzeRequest
        from pydantic import ValidationError
        request = MessageAnalyzeRequest(message="Test message", sender="+1-555-1234")
        assert request.message == "Test message"
        with pytest.raises(ValidationError):
            MessageAnalyzeRequest(message="", sender="+1-555-1234")
    
    def test_user_create_validation(self):
        from models.user import UserCreate
        from pydantic import ValidationError
        user = UserCreate(email="test@example.com", password="secure123")
        assert user.email == "test@example.com"
        with pytest.raises(ValidationError):
            UserCreate(email="test@example.com", password="short")


class TestResponseModels:
    def test_analysis_response(self):
        from models.scam import AnalysisResponse
        response = AnalysisResponse(risk_score=75, decision="BLOCK", analysis={"test": "data"}, actions_taken=["blocked"], processing_time_ms=100)
        assert response.risk_score == 75
        assert response.decision == "BLOCK"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
