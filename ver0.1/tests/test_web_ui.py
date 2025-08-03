"""
웹 UI 테스트 코드
"""

import pytest
import requests
import json
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from src.web_ui.web_server import create_web_server, ChatMessage, ChatResponse


class TestWebUI:
    """웹 UI 테스트 클래스"""
    
    @pytest.fixture
    def client(self):
        """테스트 클라이언트 생성"""
        app = create_web_server().app
        return TestClient(app)
    
    def test_health_check(self, client):
        """헬스 체크 엔드포인트 테스트"""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "SuperSOL Chat"
    
    def test_status_check(self, client):
        """상태 확인 엔드포인트 테스트"""
        response = client.get("/api/status")
        assert response.status_code == 200
        data = response.json()
        assert "active_connections" in data
        assert "service_status" in data
        assert data["service_status"] == "running"
    
    def test_main_page(self, client):
        """메인 페이지 접근 테스트"""
        response = client.get("/")
        assert response.status_code == 200
        assert "SuperSOL" in response.text
        assert "채팅" in response.text
    
    def test_chat_message_validation(self):
        """채팅 메시지 유효성 검증 테스트"""
        # 정상적인 메시지
        valid_message = ChatMessage(message="안녕하세요", session_id="test_session")
        assert valid_message.message == "안녕하세요"
        assert valid_message.session_id == "test_session"
        
        # 빈 메시지
        with pytest.raises(ValueError, match="메시지는 비어있을 수 없습니다"):
            ChatMessage(message="", session_id="test_session")
        
        # 너무 긴 메시지
        long_message = "a" * 1001
        with pytest.raises(ValueError, match="메시지는 1000자를 초과할 수 없습니다"):
            ChatMessage(message=long_message, session_id="test_session")
        
        # XSS 시도
        with pytest.raises(ValueError, match="잘못된 메시지 형식입니다"):
            ChatMessage(message="<script>alert('xss')</script>", session_id="test_session")
    
    def test_session_id_validation(self):
        """세션 ID 유효성 검증 테스트"""
        # 정상적인 세션 ID
        valid_session = ChatMessage(message="안녕하세요", session_id="test_session_123")
        assert valid_session.session_id == "test_session_123"
        
        # 빈 세션 ID (기본값으로 설정)
        empty_session = ChatMessage(message="안녕하세요", session_id="")
        assert empty_session.session_id == "default"
        
        # 잘못된 세션 ID
        with pytest.raises(ValueError, match="세션 ID는 영문자, 숫자, 언더스코어, 하이픈만 사용 가능합니다"):
            ChatMessage(message="안녕하세요", session_id="test@session")
    
    @patch('src.web_ui.web_server.ChatService')
    def test_chat_endpoint_success(self, mock_chat_service, client):
        """채팅 엔드포인트 성공 테스트"""
        # Mock 설정
        mock_service = MagicMock()
        mock_service.process_message.return_value = {
            "response": "테스트 응답입니다.",
            "session_id": "test_session"
        }
        mock_chat_service.return_value = mock_service
        
        # 요청 데이터
        chat_data = {
            "message": "안녕하세요",
            "session_id": "test_session"
        }
        
        response = client.post("/api/chat", json=chat_data)
        assert response.status_code == 200
        data = response.json()
        assert data["response"] == "테스트 응답입니다."
        assert data["session_id"] == "test_session"
        assert data["status"] == "success"
    
    @patch('src.web_ui.web_server.ChatService')
    def test_chat_endpoint_error(self, mock_chat_service, client):
        """채팅 엔드포인트 오류 테스트"""
        # Mock 설정 - 예외 발생
        mock_service = MagicMock()
        mock_service.process_message.side_effect = Exception("테스트 오류")
        mock_chat_service.return_value = mock_service
        
        # 요청 데이터
        chat_data = {
            "message": "안녕하세요",
            "session_id": "test_session"
        }
        
        response = client.post("/api/chat", json=chat_data)
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data


class TestChatResponse:
    """채팅 응답 모델 테스트"""
    
    def test_chat_response_creation(self):
        """채팅 응답 생성 테스트"""
        response = ChatResponse(
            response="테스트 응답",
            session_id="test_session"
        )
        assert response.response == "테스트 응답"
        assert response.session_id == "test_session"
        assert response.status == "success"
        assert response.error is None
    
    def test_chat_response_with_error(self):
        """오류가 있는 채팅 응답 테스트"""
        response = ChatResponse(
            response="오류 발생",
            session_id="test_session",
            status="error",
            error="테스트 오류"
        )
        assert response.status == "error"
        assert response.error == "테스트 오류"


if __name__ == "__main__":
    pytest.main([__file__]) 