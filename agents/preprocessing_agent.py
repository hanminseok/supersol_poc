import json
from typing import Dict, Any, Optional
from .base_agent import BaseAgent
from models.agent_config import get_agent_config

class PreprocessingAgent(BaseAgent):
    def __init__(self):
        config = get_agent_config("preprocessing_agent")
        if not config:
            raise ValueError("Preprocessing agent config not found")
        super().__init__(config)
    
    async def _process(self, input_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """질문 전처리 및 의도/슬롯 추출"""
        rewritten_text = input_data.get("rewritten_text", "")
        topic = input_data.get("topic", "")
        
        # 전처리 프롬프트 생성
        prompt = self._build_preprocessing_prompt(rewritten_text, topic)
        
        # LLM 호출
        messages = [
            self._create_system_message(),
            self._create_user_message(prompt)
        ]
        
        response = await self._call_llm(messages)
        
        # JSON 응답 파싱
        try:
            result = json.loads(response)
            return {
                "normalized_text": result.get("normalized_text", rewritten_text),
                "intent": result.get("intent", ""),
                "slot": result.get("slot", [])
            }
        except json.JSONDecodeError:
            self.logger.error(f"Failed to parse JSON response from {self.config.name}")
            # 기본 응답 생성
            return {
                "normalized_text": rewritten_text,
                "intent": "general_inquiry",
                "slot": []
            }
    
    def _build_preprocessing_prompt(self, rewritten_text: str, topic: str) -> str:
        """전처리 프롬프트 생성"""
        prompt = f"""
다음 재작성된 질문을 분석하여 표준화된 텍스트, 의도, 그리고 필요한 슬롯을 추출해주세요.

재작성된 질문: {rewritten_text}
주제: {topic}

다음 JSON 형식으로 응답해주세요:
{{
    "normalized_text": "표준화된 질문 텍스트",
    "intent": "사용자 의도 (예: check_balance, transfer_money, loan_inquiry, investment_info, general_inquiry)",
    "slot": ["필요한_정보1", "필요한_정보2", ...]
}}

의도 분류:
- check_balance: 잔액 조회
- transfer_money: 송금
- loan_inquiry: 대출 문의
- investment_info: 투자 정보
- account_info: 계좌 정보
- general_inquiry: 일반 문의

슬롯 예시:
- account_number: 계좌번호
- amount: 금액
- recipient: 수신자
- loan_type: 대출 종류
- investment_product: 투자 상품
"""
        return prompt 