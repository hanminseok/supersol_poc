import asyncio
import os
import sys
from unittest.mock import patch

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.agent_manager import AgentManager

async def test_workflow_conditional_routing():
    """워크플로우에서 conditional_routing 테스트"""
    print("=== 워크플로우 Conditional Routing 테스트 시작 ===")
    
    # Agent Manager 초기화
    agent_manager = AgentManager()
    
    # 테스트 케이스 1: 일반 질문 (general topic)
    print("\n1. 일반 질문 테스트 (날씨 관련)...")
    input_data_1 = {
        "query": "오늘 날씨가 어떤가요?",
        "conversation_context": [],
        "current_state": {}
    }
    
    try:
        result_1 = await agent_manager.execute_workflow("rewriting_agent", input_data_1)
        print(f"결과: {result_1}")
        
        # general topic이면 다음 agent를 건너뛰어야 함
        if result_1.get("topic") == "general" or result_1.get("is_general"):
            print("✓ 일반 질문이 감지되어 다음 agent를 건너뛰었습니다.")
            if "direct_response" in result_1:
                print(f"✓ 직접 답변 생성: {result_1['direct_response']}")
        else:
            print("⚠ 일반 질문이 감지되지 않았습니다.")
            
    except Exception as e:
        print(f"❌ 테스트 실패: {str(e)}")
    
    # 테스트 케이스 2: 은행 관련 질문 (account topic)
    print("\n2. 은행 관련 질문 테스트 (계좌 잔액)...")
    input_data_2 = {
        "query": "내 계좌 잔액을 확인해주세요",
        "conversation_context": [],
        "current_state": {}
    }
    
    try:
        result_2 = await agent_manager.execute_workflow("rewriting_agent", input_data_2)
        print(f"결과: {result_2}")
        
        # account topic이면 다음 agent로 진행해야 함
        if result_2.get("topic") in ["account", "banking", "loan", "investment"]:
            print("✓ 은행 관련 질문이 감지되어 다음 agent로 진행합니다.")
        else:
            print("⚠ 은행 관련 질문이 감지되지 않았습니다.")
            
    except Exception as e:
        print(f"❌ 테스트 실패: {str(e)}")
    
    print("\n=== 워크플로우 테스트 완료 ===")

async def main():
    """메인 함수"""
    await test_workflow_conditional_routing()

if __name__ == "__main__":
    asyncio.run(main()) 