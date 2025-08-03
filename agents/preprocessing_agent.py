import json
from typing import Dict, Any, Optional
from .base_agent import BaseAgent
from models.agent_config import get_agent_config
from config.config_loader import config_loader

class PreprocessingAgent(BaseAgent):
    def __init__(self):
        config = get_agent_config("preprocessing_agent")
        if not config:
            raise ValueError("Preprocessing agent config not found")
        super().__init__(config)
    
    async def _process(self, input_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """질문 전처리 및 의도/슬롯 추출 - 멀티턴 질의 지원"""
        rewritten_text = input_data.get("rewritten_text", "")
        topic = input_data.get("topic", "")
        
        # 컨텍스트에서 추가 정보 추출
        conversation_context = input_data.get("conversation_context", [])
        current_state = input_data.get("current_state", {})
        
        # 입력 데이터 로깅
        self.logger.info(f"=== {self.config.name} Input ===")
        self.logger.info(f"Rewritten Text: {rewritten_text}")
        self.logger.info(f"Topic: {topic}")
        self.logger.info(f"Conversation Context: {len(conversation_context)} entries")
        self.logger.info(f"Current State: {current_state}")
        
        # 컨텍스트를 고려한 전처리 프롬프트 생성
        prompt = self._build_context_aware_preprocessing_prompt(rewritten_text, topic, conversation_context, current_state)
        
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
            context_settings = config_loader.get_context_settings()
            default_intent = context_settings.get("default_intent", "general_inquiry")
            
            if isinstance(intent_value, list):
                if len(intent_value) > 0:
                    intent_value = intent_value[0]  # 첫 번째 의도를 선택
                else:
                    intent_value = default_intent
            elif not isinstance(intent_value, str):
                intent_value = default_intent
            
            # 컨텍스트를 고려한 슬롯 보완
            enhanced_slot = self._enhance_slots_with_context(result.get("slot", []), conversation_context, current_state)
            
            output_result = {
                "normalized_text": result.get("normalized_text", rewritten_text),
                "intent": intent_value,
                "slot": enhanced_slot,
                "context_used": result.get("context_used", False)
            }
            
            # 출력 데이터 로깅
            self.logger.info(f"=== {self.config.name} Output ===")
            self.logger.info(f"Result: {output_result}")
            
            return output_result
        except json.JSONDecodeError:
            self.logger.error(f"Failed to parse JSON response from {self.config.name}")
            # 기본 응답 생성 - 컨텍스트를 고려한 보완
            enhanced_slot = self._enhance_slots_with_context([], conversation_context, current_state)
            context_settings = config_loader.get_context_settings()
            default_intent = context_settings.get("default_intent", "general_inquiry")
            default_result = {
                "normalized_text": rewritten_text,
                "intent": default_intent,
                "slot": enhanced_slot,
                "context_used": False
            }
            
            # 기본 출력 데이터 로깅
            self.logger.info(f"=== {self.config.name} Output (Default) ===")
            self.logger.info(f"Result: {default_result}")
            
            return default_result
    
    def _enhance_slots_with_context(self, slot: list, conversation_context: list, current_state: dict) -> list:
        """컨텍스트를 고려한 슬롯 보완"""
        enhanced_slot = slot.copy()
        
        # 이전 대화에서 계좌 정보 추출
        for entry in conversation_context:
            extracted_info = entry.get("extracted_info", {})
            accounts_mentioned = extracted_info.get("accounts_mentioned", [])
            
            # 계좌 관련 슬롯이 없고 이전에 계좌가 언급되었다면 추가
            if not any("account" in s.lower() for s in enhanced_slot) and accounts_mentioned:
                enhanced_slot.append("account_number")
        
        # 현재 상태에서 선택된 계좌 정보 추가
        selected_account = current_state.get("selected_account")
        if selected_account and "account_number" not in enhanced_slot:
            enhanced_slot.append("account_number")
        
        # 이전 의도와 슬롯 정보 추가
        last_intent = current_state.get("last_intent")
        last_slots = current_state.get("last_slots", [])
        
        # 이전 의도와 연관된 슬롯 추가
        if last_intent:
            related_slots = self._get_related_slots_for_intent(last_intent)
            for related_slot in related_slots:
                if related_slot not in enhanced_slot:
                    enhanced_slot.append(related_slot)
        
        # 이전 슬롯 중 현재 슬롯에 없는 것들 추가
        for last_slot in last_slots:
            if last_slot not in enhanced_slot:
                enhanced_slot.append(last_slot)
        
        return enhanced_slot
    
    def _get_related_slots_for_intent(self, intent: str) -> list:
        """의도와 연관된 슬롯 반환"""
        intent_slots = config_loader.get_intent_slots("preprocessing_agent")
        return intent_slots.get(intent, [])
    
    def _build_context_aware_preprocessing_prompt(self, rewritten_text: str, topic: str, conversation_context: list, current_state: dict) -> str:
        """컨텍스트를 고려한 전처리 프롬프트 생성"""
        # 대화 컨텍스트 요약
        context_summary = self._summarize_conversation_context(conversation_context)
        
        # 현재 상태 정보
        current_state_info = self._format_current_state(current_state)
        
        prompt = f"""
다음 재작성된 질문을 분석하여 표준화된 텍스트, 의도, 그리고 필요한 슬롯을 추출해주세요.

재작성된 질문: {rewritten_text}
주제: {topic}

대화 컨텍스트:
{context_summary}

현재 상태:
{current_state_info}

다음 JSON 형식으로 응답해주세요:
{{
    "normalized_text": "표준화된 질문 텍스트",
    "intent": "사용자 의도 (단일 의도만 선택: check_balance, transfer_money, loan_inquiry, investment_info, general_inquiry)",
    "slot": ["필요한_정보1", "필요한_정보2", ...],
    "context_used": true/false
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

컨텍스트 활용 가이드:
1. 이전 대화에서 언급된 계좌 정보가 있다면 해당 계좌를 참조
2. "그 계좌", "이 계좌" 등의 표현은 이전에 언급된 계좌를 의미
3. "잔액은?" 같은 단축 표현은 이전 의도를 유지
4. 대화 맥락을 고려하여 의도와 슬롯을 추출

슬롯 예시:
- account_number: 계좌번호
- amount: 금액
- recipient: 수신자
- loan_type: 대출 종류
- investment_product: 투자 상품
"""
        return prompt
    
    def _summarize_conversation_context(self, conversation_context: list) -> str:
        """대화 컨텍스트 요약"""
        if not conversation_context:
            return "이전 대화 없음"
        
        summary_parts = []
        
        for i, entry in enumerate(conversation_context[-3:]):  # 최근 3개 대화만 요약
            user_query = entry.get("user_query", "")
            extracted_info = entry.get("extracted_info", {})
            
            summary = f"대화 {i+1}: {user_query}"
            
            # 추출된 정보 추가
            intent = extracted_info.get("intent")
            tool_name = extracted_info.get("tool_name")
            accounts = extracted_info.get("accounts_mentioned", [])
            
            if intent:
                summary += f" (의도: {intent})"
            if tool_name:
                summary += f" (도구: {tool_name})"
            if accounts:
                summary += f" (계좌: {', '.join(accounts)})"
            
            summary_parts.append(summary)
        
        return "\n".join(summary_parts)
    
    def _format_current_state(self, current_state: dict) -> str:
        """현재 상태 정보 포맷팅"""
        if not current_state:
            return "상태 정보 없음"
        
        state_parts = []
        
        selected_account = current_state.get("selected_account")
        if selected_account:
            state_parts.append(f"- 선택된 계좌: {selected_account}")
        
        last_intent = current_state.get("last_intent")
        if last_intent:
            state_parts.append(f"- 이전 의도: {last_intent}")
        
        last_slots = current_state.get("last_slots", [])
        if last_slots:
            state_parts.append(f"- 이전 슬롯: {', '.join(last_slots)}")
        
        pending_action = current_state.get("pending_action")
        if pending_action:
            state_parts.append(f"- 진행 중인 작업: {pending_action}")
        
        if not state_parts:
            return "상태 정보 없음"
        
        return "\n".join(state_parts) 