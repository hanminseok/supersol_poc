#!/usr/bin/env python3
"""
RewritingAgent 테스트 스크립트
- Singleturn 상황 테스트
- Multiturn 상황 테스트
- 실제 LLM 호출 포함
"""

import asyncio
import json
import os
import sys
from typing import Dict, Any, List

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agents.rewriting_agent import RewritingAgent
from models.agent_config import get_agent_config

class RewritingAgentTester:
    """RewritingAgent 테스트 클래스"""
    
    def __init__(self):
        self.agent = None
        self.test_results = []
    
    async def setup(self):
        """테스트 환경 설정"""
        print("=== RewritingAgent 테스트 환경 설정 ===")
        
        # Agent 초기화
        try:
            self.agent = RewritingAgent()
            print(f"✓ RewritingAgent 초기화 성공")
            print(f"  - 모델: {self.agent.config.model}")
            print(f"  - 제공자: {self.agent.config.model_provider}")
            print(f"  - 온도: {self.agent.config.temperature}")
        except Exception as e:
            print(f"✗ RewritingAgent 초기화 실패: {str(e)}")
            raise
    
    async def test_singleturn_scenarios(self):
        """Singleturn 상황 테스트"""
        print("\n=== Singleturn 상황 테스트 ===")
        
        test_cases = [
            {
                "name": "기본 계좌 잔액 조회",
                "input": {
                    "query": "123-456-789 계좌 잔액 알려줘",
                    "conversation_context": [],
                    "current_state": {}
                },
                "expected_topic": "account"
            },
            {
                "name": "송금 요청",
                "input": {
                    "query": "김철수에게 10만원 송금해줘",
                    "conversation_context": [],
                    "current_state": {}
                },
                "expected_topic": "banking"
            },
            {
                "name": "대출 정보 조회",
                "input": {
                    "query": "대출 한도가 얼마나 되나요?",
                    "conversation_context": [],
                    "current_state": {}
                },
                "expected_topic": "loan"
            },
            {
                "name": "투자 상품 문의",
                "input": {
                    "query": "펀드 상품 추천해주세요",
                    "conversation_context": [],
                    "current_state": {}
                },
                "expected_topic": "investment"
            },
            {
                "name": "일반 문의",
                "input": {
                    "query": "은행 영업시간이 어떻게 되나요?",
                    "conversation_context": [],
                    "current_state": {}
                },
                "expected_topic": "general"
            }
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n--- 테스트 {i}: {test_case['name']} ---")
            await self._run_single_test(test_case)
    
    async def test_multiturn_scenarios(self):
        """Multiturn 상황 테스트"""
        print("\n=== Multiturn 상황 테스트 ===")
        
        # 시나리오 1: 계좌 관련 대화
        print("\n--- 시나리오 1: 계좌 관련 대화 ---")
        await self._test_account_conversation()
        
        # 시나리오 2: 대출 관련 대화
        print("\n--- 시나리오 2: 대출 관련 대화 ---")
        await self._test_loan_conversation()
        
        # 시나리오 3: 참조 해결 테스트
        print("\n--- 시나리오 3: 참조 해결 테스트 ---")
        await self._test_reference_resolution()
    
    async def _test_account_conversation(self):
        """계좌 관련 대화 테스트"""
        conversation_context = []
        current_state = {}
        
        # 첫 번째 질문
        print("1단계: 계좌 잔액 조회")
        input_data = {
            "query": "123-456-789 계좌 잔액 알려줘",
            "conversation_context": conversation_context,
            "current_state": current_state
        }
        
        result1 = await self.agent.execute(input_data)
        print(f"  입력: {input_data['query']}")
        print(f"  출력: {result1}")
        
        # 대화 컨텍스트 업데이트
        conversation_context.append({
            "user_query": input_data["query"],
            "extracted_info": {
                "intent": "balance_inquiry",
                "tool_name": "get_balance",
                "accounts_mentioned": ["123-456-789"]
            }
        })
        current_state["selected_account"] = "123-456-789"
        current_state["last_intent"] = "balance_inquiry"
        
        # 두 번째 질문 (참조 사용)
        print("\n2단계: 참조를 사용한 질문")
        input_data2 = {
            "query": "그 계좌에서 5만원 출금해줘",
            "conversation_context": conversation_context,
            "current_state": current_state
        }
        
        result2 = await self.agent.execute(input_data2)
        print(f"  입력: {input_data2['query']}")
        print(f"  출력: {result2}")
        
        # 세 번째 질문 (추가 정보 요청)
        print("\n3단계: 추가 정보 요청")
        conversation_context.append({
            "user_query": input_data2["query"],
            "extracted_info": {
                "intent": "withdrawal",
                "tool_name": "withdraw_money",
                "accounts_mentioned": ["123-456-789"]
            }
        })
        
        input_data3 = {
            "query": "거래 내역도 보여줘",
            "conversation_context": conversation_context,
            "current_state": current_state
        }
        
        result3 = await self.agent.execute(input_data3)
        print(f"  입력: {input_data3['query']}")
        print(f"  출력: {result3}")
    
    async def _test_loan_conversation(self):
        """대출 관련 대화 테스트"""
        conversation_context = []
        current_state = {}
        
        # 첫 번째 질문
        print("1단계: 대출 한도 조회")
        input_data = {
            "query": "대출 한도가 얼마나 되나요?",
            "conversation_context": conversation_context,
            "current_state": current_state
        }
        
        result1 = await self.agent.execute(input_data)
        print(f"  입력: {input_data['query']}")
        print(f"  출력: {result1}")
        
        # 대화 컨텍스트 업데이트
        conversation_context.append({
            "user_query": input_data["query"],
            "extracted_info": {
                "intent": "loan_limit_inquiry",
                "tool_name": "get_loan_limit",
                "accounts_mentioned": []
            }
        })
        current_state["last_intent"] = "loan_limit_inquiry"
        
        # 두 번째 질문
        print("\n2단계: 대출 신청")
        input_data2 = {
            "query": "대출 신청하고 싶어요",
            "conversation_context": conversation_context,
            "current_state": current_state
        }
        
        result2 = await self.agent.execute(input_data2)
        print(f"  입력: {input_data2['query']}")
        print(f"  출력: {result2}")
        
        # 세 번째 질문
        print("\n3단계: 대출 조건 문의")
        conversation_context.append({
            "user_query": input_data2["query"],
            "extracted_info": {
                "intent": "loan_application",
                "tool_name": "apply_loan",
                "accounts_mentioned": []
            }
        })
        
        input_data3 = {
            "query": "이자율은 어떻게 되나요?",
            "conversation_context": conversation_context,
            "current_state": current_state
        }
        
        result3 = await self.agent.execute(input_data3)
        print(f"  입력: {input_data3['query']}")
        print(f"  출력: {result3}")
    
    async def _test_reference_resolution(self):
        """참조 해결 테스트"""
        conversation_context = []
        current_state = {}
        
        # 첫 번째 질문
        print("1단계: 계좌 선택")
        input_data = {
            "query": "123-456-789 계좌 선택해줘",
            "conversation_context": conversation_context,
            "current_state": current_state
        }
        
        result1 = await self.agent.execute(input_data)
        print(f"  입력: {input_data['query']}")
        print(f"  출력: {result1}")
        
        # 대화 컨텍스트 업데이트
        conversation_context.append({
            "user_query": input_data["query"],
            "extracted_info": {
                "intent": "account_selection",
                "tool_name": "select_account",
                "accounts_mentioned": ["123-456-789"]
            }
        })
        current_state["selected_account"] = "123-456-789"
        
        # 두 번째 질문 (참조 해결 테스트)
        print("\n2단계: 참조 해결 테스트 - '그 계좌'")
        input_data2 = {
            "query": "그 계좌 잔액은?",
            "conversation_context": conversation_context,
            "current_state": current_state
        }
        
        result2 = await self.agent.execute(input_data2)
        print(f"  입력: {input_data2['query']}")
        print(f"  출력: {result2}")
        
        # 세 번째 질문 (추가 참조 해결 테스트)
        print("\n3단계: 참조 해결 테스트 - '이 계좌'")
        input_data3 = {
            "query": "이 계좌에서 송금은?",
            "conversation_context": conversation_context,
            "current_state": current_state
        }
        
        result3 = await self.agent.execute(input_data3)
        print(f"  입력: {input_data3['query']}")
        print(f"  출력: {result3}")
    
    async def _run_single_test(self, test_case: Dict[str, Any]):
        """단일 테스트 실행"""
        try:
            result = await self.agent.execute(test_case["input"])
            
            # 결과 검증
            success = True
            issues = []
            
            # 필수 필드 확인
            if "rewritten_text" not in result:
                success = False
                issues.append("rewritten_text 필드 누락")
            
            if "topic" not in result:
                success = False
                issues.append("topic 필드 누락")
            
            if "context_used" not in result:
                success = False
                issues.append("context_used 필드 누락")
            
            # 주제 검증
            expected_topic = test_case.get("expected_topic")
            if expected_topic and result.get("topic") != expected_topic:
                success = False
                issues.append(f"주제 불일치: 예상={expected_topic}, 실제={result.get('topic')}")
            
            # 결과 출력
            if success:
                print(f"  ✓ 성공")
                print(f"    - 재작성된 텍스트: {result.get('rewritten_text', 'N/A')}")
                print(f"    - 주제: {result.get('topic', 'N/A')}")
                print(f"    - 컨텍스트 사용: {result.get('context_used', 'N/A')}")
            else:
                print(f"  ✗ 실패: {', '.join(issues)}")
                print(f"    - 결과: {result}")
            
            # 테스트 결과 저장
            self.test_results.append({
                "test_name": test_case["name"],
                "success": success,
                "result": result,
                "issues": issues
            })
            
        except Exception as e:
            print(f"  ✗ 예외 발생: {str(e)}")
            self.test_results.append({
                "test_name": test_case["name"],
                "success": False,
                "result": None,
                "issues": [f"예외: {str(e)}"]
            })
    
    def print_summary(self):
        """테스트 결과 요약 출력"""
        print("\n=== 테스트 결과 요약 ===")
        
        total_tests = len(self.test_results)
        successful_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - successful_tests
        
        print(f"총 테스트 수: {total_tests}")
        print(f"성공: {successful_tests}")
        print(f"실패: {failed_tests}")
        print(f"성공률: {(successful_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\n실패한 테스트:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  - {result['test_name']}: {', '.join(result['issues'])}")

async def main():
    """메인 테스트 함수"""
    print("RewritingAgent 테스트 시작")
    print("=" * 50)
    
    tester = RewritingAgentTester()
    
    try:
        # 테스트 환경 설정
        await tester.setup()
        
        # Singleturn 테스트
        await tester.test_singleturn_scenarios()
        
        # Multiturn 테스트
        await tester.test_multiturn_scenarios()
        
        # 결과 요약
        tester.print_summary()
        
    except Exception as e:
        print(f"테스트 실행 중 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # 테스트 모드 설정 (Mock LLM 사용)
    os.environ['TEST_MODE'] = 'true'
    
    # asyncio 이벤트 루프 실행
    asyncio.run(main()) 