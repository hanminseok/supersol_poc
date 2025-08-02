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
        
        # 대화 맥락을 포함한 프롬프트 생성
        context_prompt = self._build_context_prompt(query, context)
        
        # LLM 호출
        messages = [
            self._create_system_message(),
            self._create_user_message(context_prompt)
        ]
        
        response = await self._call_llm(messages)
        
        # JSON 응답 파싱
        try:
            result = json.loads(response)
            return {
                "rewritten_text": result.get("rewritten_text", ""),
                "topic": result.get("topic", "")
            }
        except json.JSONDecodeError:
            self.logger.error(f"Failed to parse JSON response from {self.config.name}")
            # 기본 응답 생성
            return {
                "rewritten_text": response,
                "topic": "general"
            }
    
    def _build_context_prompt(self, query: list, context: Optional[Dict[str, Any]] = None) -> str:
        """컨텍스트를 포함한 프롬프트 생성"""
        prompt = f"""
다음 사용자 질문을 대화 맥락을 고려하여 명확하고 구체적으로 재작성해주세요.

사용자 질문: {query}

재작성된 질문과 주제를 다음 JSON 형식으로 응답해주세요:
{{
    "rewritten_text": "재작성된 명확한 질문",
    "topic": "질문의 주제 (예: banking, account, loan, investment, general)"
}}

재작성 시 고려사항:
1. 대화 맥락을 고려하여 명확하게 만듭니다
2. 은행 서비스와 관련된 용어를 정확히 사용합니다
3. 구체적이고 실행 가능한 질문으로 만듭니다
"""
        return prompt 