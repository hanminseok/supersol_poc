import asyncio
import json
import os
import sys
from unittest.mock import patch, MagicMock

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.rewriting_agent import RewritingAgent
from models.agent_config import get_agent_config

class TestRewritingAgentConditionalRouting:
    """RewritingAgent의 conditional_routing 기능 테스트"""
    
    def setup_method(self):
        """테스트 설정"""
        # 테스트 모드 설정
        os.environ['TEST_MODE'] = 'true'
        
        # Agent 설정 로드
        self.config = get_agent_config("rewriting_agent")
        self.agent = RewritingAgent()
    
    def test_conditional_routing_config_exists(self):
        """conditional_routing 설정이 존재하는지 확인"""
        assert self.config.get("conditional_routing") is not None
        assert "conditions" in self.config.get("conditional_routing", {})
        
        # general topic 조건이 있는지 확인
        conditions = self.config.get("conditional_routing", {}).get("conditions", [])
        general_condition = None
        for condition in conditions:
            if condition.get("condition") == "topic == 'general'":
                general_condition = condition
                break
        
        assert general_condition is not None
        assert "action" in general_condition
        assert "response_prompt" in general_condition
    
    @patch('agents.rewriting_agent.RewritingAgent._call_llm')
    async def test_general_topic_skips_next_agent(self, mock_call_llm):
        """general topic일 때 다음 agent를 건너뛰는지 확인"""
        # Mock LLM 응답 설정
        mock_response = json.dumps({
            "rewritten_text": "날씨에 대한 질문입니다",
            "topic": "general",
            "context_used": False,
            "is_general": True,
            "direct_response": "현재 날씨 정보를 확인하기 위해서는 실시간 날씨 앱이나 웹사이트를 이용하시는 것이 좋습니다."
        })
        mock_call_llm.return_value = mock_response
        
        # 테스트 입력
        input_data = {
            "query": "날씨가 어떤가요?",
            "conversation_context": [],
            "current_state": {}
        }
        
        # Agent 실행
        result = await self.agent._process(input_data)
        
        # 결과 검증
        assert result["topic"] == "general"
        assert result["is_general"] == True
        assert result["should_skip_next_agent"] == True
        assert "direct_response" in result
        assert len(result["direct_response"]) > 0
    
    @patch('agents.rewriting_agent.RewritingAgent._call_llm')
    async def test_banking_topic_continues_to_next_agent(self, mock_call_llm):
        """banking topic일 때 다음 agent로 진행하는지 확인"""
        # Mock LLM 응답 설정
        mock_response = json.dumps({
            "rewritten_text": "123-456-789 계좌의 잔액을 확인하고 싶습니다",
            "topic": "account",
            "context_used": True,
            "is_general": False,
            "direct_response": ""
        })
        mock_call_llm.return_value = mock_response
        
        # 테스트 입력
        input_data = {
            "query": "계좌 잔액 확인",
            "conversation_context": [],
            "current_state": {}
        }
        
        # Agent 실행
        result = await self.agent._process(input_data)
        
        # 결과 검증
        assert result["topic"] == "account"
        assert result["is_general"] == False
        assert result.get("should_skip_next_agent", False) == False
    
    async def test_handle_conditional_routing_general(self):
        """_handle_conditional_routing 메서드 테스트 - general topic"""
        # 테스트 입력
        result = {
            "rewritten_text": "날씨에 대한 질문입니다",
            "topic": "general",
            "context_used": False,
            "is_general": True
        }
        
        # 메서드 실행
        processed_result = await self.agent._handle_conditional_routing(result, "날씨가 어떤가요?")
        
        # 결과 검증
        assert processed_result["should_skip_next_agent"] == True
        assert "direct_response" in processed_result
        assert len(processed_result["direct_response"]) > 0
    
    async def test_handle_conditional_routing_banking(self):
        """_handle_conditional_routing 메서드 테스트 - banking topic"""
        # 테스트 입력
        result = {
            "rewritten_text": "계좌 잔액 확인",
            "topic": "account",
            "context_used": True,
            "is_general": False
        }
        
        # 메서드 실행
        processed_result = await self.agent._handle_conditional_routing(result, "계좌 잔액 확인")
        
        # 결과 검증
        assert processed_result.get("should_skip_next_agent", False) == False
        assert "direct_response" not in processed_result or processed_result["direct_response"] == ""

async def main():
    """테스트 실행"""
    print("=== RewritingAgent Conditional Routing 테스트 시작 ===")
    
    test_instance = TestRewritingAgentConditionalRouting()
    test_instance.setup_method()
    
    # 설정 테스트
    print("1. conditional_routing 설정 확인...")
    test_instance.test_conditional_routing_config_exists()
    print("✓ 설정 확인 완료")
    
    # 메서드 테스트
    print("2. _handle_conditional_routing 메서드 테스트...")
    await test_instance.test_handle_conditional_routing_general()
    await test_instance.test_handle_conditional_routing_banking()
    print("✓ 메서드 테스트 완료")
    
    # 통합 테스트
    print("3. 통합 테스트...")
    await test_instance.test_general_topic_skips_next_agent()
    await test_instance.test_banking_topic_continues_to_next_agent()
    print("✓ 통합 테스트 완료")
    
    print("=== 모든 테스트 통과! ===")

if __name__ == "__main__":
    asyncio.run(main()) 