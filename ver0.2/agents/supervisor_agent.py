import json
import asyncio
from typing import Dict, Any, Optional, List
from .base_agent import BaseAgent
from models.agent_config import get_agent_config

class SupervisorAgent(BaseAgent):
    def __init__(self):
        config = get_agent_config("supervisor_agent")
        if not config:
            raise ValueError("Supervisor agent config not found")
        super().__init__(config)
    
    async def _process(self, input_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """질문 분석 및 도메인 라우팅 - 멀티턴 질의 지원"""
        normalized_text = input_data.get("normalized_text", "")
        intent = input_data.get("intent", "")
        slot = input_data.get("slot", [])
        
        # 컨텍스트에서 추가 정보 추출
        conversation_context = input_data.get("conversation_context", [])
        current_state = input_data.get("current_state", {})
        
        # 입력 데이터 로깅
        self.logger.info(f"=== {self.config.name} Input ===")
        self.logger.info(f"Normalized Text: {normalized_text}")
        self.logger.info(f"Intent: {intent}")
        self.logger.info(f"Slot: {slot}")
        self.logger.info(f"Conversation Context: {len(conversation_context)} entries")
        self.logger.info(f"Current State: {current_state}")
        
        # 컨텍스트 업데이트
        updated_context = self._update_context(context, input_data)
        
        # 컨텍스트를 고려한 라우팅 결정
        routing_decision = await self._make_context_aware_routing_decision(
            normalized_text, intent, slot, updated_context
        )
        
        result = {
            "target_domain": routing_decision.get("target_domain", "general"),
            "normalized_text": normalized_text,
            "intent": intent,
            "slot": slot,
            "context": updated_context,
            "routing_reasoning": routing_decision.get("reasoning", "")
        }
        
        # 출력 데이터 로깅
        self.logger.info(f"=== {self.config.name} Output ===")
        self.logger.info(f"Result: {result}")
        
        return result
    
    def _prepare_next_agent_input(self, current_result: Dict[str, Any], original_input: Dict[str, Any]) -> Dict[str, Any]:
        """다음 Agent(Domain)의 입력 데이터 준비"""
        return {
            "target_domain": current_result.get("target_domain", ""),
            "normalized_text": current_result.get("normalized_text", ""),
            "intent": current_result.get("intent", ""),
            "slot": current_result.get("slot", []),
            "context": current_result.get("context", {})
        }
    
    def _update_context(self, context: Optional[Dict[str, Any]], input_data: Dict[str, Any]) -> Dict[str, Any]:
        """컨텍스트 업데이트"""
        if context is None:
            context = {
                "session_id": "",
                "depth": 0,
                "current_step": "supervisor",
                "status_history": [],
                "agent_call_history": [],
                "missing_slots": []
            }
        
        # 필수 키들이 없으면 기본값 설정
        if "status_history" not in context:
            context["status_history"] = []
        if "agent_call_history" not in context:
            context["agent_call_history"] = []
        if "missing_slots" not in context:
            context["missing_slots"] = []
        
        # 현재 상태 기록
        context["status_history"].append(f"supervisor_processing_{input_data.get('intent', 'unknown')}")
        context["agent_call_history"].append({
            "agent_name": self.config.name,
            "status": "processing"
        })
        
        return context
    
    async def _make_context_aware_routing_decision(self, normalized_text: str, intent: str, slot: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        """컨텍스트를 고려한 라우팅 결정"""
        prompt = self._build_context_aware_routing_prompt(normalized_text, intent, slot, context)
        
        messages = [
            self._create_system_message(),
            self._create_user_message(prompt)
        ]
        
        response = await self._call_llm(messages)
        
        try:
            result = json.loads(response)
            return {
                "target_domain": result.get("target_domain", "general"),
                "reasoning": result.get("reasoning", "")
            }
        except json.JSONDecodeError:
            self.logger.error(f"Failed to parse JSON response from {self.config.name}")
            return self._default_context_aware_routing(intent, context)
    
    def _default_context_aware_routing(self, intent: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """기본 라우팅 결정"""
        # Get intent-domain mapping from JSON configuration
        intent_domain_mapping = self.config.get("intent_domain_mapping", {})
        default_domain = self.config.get("default_domain", "general")
        
        target_domain = intent_domain_mapping.get(intent, default_domain)
        
        return {
            "target_domain": target_domain,
            "reasoning": f"기본 매핑에 따른 라우팅: {intent} -> {target_domain}"
        }
    
    def _build_context_aware_routing_prompt(self, normalized_text: str, intent: str, slot: List[str], context: Dict[str, Any]) -> str:
        """컨텍스트를 고려한 라우팅 프롬프트 생성"""
        conversation_context = context.get("conversation_history", [])
        current_state = context.get("current_state", {})
        
        # 대화 컨텍스트 요약
        context_summary = self._summarize_conversation_context(conversation_context)
        
        # 현재 상태 정보
        current_state_info = self._format_current_state(current_state)
        
        # Get domains and intent-domain mapping from JSON configuration
        domains = self.config.get("domains", {})
        intent_domain_mapping = self.config.get("intent_domain_mapping", {})
        
        # Format domains list
        domains_list = []
        for domain_key, domain_desc in domains.items():
            domains_list.append(f"- {domain_key}: {domain_desc}")
        domains_list_text = "\n".join(domains_list)
        
        # Format intent-domain mapping list
        intent_domain_mapping_list = []
        for intent_key, domain_key in intent_domain_mapping.items():
            intent_domain_mapping_list.append(f"- {intent_key} -> {domain_key}")
        intent_domain_mapping_list_text = "\n".join(intent_domain_mapping_list)
        
        # Get prompt template from JSON configuration
        prompt_template = self.config.get("prompt_template", {})
        domain_routing_prompt_template = prompt_template.get("domain_routing_prompt", [])
        
        # Handle both string and array formats
        if isinstance(domain_routing_prompt_template, str):
            # If it's a string, format it directly
            prompt = domain_routing_prompt_template.format(
                normalized_text=normalized_text,
                intent=intent,
                slot=slot,
                context_summary=context_summary,
                current_state_info=current_state_info,
                intent_domain_mapping_list=intent_domain_mapping_list_text,
                domains_list=domains_list_text
            )
        elif isinstance(domain_routing_prompt_template, list):
            # If it's an array, join with newlines and then format
            prompt_lines = domain_routing_prompt_template
            prompt_text = "\n".join(prompt_lines)
            prompt = prompt_text.format(
                normalized_text=normalized_text,
                intent=intent,
                slot=slot,
                context_summary=context_summary,
                current_state_info=current_state_info,
                intent_domain_mapping_list=intent_domain_mapping_list_text,
                domains_list=domains_list_text
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
    
    async def handle_missing_input(self, missing_slots: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        """누락된 입력 처리"""
        # Get missing slots tools from JSON configuration
        missing_slots_tools = self.config.get("missing_slots_tools", {})
        
        available_tools = []
        for slot in missing_slots:
            tools = missing_slots_tools.get(slot, [])
            available_tools.extend(tools)
        
        if available_tools:
            # 도구를 통해 정보 추출 시도
            extracted_info = await self._extract_missing_info(available_tools, context)
            return {
                "status": "extracted",
                "missing_slots": missing_slots,
                "extracted_info": extracted_info
            }
        else:
            # 사용자에게 정보 요청
            return {
                "status": "need_user_input",
                "missing_slots": missing_slots,
                "message": f"다음 정보가 필요합니다: {', '.join(missing_slots)}"
            }
    
    async def _check_tool_availability(self, missing_slots: List[str]) -> List[str]:
        """도구 가용성 확인"""
        # Get missing slots tools from JSON configuration
        missing_slots_tools = self.config.get("missing_slots_tools", {})
        
        available_tools = []
        for slot in missing_slots:
            tools = missing_slots_tools.get(slot, [])
            available_tools.extend(tools)
        
        return list(set(available_tools))  # 중복 제거
    
    async def _extract_missing_info(self, tools: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        """누락된 정보 추출"""
        # 실제 구현에서는 도구를 호출하여 정보를 추출
        # 여기서는 기본 구현만 제공
        return {
            "extracted_slots": {},
            "tools_used": tools
        } 