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
        
        # 입력 데이터 로깅
        self.logger.info(f"=== {self.config.name} Input ===")
        self.logger.info(f"Rewritten Text: {rewritten_text}")
        self.logger.info(f"Topic: {topic}")
        
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
            
            # intent 처리: 리스트인 경우 첫 번째 요소를 선택하거나 쉼표로 구분된 문자열로 변환
            intent_value = result.get("intent", "")
            if isinstance(intent_value, list):
                if len(intent_value) > 0:
                    intent_value = intent_value[0]  # 첫 번째 의도를 선택
                else:
                    intent_value = "general_inquiry"
            elif not isinstance(intent_value, str):
                intent_value = "general_inquiry"
            
            output_result = {
                "normalized_text": result.get("normalized_text", rewritten_text),
                "intent": intent_value,
                "slot": result.get("slot", [])
            }
            
            # 출력 데이터 로깅
            self.logger.info(f"=== {self.config.name} Output ===")
            self.logger.info(f"Result: {output_result}")
            
            return output_result
        except json.JSONDecodeError:
            self.logger.error(f"Failed to parse JSON response from {self.config.name}")
            # 기본 응답 생성
            default_result = {
                "normalized_text": rewritten_text,
                "intent": "general_inquiry",
                "slot": []
            }
            
            # 기본 출력 데이터 로깅
            self.logger.info(f"=== {self.config.name} Output (Default) ===")
            self.logger.info(f"Result: {default_result}")
            
            return default_result
    
    def _build_preprocessing_prompt(self, rewritten_text: str, topic: str) -> str:
        """전처리 프롬프트 생성"""
        prompt = f"""
다음 재작성된 질문을 분석하여 표준화된 텍스트, 의도, 그리고 필요한 슬롯을 추출해주세요.

재작성된 질문: {rewritten_text}
주제: {topic}

다음 JSON 형식으로 응답해주세요:
{{
    "normalized_text": "표준화된 질문 텍스트",
    "intent": "사용자 의도 (단일 의도만 선택: check_balance, transfer_money, loan_inquiry, investment_info, general_inquiry)",
    "slot": ["필요한_정보1", "필요한_정보2", ...]
}}

의도 분류 (가장 적합한 단일 의도만 선택):
- check_balance: 잔액 조회
- transfer_money: 송금
- loan_inquiry: 대출 문의
- investment_info: 투자 정보 (일반 투자 상품 정보)
- account_info: 계좌 정보 (일반 계좌 정보)
- transaction_history: 거래 내역 조회
- deposit_history: 입금 내역 조회
- auto_transfer_history: 자동이체 내역 조회
- minus_account_info: 마이너스 통장 정보 조회
- isa_account_info: ISA 계좌 정보 조회 (ISA 계좌 수익, 투자 내역)
- mortgage_rate_change: 주택담보대출 금리 변동 조회
- fund_info: 펀드 수익률 및 운용사 정보 조회
- hot_etf_info: 인기 ETF 정보 조회
- transfer_limit_change: 이체 한도 변경 기록 조회
- frequent_deposit_accounts: 자주 입금한 계좌 목록 조회
- loan_account_status: 대출 계좌 상태 조회
- general_inquiry: 일반 문의

주의: ISA 계좌 관련 질문은 반드시 "isa_account_info"로 분류해주세요.
주의: 주택담보대출 금리 변동 관련 질문은 반드시 "mortgage_rate_change"로 분류해주세요.
주의: 펀드 수익률 및 운용사 정보 관련 질문은 반드시 "fund_info"로 분류해주세요.
주의: 인기 ETF 정보 관련 질문은 반드시 "hot_etf_info"로 분류해주세요.
주의: 이체 한도 변경 기록 관련 질문은 반드시 "transfer_limit_change"로 분류해주세요.
주의: 자주 입금한 계좌 목록 관련 질문은 반드시 "frequent_deposit_accounts"로 분류해주세요.
주의: 대출 계좌 상태 관련 질문은 반드시 "loan_account_status"로 분류해주세요.

주의: intent는 반드시 단일 문자열이어야 하며, 리스트나 배열이 아닙니다.
여러 의도가 있는 경우 가장 주요한 의도를 하나만 선택해주세요.

슬롯 예시:
- account_number: 계좌번호
- amount: 금액
- recipient: 수신자
- loan_type: 대출 종류
- investment_product: 투자 상품
"""
        return prompt 