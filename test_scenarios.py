#!/usr/bin/env python3
"""
SuperSOL 시나리오 테스트 스크립트
"""

import asyncio
import json
import sys
import os
from typing import Dict, Any, List

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 테스트 모드 활성화
os.environ['TEST_MODE'] = 'true'

from services.chat_service import ChatService
from utils.logger import service_logger

class ScenarioTester:
    def __init__(self):
        self.chat_service = ChatService()
        self.test_results = []
        
    def load_scenarios(self, file_path: str) -> Dict[int, List[str]]:
        """TestSet2.txt에서 시나리오 로드"""
        scenarios = {}
        current_scenario = None
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                    
                parts = line.split('\t')
                if len(parts) >= 2:
                    scenario_num = int(parts[0])
                    question = parts[1]
                    
                    if scenario_num not in scenarios:
                        scenarios[scenario_num] = []
                    scenarios[scenario_num].append(question)
        
        return scenarios
    
    async def test_scenario(self, scenario_num: int, questions: List[str]) -> Dict[str, Any]:
        """단일 시나리오 테스트"""
        print(f"\n=== 시나리오 {scenario_num} 테스트 ===")
        print(f"질문: {questions}")
        
        results = {
            "scenario_num": scenario_num,
            "questions": questions,
            "responses": [],
            "errors": []
        }
        
        try:
            # 새로운 세션 시작
            session_id = f"test_scenario_{scenario_num}"
            
            for i, question in enumerate(questions):
                print(f"\n--- 질문 {i+1}: {question} ---")
                
                try:
                    # 채팅 서비스 호출
                    response_generator = self.chat_service.process_chat(
                        session_id=session_id,
                        user_query=question
                    )
                    
                    # 응답 수집
                    response_text = ""
                    async for chunk in response_generator:
                        response_text += chunk
                    
                    print(f"응답: {response_text}")
                    
                    results["responses"].append({
                        "question": question,
                        "response": response_text,
                        "success": True
                    })
                    
                except Exception as e:
                    error_msg = f"질문 {i+1} 처리 중 오류: {str(e)}"
                    print(f"오류: {error_msg}")
                    results["errors"].append(error_msg)
                    results["responses"].append({
                        "question": question,
                        "response": f"오류: {str(e)}",
                        "success": False
                    })
                    
        except Exception as e:
            error_msg = f"시나리오 {scenario_num} 전체 오류: {str(e)}"
            print(f"오류: {error_msg}")
            results["errors"].append(error_msg)
        
        return results
    
    async def run_tests(self, scenarios: Dict[int, List[str]], max_scenarios: int = 5):
        """모든 시나리오 테스트 실행"""
        print(f"총 {len(scenarios)}개 시나리오 중 {max_scenarios}개 테스트 시작")
        
        for i, (scenario_num, questions) in enumerate(scenarios.items()):
            if i >= max_scenarios:
                break
                
            result = await self.test_scenario(scenario_num, questions)
            self.test_results.append(result)
            
            # 잠시 대기
            await asyncio.sleep(1)
        
        # 결과 요약
        self.print_summary()
    
    def print_summary(self):
        """테스트 결과 요약 출력"""
        print("\n" + "="*50)
        print("테스트 결과 요약")
        print("="*50)
        
        total_scenarios = len(self.test_results)
        successful_scenarios = sum(1 for r in self.test_results if not r["errors"])
        total_errors = sum(len(r["errors"]) for r in self.test_results)
        
        print(f"총 시나리오: {total_scenarios}")
        print(f"성공한 시나리오: {successful_scenarios}")
        print(f"실패한 시나리오: {total_scenarios - successful_scenarios}")
        print(f"총 오류 수: {total_errors}")
        
        if total_errors > 0:
            print("\n오류 목록:")
            for result in self.test_results:
                for error in result["errors"]:
                    print(f"- 시나리오 {result['scenario_num']}: {error}")

async def main():
    """메인 함수"""
    try:
        tester = ScenarioTester()
        
        # 시나리오 로드
        scenarios = tester.load_scenarios("tests/TestSet2.txt")
        print(f"로드된 시나리오 수: {len(scenarios)}")
        
        # 처음 5개 시나리오만 테스트
        await tester.run_tests(scenarios, max_scenarios=5)
        
    except Exception as e:
        print(f"테스트 실행 중 오류: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main()) 