import asyncio
import json
import os
import sys
import requests

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.chat_service import ChatService

async def test_api_direct_response():
    """API를 통해 direct_response 테스트"""
    print("=== API Direct Response 테스트 시작 ===")
    
    # ChatService 인스턴스 생성
    chat_service = ChatService()
    
    # 테스트 케이스 1: 일반 질문 (날씨 관련)
    print("\n1. 일반 질문 테스트 (날씨 관련)...")
    session_id = "test_session_weather"
    user_query = "오늘 날씨가 어떤가요?"
    
    try:
        responses = []
        async for response in chat_service.process_chat(
            session_id=session_id,
            user_query=user_query,
            customer_info=None
        ):
            responses.append(response)
            print(f"응답 청크: {response}")
        
        # 최종 응답 확인
        final_response = ""
        for response in responses:
            if response.startswith('{"type": "response"'):
                data = json.loads(response)
                final_response += data.get("content", "")
        
        print(f"\n최종 응답: {final_response}")
        
        # direct_response가 제대로 전달되었는지 확인
        if "날씨" in final_response and ("AI" in final_response or "인터넷" in final_response or "앱" in final_response):
            print("✓ direct_response가 제대로 사용자에게 전달되었습니다.")
        else:
            print("⚠ direct_response가 제대로 전달되지 않았습니다.")
            
    except Exception as e:
        print(f"❌ 테스트 실패: {str(e)}")
    
    # 테스트 케이스 2: 은행 관련 질문
    print("\n2. 은행 관련 질문 테스트 (계좌 잔액)...")
    session_id = "test_session_banking"
    user_query = "내 계좌 잔액을 확인해주세요"
    
    try:
        responses = []
        async for response in chat_service.process_chat(
            session_id=session_id,
            user_query=user_query,
            customer_info=None
        ):
            responses.append(response)
            print(f"응답 청크: {response}")
        
        # 최종 응답 확인
        final_response = ""
        for response in responses:
            if response.startswith('{"type": "response"'):
                data = json.loads(response)
                final_response += data.get("content", "")
        
        print(f"\n최종 응답: {final_response}")
        
        # 은행 관련 응답이 제대로 전달되었는지 확인
        if "계좌" in final_response or "잔액" in final_response:
            print("✓ 은행 관련 응답이 제대로 사용자에게 전달되었습니다.")
        else:
            print("⚠ 은행 관련 응답이 제대로 전달되지 않았습니다.")
            
    except Exception as e:
        print(f"❌ 테스트 실패: {str(e)}")
    
    print("\n=== API 테스트 완료 ===")

async def main():
    """메인 함수"""
    await test_api_direct_response()

if __name__ == "__main__":
    asyncio.run(main()) 