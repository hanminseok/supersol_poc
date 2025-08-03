#!/usr/bin/env python3
"""
next_agent 워크플로우 테스트 스크립트
"""

import asyncio
import json
import os
import sys
from typing import Dict, Any

# ver0.2 디렉토리를 Python 경로에 추가
ver0_2_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ver0.2")
sys.path.append(ver0_2_path)

from services.agent_manager import AgentManager
from services.chat_service import ChatService
from utils.logger import service_logger

async def test_agent_manager():
    """AgentManager 테스트"""
    print("=== AgentManager 테스트 ===")
    
    try:
        agent_manager = AgentManager()
        print("✓ AgentManager 초기화 성공")
        
        # Agent 목록 확인
        for agent_name, agent in agent_manager.agents.items():
            print(f"✓ {agent_name}: {agent.config.name}")
        
        # 단일 Agent 실행 테스트
        print("\n--- 단일 Agent 실행 테스트 ---")
        test_input = {
            "query": "123-456-789 계좌 잔액 확인해줘",
            "conversation_context": [],
            "current_state": {}
        }
        
        result = await agent_manager.execute_single_agent("rewriting", test_input)
        print(f"Rewriting Agent 결과: {json.dumps(result, ensure_ascii=False, indent=2)}")
        
        return True
        
    except Exception as e:
        print(f"✗ AgentManager 테스트 실패: {str(e)}")
        return False

async def test_workflow():
    """워크플로우 테스트"""
    print("\n=== 워크플로우 테스트 ===")
    
    try:
        agent_manager = AgentManager()
        
        # 워크플로우 실행 테스트
        test_input = {
            "query": "123-456-789 계좌 잔액 확인해줘",
            "conversation_context": [],
            "current_state": {}
        }
        
        print("워크플로우 실행 중...")
        result = await agent_manager.execute_workflow("rewriting", test_input)
        
        print(f"워크플로우 결과: {json.dumps(result, ensure_ascii=False, indent=2)}")
        
        # 결과 검증
        expected_keys = ["rewritten_text", "topic", "context_used", "normalized_text", "intent", "slot", "target_domain", "tool_name", "tool_output"]
        found_keys = list(result.keys())
        
        print(f"\n예상 키: {expected_keys}")
        print(f"실제 키: {found_keys}")
        
        # 필수 키들이 있는지 확인
        missing_keys = [key for key in expected_keys if key not in found_keys]
        if missing_keys:
            print(f"✗ 누락된 키: {missing_keys}")
            return False
        else:
            print("✓ 모든 필수 키가 포함됨")
            return True
            
    except Exception as e:
        print(f"✗ 워크플로우 테스트 실패: {str(e)}")
        return False

async def test_chat_service():
    """ChatService 테스트"""
    print("\n=== ChatService 테스트 ===")
    
    try:
        chat_service = ChatService()
        print("✓ ChatService 초기화 성공")
        
        # 간단한 채팅 처리 테스트
        session_id = "test_session_001"
        user_query = "123-456-789 계좌 잔액 확인해줘"
        
        print("채팅 처리 중...")
        response_chunks = []
        async for chunk in chat_service.process_chat(session_id, user_query):
            response_chunks.append(chunk)
        
        response = "".join(response_chunks)
        print(f"응답: {response}")
        
        if response and len(response) > 0:
            print("✓ ChatService 테스트 성공")
            return True
        else:
            print("✗ ChatService 응답이 비어있음")
            return False
            
    except Exception as e:
        print(f"✗ ChatService 테스트 실패: {str(e)}")
        return False

async def test_next_agent_config():
    """next_agent 설정 테스트"""
    print("\n=== next_agent 설정 테스트 ===")
    
    try:
        from models.agent_config import get_agent_config
        
        # 각 Agent의 next_agent 설정 확인
        agents = ["rewriting_agent", "preprocessing_agent", "supervisor_agent", "domain_agent"]
        
        for agent_name in agents:
            config = get_agent_config(agent_name)
            if config and hasattr(config, 'next_agent'):
                print(f"✓ {agent_name}: next_agent = {config.next_agent}")
            else:
                print(f"✗ {agent_name}: next_agent 설정 없음")
        
        return True
        
    except Exception as e:
        print(f"✗ next_agent 설정 테스트 실패: {str(e)}")
        return False

async def main():
    """메인 테스트 함수"""
    print("next_agent 워크플로우 테스트 시작\n")
    
    tests = [
        ("AgentManager", test_agent_manager),
        ("워크플로우", test_workflow),
        ("ChatService", test_chat_service),
        ("next_agent 설정", test_next_agent_config)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results[test_name] = result
        except Exception as e:
            print(f"✗ {test_name} 테스트에서 예외 발생: {str(e)}")
            results[test_name] = False
    
    # 결과 요약
    print("\n" + "="*50)
    print("테스트 결과 요약:")
    print("="*50)
    
    for test_name, result in results.items():
        status = "✓ 성공" if result else "✗ 실패"
        print(f"{test_name}: {status}")
    
    success_count = sum(results.values())
    total_count = len(results)
    
    print(f"\n전체: {success_count}/{total_count} 테스트 성공")
    
    if success_count == total_count:
        print("🎉 모든 테스트가 성공했습니다!")
        return 0
    else:
        print("❌ 일부 테스트가 실패했습니다.")
        return 1

if __name__ == "__main__":
    # 환경 변수 설정 (테스트 모드)
    os.environ['TEST_MODE'] = 'true'
    
    # 작업 디렉토리를 ver0.2로 변경
    ver0_2_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ver0.2")
    os.chdir(ver0_2_path)
    
    # 로깅 설정
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # 테스트 실행
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 