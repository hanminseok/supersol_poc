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
            default_intent = self.config.get("default_intent", "general_inquiry")
            
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
            default_intent = self.config.get("default_intent", "general_inquiry")
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
    
    def _prepare_next_agent_input(self, current_result: Dict[str, Any], original_input: Dict[str, Any]) -> Dict[str, Any]:
        """다음 Agent(Supervisor)의 입력 데이터 준비"""
        return {
            "normalized_text": current_result.get("normalized_text", ""),
            "intent": current_result.get("intent", ""),
            "slot": current_result.get("slot", []),
            "conversation_context": original_input.get("conversation_context", []),
            "current_state": original_input.get("current_state", {})
        }
    
    def _enhance_slots_with_context(self, slot: list, conversation_context: list, current_state: dict) -> list:
        """컨텍스트를 고려한 슬롯 보완"""
        enhanced_slot = slot.copy()
        
        # 이전 대화에서 계좌 정보 추출
        for entry in conversation_context:
            extracted_info = entry.get("extracted_info", {})
            accounts_mentioned = extracted_info.get("accounts_mentioned", [])
            
            for account in accounts_mentioned:
                if account not in enhanced_slot:
                    enhanced_slot.append(account)
        
        # 현재 상태에서 계좌 정보 추가
        selected_account = current_state.get("selected_account")
        if selected_account and selected_account not in enhanced_slot:
            enhanced_slot.append(selected_account)
        
        return enhanced_slot
    
    def _get_related_slots_for_intent(self, intent: str) -> list:
        """의도에 따른 관련 슬롯 반환"""
        intent_slots = self.config.get("intent_slots", {})
        return intent_slots.get(intent, [])
    
    def _build_context_aware_preprocessing_prompt(self, rewritten_text: str, topic: str, conversation_context: list, current_state: dict) -> str:
        """컨텍스트를 고려한 전처리 프롬프트 생성"""
        # 대화 컨텍스트 요약
        context_summary = self._summarize_conversation_context(conversation_context)
        
        # 현재 상태 정보
        current_state_info = self._format_current_state(current_state)
        
        # Get intents and intent_slots from JSON configuration
        intents = self.config.get("intents", {})
        intent_slots = self.config.get("intent_slots", {})
        
        # Format intents list
        intents_list = []
        for intent_key, intent_desc in intents.items():
            intents_list.append(f"- {intent_key}: {intent_desc}")
        intents_list_text = "\n".join(intents_list)
        
        # Format intent_slots list
        intent_slots_list = []
        for intent_key, slots in intent_slots.items():
            intent_slots_list.append(f"- {intent_key}: {', '.join(slots) if slots else '없음'}")
        intent_slots_list_text = "\n".join(intent_slots_list)
        
        # Get prompt template from JSON configuration
        prompt_template = self.config.get("prompt_template", {})
        intent_extraction_prompt_template = prompt_template.get("intent_extraction_prompt", [])
        
        # Handle both string and array formats
        if isinstance(intent_extraction_prompt_template, str):
            # If it's a string, format it directly
            prompt = intent_extraction_prompt_template.format(
                rewritten_text=rewritten_text,
                topic=topic,
                context_summary=context_summary,
                current_state_info=current_state_info,
                intents_list=intents_list_text,
                intent_slots_list=intent_slots_list_text
            )
        elif isinstance(intent_extraction_prompt_template, list):
            # If it's an array, join with newlines and then format
            prompt_lines = intent_extraction_prompt_template
            prompt_text = "\n".join(prompt_lines)
            prompt = prompt_text.format(
                rewritten_text=rewritten_text,
                topic=topic,
                context_summary=context_summary,
                current_state_info=current_state_info,
                intents_list=intents_list_text,
                intent_slots_list=intent_slots_list_text
            )
        else:
            # Fallback to empty string
            prompt = ""
        
        return prompt
    
    def _summarize_conversation_context(self, conversation_context: list) -> str:
        """대화 컨텍스트 요약"""
        if not conversation_context:
            return "이전 대화 없음"
        
        summary_parts = []
        
        # Get max conversation entries from JSON configuration
        context_settings = self.config.get("context_settings", {})
        max_entries = context_settings.get("max_conversation_entries", 3)
        
        for i, entry in enumerate(conversation_context[-max_entries:]):
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