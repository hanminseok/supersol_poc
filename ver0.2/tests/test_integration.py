import asyncio
import json
import pytest
import pytest_asyncio
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

from services.chat_service import ChatService
from services.session_manager import SessionManager
from services.response_generator import ResponseGenerator
from services.session_optimizer import SessionOptimizer
from services.agent_manager import AgentManager
from utils.logger import service_logger

class TestChatServiceIntegration:
    """채팅 서비스 통합 테스트"""
    
    @pytest_asyncio.fixture
    async def chat_service(self):
        """채팅 서비스 인스턴스 생성"""
        return ChatService()
    
    @pytest_asyncio.fixture
    async def session_manager(self):
        """세션 매니저 인스턴스 생성"""
        return SessionManager()
    
    @pytest_asyncio.fixture
    async def session_optimizer(self):
        """세션 최적화 인스턴스 생성"""
        return SessionOptimizer()
    
    @pytest.mark.asyncio
    async def test_chat_service_initialization(self, chat_service):
        """채팅 서비스 초기화 테스트"""
        assert chat_service is not None
        assert hasattr(chat_service, 'session_manager')
        assert hasattr(chat_service, 'agent_manager')
        assert hasattr(chat_service, 'logger')
    
    @pytest.mark.asyncio
    async def test_session_creation_and_management(self, session_manager):
        """세션 생성 및 관리 테스트"""
        session_id = "test_session_001"
        customer_info = {"name": "테스트 고객", "id": "CUST001"}
        
        # 세션 생성
        result = await session_manager.create_session(session_id, customer_info)
        assert result is True
        
        # 세션 로드
        session_data = await session_manager.load_session(session_id)
        assert session_data is not None
        assert session_data["session_id"] == session_id
        assert session_data["customer_info"]["name"] == "테스트 고객"
        
        # 세션 정리
        await session_manager.delete_session(session_id)
    
    @pytest.mark.asyncio
    async def test_response_generator(self):
        """응답 생성기 테스트"""
        # 계좌 잔액 응답 테스트
        tool_output = {"balance": "1,000,000원", "account_number": "123-456-789"}
        customer_info = {"name": "김철수"}
        
        response = ResponseGenerator.generate_response(
            "account_balance", 
            tool_output, 
            customer_info
        )
        
        assert "김철수님" in response
        assert "1,000,000원" in response
        assert "123-456-789" in response
    
    @pytest.mark.asyncio
    async def test_session_optimizer(self, session_optimizer):
        """세션 최적화 테스트"""
        # 대용량 세션 목록 조회
        large_sessions = await session_optimizer.get_large_sessions()
        assert isinstance(large_sessions, list)
        
        # 모든 세션 최적화
        results = await session_optimizer.optimize_all_sessions()
        assert isinstance(results, dict)
        assert "total_sessions" in results
        assert "optimized_sessions" in results
        assert "large_sessions" in results
        assert "errors" in results
    
    @pytest.mark.asyncio
    async def test_chat_workflow_with_mock_agents(self, chat_service):
        """모의 Agent를 사용한 채팅 워크플로우 테스트"""
        session_id = "test_workflow_session"
        user_query = "잔액 조회해줘"
        
        # Agent Manager 모의 설정
        mock_agent_manager = Mock()
        mock_agent_manager.execute_workflow = AsyncMock(return_value={
            "tool_name": "account_balance",
            "tool_output": {"balance": "500,000원", "account_number": "123-456-789"},
            "context": {"current_state": {"selected_account": "123-456-789"}}
        })
        
        chat_service.agent_manager = mock_agent_manager
        
        # 채팅 처리 테스트
        responses = []
        async for response in chat_service.process_chat(session_id, user_query):
            responses.append(response)
        
        assert len(responses) > 0
        assert any("500,000원" in resp for resp in responses)
    
    @pytest.mark.asyncio
    async def test_error_handling(self, chat_service):
        """에러 처리 테스트"""
        session_id = "test_error_session"
        user_query = "잔액 조회해줘"
        
        # Agent Manager 에러 시뮬레이션
        mock_agent_manager = Mock()
        mock_agent_manager.execute_workflow = AsyncMock(side_effect=Exception("Agent error"))
        
        chat_service.agent_manager = mock_agent_manager
        
        # 에러 상황에서도 응답 생성 확인
        responses = []
        async for response in chat_service.process_chat(session_id, user_query):
            responses.append(response)
        
        assert len(responses) > 0
        # 에러 상황에서도 기본 응답이 생성되어야 함
    
    @pytest.mark.asyncio
    async def test_conversation_history_management(self, session_manager):
        """대화 내역 관리 테스트"""
        session_id = "test_history_session"
        
        # 세션 생성
        await session_manager.create_session(session_id)
        
        # 대화 내역 추가
        for i in range(5):
            await session_manager.save_conversation(
                session_id,
                f"사용자 질문 {i}",
                f"에이전트 응답 {i}",
                f"에이전트 로그 {i}",
                {"current_state": {"test": i}}
            )
        
        # 대화 내역 조회
        history = await session_manager.get_conversation_history(session_id, limit=3)
        assert len(history) <= 3
        assert len(history) > 0
        
        # 세션 정리
        await session_manager.delete_session(session_id)
    
    @pytest.mark.asyncio
    async def test_context_management(self, session_manager):
        """컨텍스트 관리 테스트"""
        session_id = "test_context_session"
        
        # 세션 생성
        await session_manager.create_session(session_id)
        
        # 컨텍스트 업데이트
        context_updates = {
            "selected_account": "123-456-789",
            "pending_action": "transfer",
            "missing_slots": ["amount", "recipient"]
        }
        
        result = await session_manager.update_context(session_id, context_updates)
        assert result is True
        
        # 컨텍스트 조회
        current_context = await session_manager.get_current_context(session_id)
        assert current_context is not None
        assert current_context.get("selected_account") == "123-456-789"
        
        # 컨텍스트 정리
        result = await session_manager.clear_context(session_id)
        assert result is True
        
        # 세션 정리
        await session_manager.delete_session(session_id)
    
    @pytest.mark.asyncio
    async def test_large_session_handling(self, session_optimizer):
        """대용량 세션 처리 테스트"""
        # 테스트용 대용량 세션 데이터 생성
        large_session_data = {
            "session_id": "test_large_session",
            "conversation_history": [
                {
                    "timestamp": "2025-08-04T00:00:00",
                    "user_query": "테스트 질문",
                    "agent_response": "테스트 응답",
                    "agent_log": "A" * 10000  # 큰 로그 데이터
                }
            ] * 1000  # 1000개의 대화 내역
        }
        
        # 실제 파일 생성은 테스트에서 제외하고 로직만 테스트
        # 실제 구현에서는 파일 I/O가 포함됨
        
        # 최적화 결과 구조 확인
        results = await session_optimizer.optimize_all_sessions()
        assert isinstance(results, dict)
        assert all(key in results for key in ["total_sessions", "optimized_sessions", "large_sessions", "errors"])

class TestPerformanceOptimization:
    """성능 최적화 테스트"""
    
    @pytest.mark.asyncio
    async def test_session_file_size_monitoring(self):
        """세션 파일 크기 모니터링 테스트"""
        optimizer = SessionOptimizer()
        
        # 대용량 세션 목록 조회 성능 테스트
        start_time = asyncio.get_event_loop().time()
        large_sessions = await optimizer.get_large_sessions()
        end_time = asyncio.get_event_loop().time()
        
        # 1초 이내에 완료되어야 함
        assert (end_time - start_time) < 1.0
        assert isinstance(large_sessions, list)
    
    @pytest.mark.asyncio
    async def test_response_generation_performance(self):
        """응답 생성 성능 테스트"""
        # 다양한 도구 출력에 대한 응답 생성 성능 테스트
        test_cases = [
            ("account_balance", {"balance": "1,000,000원", "account_number": "123-456-789"}),
            ("transfer_money", {"status": "success", "amount": "100,000원", "recipient": "김철수"}),
            ("loan_info", {"available_loan_amount": "50,000,000원", "interest_rate": "3.5%"}),
        ]
        
        customer_info = {"name": "테스트 고객"}
        
        for tool_name, tool_output in test_cases:
            start_time = asyncio.get_event_loop().time()
            response = ResponseGenerator.generate_response(tool_name, tool_output, customer_info)
            end_time = asyncio.get_event_loop().time()
            
            # 응답 생성이 0.1초 이내에 완료되어야 함
            assert (end_time - start_time) < 0.1
            assert isinstance(response, str)
            assert len(response) > 0

if __name__ == "__main__":
    # 테스트 실행
    pytest.main([__file__, "-v"]) 