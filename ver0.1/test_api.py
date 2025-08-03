#!/usr/bin/env python3
"""
SuperSOL API 테스트 스크립트
"""

import requests
import json
import time

def test_health():
    """헬스 체크 테스트"""
    try:
        response = requests.get("http://localhost:8001/health")
        print(f"Health Check: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Health check failed: {e}")
        return False

def test_chat():
    """채팅 API 테스트"""
    try:
        data = {
            "message": "고객정보를 조회해주세요",
            "user_id": "test_user_001"
        }
        
        response = requests.post(
            "http://localhost:8001/chat",
            json=data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Chat API: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Chat API failed: {e}")
        return False

def test_root():
    """루트 엔드포인트 테스트"""
    try:
        response = requests.get("http://localhost:8001/")
        print(f"Root: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Root test failed: {e}")
        return False

def main():
    """메인 테스트 함수"""
    print("🏦 SuperSOL API 테스트 시작")
    print("=" * 50)
    
    # 서버 시작 대기
    print("서버 시작 대기 중...")
    time.sleep(3)
    
    # 테스트 실행
    tests = [
        ("Health Check", test_health),
        ("Root Endpoint", test_root),
        ("Chat API", test_chat),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n📋 {test_name} 테스트")
        print("-" * 30)
        success = test_func()
        results.append((test_name, success))
        print(f"결과: {'✅ 성공' if success else '❌ 실패'}")
    
    # 결과 요약
    print("\n" + "=" * 50)
    print("📊 테스트 결과 요약")
    print("=" * 50)
    
    for test_name, success in results:
        status = "✅ 성공" if success else "❌ 실패"
        print(f"{test_name}: {status}")
    
    success_count = sum(1 for _, success in results if success)
    total_count = len(results)
    
    print(f"\n전체: {success_count}/{total_count} 테스트 통과")
    
    if success_count == total_count:
        print("🎉 모든 테스트가 성공했습니다!")
    else:
        print("⚠️  일부 테스트가 실패했습니다.")

if __name__ == "__main__":
    main() 