import json
from typing import Dict, Any, Optional
from .base_agent import BaseAgent
from models.agent_config import get_agent_config

class RewritingAgent(BaseAgent):
    def __init__(self):
        config = get_agent_config("rewriting_agent")
        if not config:
            raise ValueError("Rewriting agent config not found")
        super().__init__(config)
    
    async def _process(self, input_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """질문 재작성 처리"""
        query = input_data.get("query", [])
        
        # 입력 데이터 로깅
        self.logger.info(f"=== {self.config.name} Input ===")
        self.logger.info(f"Query: {query}")
        self.logger.info(f"Context: {context}")
        
        # 대화 맥락을 포함한 프롬프트 생성
        context_prompt = self._build_context_prompt(query, context)
        
        # LLM 호출
        messages = [
            self._create_system_message(),
            self._create_user_message(context_prompt)
        ]
        
        response = await self._call_llm(messages)
        
        # JSON 응답 파싱 - 개선된 버전
        result = self._parse_json_response(response, input_data)
        
        # 출력 데이터 로깅
        self.logger.info(f"=== {self.config.name} Output ===")
        self.logger.info(f"Result: {result}")
        
        return result
    
    def _parse_json_response(self, response: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """JSON 응답 파싱 - 개선된 버전"""
        if not response or response.strip() == "":
            self.logger.warning(f"Empty response from {self.config.name}")
            return self._create_default_response(input_data)
        
        # JSON 블록 추출 시도
        json_response = self._extract_json_from_response(response)
        
        try:
            result = json.loads(json_response)
            
            # 필수 필드 확인 및 기본값 설정
            rewritten_text = result.get("rewritten_text", "")
            topic = result.get("topic", "general")
            
            if not rewritten_text:
                self.logger.warning(f"Empty rewritten_text in response from {self.config.name}")
                return self._create_default_response(input_data, topic)
            
            return {
                "rewritten_text": rewritten_text,
                "topic": topic
            }
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON response from {self.config.name}: {str(e)}")
            self.logger.error(f"Raw response: {response}")
            return self._create_default_response(input_data)
    
    def _extract_json_from_response(self, response: str) -> str:
        """응답에서 JSON 블록 추출"""
        response = response.strip()
        
        # JSON 블록이 ```json ... ``` 형태로 감싸져 있는 경우
        if "```json" in response and "```" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            if end != -1:
                return response[start:end].strip()
        
        # JSON 블록이 ``` ... ``` 형태로 감싸져 있는 경우
        if "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            if end != -1:
                return response[start:end].strip()
        
        # 중괄호로 시작하고 끝나는 JSON 찾기
        if response.startswith("{") and response.endswith("}"):
            return response
        
        # 중괄호로 시작하는 부분 찾기
        start = response.find("{")
        if start != -1:
            # 중괄호 카운팅으로 JSON 끝 찾기
            brace_count = 0
            for i, char in enumerate(response[start:], start):
                if char == "{":
                    brace_count += 1
                elif char == "}":
                    brace_count -= 1
                    if brace_count == 0:
                        return response[start:i+1]
        
        return response
    
    def _create_default_response(self, input_data: Dict[str, Any], topic: str = "general") -> Dict[str, Any]:
        """기본 응답 생성"""
        original_query = input_data.get("query", "")
        if isinstance(original_query, list):
            original_query = " ".join(original_query)
        
        return {
            "rewritten_text": original_query if original_query else "질문을 이해하지 못했습니다.",
            "topic": topic
        }
    
    def _build_context_prompt(self, query: list, context: Optional[Dict[str, Any]] = None) -> str:
        """컨텍스트를 포함한 프롬프트 생성"""
        prompt = f"""
다음 사용자 질문을 대화 맥락을 고려하여 명확하고 구체적으로 재작성해주세요.

사용자 질문: {query}

반드시 다음 JSON 형식으로만 응답해주세요. 다른 텍스트는 포함하지 마세요:
{{
    "rewritten_text": "재작성된 명확한 질문",
    "topic": "질문의 주제 (예: banking, account, loan, investment, general)"
}}

재작성 시 고려사항:
1. 대화 맥락을 고려하여 명확하게 만듭니다
2. 은행 서비스와 관련된 용어를 정확히 사용합니다
3. 구체적이고 실행 가능한 질문으로 만듭니다
4. 반드시 JSON 형식을 정확히 지켜주세요

응답 예시:
{{
    "rewritten_text": "계좌 잔액을 확인하고 싶습니다",
    "topic": "account"
}}
"""
        return prompt 