#!/usr/bin/env python3
"""
Agent 간 JSON 통신 테스트 스크립트
실제 LLM을 호출하여 Agent 체인을 테스트합니다.
"""

import asyncio
import json
import os
from typing import Dict, Any, Optional
import sys

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents import RewritingAgent, PreprocessingAgent, SupervisorAgent, DomainAgent
from utils.logger import agent_logger

class MockAgentTester:
    """모의 응답을 사용하는 Agent 테스터"""
    
    def __init__(self):
        self.logger = agent_logger
    
    async def test_agent_chain(self, test_input: Dict[str, Any]) -> Dict[str, Any]:
        """모의 Agent 체인 테스트"""
        print("=== 모의 Agent JSON 통신 테스트 시작 ===\n")
        
        # 컨텍스트 초기화
        context = {
            "session_id": "mock_test_session_001",
            "depth": 0,
            "current_step": "start",
            "customer_info": test_input.get("customer_info", {})
        }
        
        try:
            # 1. Rewriting Agent 모의 응답
            print("1. Rewriting Agent 실행 (모의 응답)")
            rewriting_result = {
                "rewritten_text": f"재작성된 질문: {test_input['query'][0]}",
                "topic": "banking"
            }
            context["rewriting_result"] = rewriting_result
            context["depth"] = 1
            context["current_step"] = "rewriting"
            
            print(f"   결과: {json.dumps(rewriting_result, ensure_ascii=False, indent=2)}")
            
            # 2. Preprocessing Agent 모의 응답
            print("\n2. Preprocessing Agent 실행 (모의 응답)")
            preprocessing_result = {
                "normalized_text": f"표준화된 텍스트: {rewriting_result['rewritten_text']}",
                "intent": "query_balance",
                "slot": ["account_type"]
            }
            context["preprocessing_result"] = preprocessing_result
            context["depth"] = 2
            context["current_step"] = "preprocessing"
            
            print(f"   결과: {json.dumps(preprocessing_result, ensure_ascii=False, indent=2)}")
            
            # 3. Supervisor Agent 모의 응답
            print("\n3. Supervisor Agent 실행 (모의 응답)")
            supervisor_result = {
                "target_domain": "account",
                "normalized_text": preprocessing_result["normalized_text"],
                "intent": preprocessing_result["intent"],
                "slot": preprocessing_result["slot"]
            }
            context["supervisor_result"] = supervisor_result
            context["depth"] = 3
            context["current_step"] = "supervisor"
            
            print(f"   결과: {json.dumps(supervisor_result, ensure_ascii=False, indent=2)}")
            
            # 4. Domain Agent 모의 응답
            print("\n4. Domain Agent 실행 (모의 응답)")
            domain_result = {
                "tool_name": "account_balance",
                "tool_input": {
                    "customer_id": test_input.get("customer_info", {}).get("customer_id", "CUST001"),
                    "account_type": "checking"
                },
                "tool_output": {
                    "balance": 1000000,
                    "currency": "KRW",
                    "account_number": "123-456-789"
                }
            }
            
            print(f"   결과: {json.dumps(domain_result, ensure_ascii=False, indent=2)}")
            
            # 최종 결과 출력
            print("\n=== 최종 결과 ===")
            print(f"도구 이름: {domain_result.get('tool_name', 'N/A')}")
            print(f"도구 입력: {json.dumps(domain_result.get('tool_input', {}), ensure_ascii=False, indent=2)}")
            print(f"도구 출력: {json.dumps(domain_result.get('tool_output', {}), ensure_ascii=False, indent=2)}")
            
            print("\n=== 컨텍스트 전달 확인 ===")
            print(f"세션 ID: {context['session_id']}")
            print(f"최종 깊이: {context['depth']}")
            print(f"최종 단계: {context['current_step']}")
            
            print("\n=== 모의 Agent JSON 통신 테스트 완료 ===")
            
            return {
                "rewriting_result": rewriting_result,
                "preprocessing_result": preprocessing_result,
                "supervisor_result": supervisor_result,
                "domain_result": domain_result,
                "context": context
            }
            
        except Exception as e:
            self.logger.error(f"모의 Agent 체인 테스트 실패: {str(e)}")
            print(f"\n❌ 테스트 실패: {str(e)}")
            raise e

class RealAgentTester:
    """실제 LLM을 호출하는 Agent 테스터"""
    
    def __init__(self):
        self.logger = agent_logger
        self.agents = {}
        self._setup_agents()
    
    def _setup_agents(self):
        """실제 Agent 인스턴스 생성"""
        try:
            self.agents = {
                "rewriting": RewritingAgent(),
                "preprocessing": PreprocessingAgent(),
                "supervisor": SupervisorAgent(),
                "domain": DomainAgent()
            }
            self.logger.info("모든 Agent 인스턴스 생성 완료")
        except Exception as e:
            self.logger.error(f"Agent 설정 실패: {str(e)}")
            raise e
    
    async def test_agent_chain(self, test_input: Dict[str, Any]) -> Dict[str, Any]:
        """실제 Agent 체인 테스트"""
        print("=== 실제 LLM Agent JSON 통신 테스트 시작 ===\n")
        
        # 컨텍스트 초기화
        context = {
            "session_id": "real_test_session_001",
            "depth": 0,
            "current_step": "start",
            "customer_info": test_input.get("customer_info", {})
        }
        
        try:
            # 1. Rewriting Agent 실행
            print("1. Rewriting Agent 실행 (실제 LLM 호출)")
            rewriting_result = await self.agents["rewriting"].execute(test_input, context)
            context["rewriting_result"] = rewriting_result
            context["depth"] = 1
            context["current_step"] = "rewriting"
            
            print(f"   결과: {json.dumps(rewriting_result, ensure_ascii=False, indent=2)}")
            
            # 2. Preprocessing Agent 실행
            print("\n2. Preprocessing Agent 실행 (실제 LLM 호출)")
            preprocessing_input = {
                "rewritten_text": rewriting_result["rewritten_text"],
                "topic": rewriting_result["topic"],
                "customer_info": test_input.get("customer_info", {})
            }
            preprocessing_result = await self.agents["preprocessing"].execute(preprocessing_input, context)
            context["preprocessing_result"] = preprocessing_result
            context["depth"] = 2
            context["current_step"] = "preprocessing"
            
            print(f"   결과: {json.dumps(preprocessing_result, ensure_ascii=False, indent=2)}")
            
            # 3. Supervisor Agent 실행
            print("\n3. Supervisor Agent 실행 (실제 LLM 호출)")
            supervisor_input = {
                "normalized_text": preprocessing_result["normalized_text"],
                "intent": preprocessing_result["intent"],
                "slot": preprocessing_result["slot"],
                "customer_info": test_input.get("customer_info", {})
            }
            supervisor_result = await self.agents["supervisor"].execute(supervisor_input, context)
            context["supervisor_result"] = supervisor_result
            context["depth"] = 3
            context["current_step"] = "supervisor"
            
            print(f"   결과: {json.dumps(supervisor_result, ensure_ascii=False, indent=2)}")
            
            # 4. Domain Agent 실행
            print("\n4. Domain Agent 실행 (실제 LLM 호출)")
            domain_input = {
                "normalized_text": supervisor_result["normalized_text"],
                "intent": supervisor_result["intent"],
                "slot": supervisor_result["slot"],
                "target_domain": supervisor_result["target_domain"],
                "customer_info": test_input.get("customer_info", {})
            }
            domain_result = await self.agents["domain"].execute(domain_input, context)
            
            print(f"   결과: {json.dumps(domain_result, ensure_ascii=False, indent=2)}")
            
            # 최종 결과 출력
            print("\n=== 최종 결과 ===")
            print(f"도구 이름: {domain_result.get('tool_name', 'N/A')}")
            print(f"도구 입력: {json.dumps(domain_result.get('tool_input', {}), ensure_ascii=False, indent=2)}")
            print(f"도구 출력: {json.dumps(domain_result.get('tool_output', {}), ensure_ascii=False, indent=2)}")
            
            print("\n=== 컨텍스트 전달 확인 ===")
            print(f"세션 ID: {context['session_id']}")
            print(f"최종 깊이: {context['depth']}")
            print(f"최종 단계: {context['current_step']}")
            
            print("\n=== 실제 LLM Agent JSON 통신 테스트 완료 ===")
            
            return {
                "rewriting_result": rewriting_result,
                "preprocessing_result": preprocessing_result,
                "supervisor_result": supervisor_result,
                "domain_result": domain_result,
                "context": context
            }
            
        except Exception as e:
            self.logger.error(f"Agent 체인 테스트 실패: {str(e)}")
            print(f"\n❌ 테스트 실패: {str(e)}")
            raise e

async def run_tests():
    """다양한 테스트 케이스 실행"""
    from Config import Config
    
    # API 키가 있으면 실제 테스터, 없으면 모의 테스터 사용
    if Config.OPENAI_API_KEY:
        tester = RealAgentTester()
        print("실제 LLM을 사용한 테스트를 실행합니다.")
    else:
        tester = MockAgentTester()
        print("모의 응답을 사용한 테스트를 실행합니다.")
    
    # 테스트 케이스들
    test_cases = [
        {
            "name": "계좌 잔액 조회",
            "input": {
                "query": ["계좌 잔액 확인해줘"],
                "customer_info": {"name": "홍길동", "customer_id": "CUST001"}
            }
        },
        {
            "name": "송금 요청",
            "input": {
                "query": ["김철수에게 10만원 송금해줘"],
                "customer_info": {"name": "이영희", "customer_id": "CUST002"}
            }
        },
        {
            "name": "대출 문의",
            "input": {
                "query": ["대출 가능 금액이 얼마인가요?"],
                "customer_info": {"name": "박민수", "customer_id": "CUST003"}
            }
        },
        {
            "name": "투자 상품 문의",
            "input": {
                "query": ["투자 상품 추천해주세요"],
                "customer_info": {"name": "최지영", "customer_id": "CUST004"}
            }
        }
    ]
    
    results = {}
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"테스트 케이스 {i}: {test_case['name']}")
        print(f"{'='*60}")
        
        try:
            result = await tester.test_agent_chain(test_case["input"])
            results[test_case["name"]] = {
                "status": "success",
                "result": result
            }
            print(f"✅ {test_case['name']} 테스트 성공")
            
        except Exception as e:
            results[test_case["name"]] = {
                "status": "failed",
                "error": str(e)
            }
            print(f"❌ {test_case['name']} 테스트 실패: {str(e)}")
        
        # 테스트 간 간격
        if i < len(test_cases):
            print("\n다음 테스트를 위해 3초 대기...")
            await asyncio.sleep(3)
    
    # 전체 결과 요약
    print(f"\n{'='*60}")
    print("전체 테스트 결과 요약")
    print(f"{'='*60}")
    
    success_count = 0
    for test_name, result in results.items():
        status = "✅ 성공" if result["status"] == "success" else "❌ 실패"
        print(f"{test_name}: {status}")
        if result["status"] == "success":
            success_count += 1
    
    print(f"\n총 {len(test_cases)}개 테스트 중 {success_count}개 성공")
    
    if success_count == len(test_cases):
        print("🎉 모든 테스트 통과!")
    else:
        print(f"⚠️  {len(test_cases) - success_count}개 테스트 실패")
    
    return results

if __name__ == "__main__":
    # 환경 변수 확인
    print("환경 설정 확인 중...")
    
    # API 키 확인
    from Config import Config
    
    if not Config.OPENAI_API_KEY:
        print("⚠️  OPENAI_API_KEY가 설정되지 않았습니다.")
        print("   모의 응답으로 테스트를 진행합니다.")
        print("   실제 LLM 테스트를 원한다면 .env 파일에 OPENAI_API_KEY를 설정해주세요.")
    
    if not Config.DEEPINFRA_API_KEY:
        print("⚠️  DEEPINFRA_API_KEY가 설정되지 않았습니다.")
        print("   OpenAI만 사용합니다.")
    
    print("✅ 환경 설정 확인 완료")
    print(f"   OpenAI API Key: {'설정됨' if Config.OPENAI_API_KEY else '설정되지 않음'}")
    print(f"   DeepInfra API Key: {'설정됨' if Config.DEEPINFRA_API_KEY else '설정되지 않음'}")
    
    # 테스트 실행
    try:
        results = asyncio.run(run_tests())
        
        # JSON 구조 검증
        print("\n=== JSON 구조 검증 ===")
        
        for test_name, result in results.items():
            if result["status"] == "success":
                test_result = result["result"]
                
                # 각 Agent 출력 검증
                agents_to_check = [
                    ("Rewriting", test_result["rewriting_result"], ["rewritten_text", "topic"]),
                    ("Preprocessing", test_result["preprocessing_result"], ["normalized_text", "intent", "slot"]),
                    ("Supervisor", test_result["supervisor_result"], ["target_domain"]),
                    ("Domain", test_result["domain_result"], ["tool_name", "tool_input", "tool_output"])
                ]
                
                all_valid = True
                for agent_name, output, required_fields in agents_to_check:
                    for field in required_fields:
                        if field not in output:
                            print(f"❌ {test_name} - {agent_name} Agent: {field} 필드 누락")
                            all_valid = False
                
                if all_valid:
                    print(f"✅ {test_name}: 모든 JSON 구조 검증 통과")
        
        print("\n🎉 실제 LLM Agent JSON 통신 테스트 완료!")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  테스트가 사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n❌ 테스트 실행 중 오류 발생: {str(e)}")
        sys.exit(1) 