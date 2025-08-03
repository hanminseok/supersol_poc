import json
from typing import Dict, Any, Optional, List
from .base_agent import BaseAgent
from models.agent_config import get_agent_config

class DomainAgent(BaseAgent):
    def __init__(self):
        config = get_agent_config("domain_agent")
        if not config:
            raise ValueError("Domain agent config not found")
        super().__init__(config)
    
    async def _process(self, input_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """도메인별 요청 처리 및 도구 선택 - 멀티턴 질의 지원"""
        try:
            normalized_text = input_data.get("normalized_text", "")
            intent = input_data.get("intent", "")
            slot = input_data.get("slot", [])
            target_domain = input_data.get("target_domain", "general")
            
            # 컨텍스트에서 추가 정보 추출
            conversation_context = input_data.get("conversation_context", [])
            current_state = input_data.get("current_state", {})
            
            # 입력 데이터 로깅
            self.logger.info(f"=== {self.config.name} Input ===")
            self.logger.info(f"Normalized Text: {normalized_text}")
            self.logger.info(f"Intent: {intent}")
            self.logger.info(f"Slot: {slot}")
            self.logger.info(f"Target Domain: {target_domain}")
            self.logger.info(f"Conversation Context: {len(conversation_context)} entries")
            self.logger.info(f"Current State: {current_state}")
            
            # 컨텍스트 업데이트
            updated_context = self._update_context(context, input_data)
            
            # 컨텍스트를 고려한 슬롯 보완
            enhanced_slot = self._enhance_slots_with_context(slot, conversation_context, current_state)
            
            # 도구 선택 - 컨텍스트를 고려한 개선된 선택
            tool_selection = await self._select_tool_with_context(
                normalized_text, intent, enhanced_slot, target_domain, updated_context
            )
            
            # 도구 실행 (실제로는 MCP 서버를 통해 실행)
            tool_result = await self._execute_tool(tool_selection, updated_context)
            
            result = {
                "tool_name": tool_selection.get("tool_name", ""),
                "tool_input": tool_selection.get("tool_input", {}),
                "tool_output": tool_result,
                "context": updated_context,
                "enhanced_slots": enhanced_slot
            }
            
            # 출력 데이터 로깅
            self.logger.info(f"=== {self.config.name} Output ===")
            self.logger.info(f"Result: {result}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Domain agent _process failed: {str(e)}")
            raise e
    
    def _prepare_next_agent_input(self, current_result: Dict[str, Any], original_input: Dict[str, Any]) -> Dict[str, Any]:
        """다음 Agent가 없으므로 빈 딕셔너리 반환 (워크플로우 종료)"""
        return {}
    
    def _update_context(self, context: Optional[Dict[str, Any]], input_data: Dict[str, Any]) -> Dict[str, Any]:
        """컨텍스트 업데이트"""
        if context is None:
            context = {
                "session_id": "",
                "depth": 0,
                "current_step": "domain",
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
        context["status_history"].append(f"domain_processing_{input_data.get('intent', 'unknown')}")
        context["agent_call_history"].append({
            "agent_name": self.config.name,
            "status": "processing"
        })
        
        return context
    
    def _enhance_slots_with_context(self, slot: List[str], conversation_context: List[Dict[str, Any]], current_state: Dict[str, Any]) -> List[str]:
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
    
    async def _select_tool(self, normalized_text: str, intent: str, slot: List[str], target_domain: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """도구 선택"""
        prompt = self._build_tool_selection_prompt(normalized_text, intent, slot, target_domain, context)
        
        messages = [
            self._create_system_message(),
            self._create_user_message(prompt)
        ]
        
        response = await self._call_llm(messages)
        
        try:
            result = json.loads(response)
            return {
                "tool_name": result.get("tool_name", ""),
                "tool_input": result.get("tool_input", {}),
                "reasoning": result.get("reasoning", "")
            }
        except json.JSONDecodeError:
            self.logger.error(f"Failed to parse tool selection response from {self.config.name}")
            return self._default_tool_selection(intent, target_domain)
    
    async def _select_tool_with_context(self, normalized_text: str, intent: str, slot: List[str], target_domain: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """컨텍스트를 고려한 도구 선택"""
        prompt = self._build_context_aware_tool_selection_prompt(normalized_text, intent, slot, target_domain, context)
        
        messages = [
            self._create_system_message(),
            self._create_user_message(prompt)
        ]
        
        response = await self._call_llm(messages)
        
        try:
            result = json.loads(response)
            return {
                "tool_name": result.get("tool_name", ""),
                "tool_input": result.get("tool_input", {}),
                "reasoning": result.get("reasoning", "")
            }
        except json.JSONDecodeError:
            self.logger.error(f"Failed to parse context-aware tool selection response from {self.config.name}")
            return self._default_tool_selection_with_context(intent, target_domain, context)
    
    def _default_tool_selection(self, intent: str, target_domain: str) -> Dict[str, Any]:
        """기본 도구 선택"""
        # Get intent-tool mapping from JSON configuration
        intent_tool_mapping = self.config.get("intent_tool_mapping", {})
        default_tool = self.config.get("default_tool", "general_inquiry")
        
        tool_name = intent_tool_mapping.get(intent, default_tool)
        
        return {
            "tool_name": tool_name,
            "tool_input": {},
            "reasoning": f"기본 매핑에 따른 도구 선택: {intent} -> {tool_name}"
        }
    
    def _default_tool_selection_with_context(self, intent: str, target_domain: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """컨텍스트를 고려한 기본 도구 선택"""
        base_selection = self._default_tool_selection(intent, target_domain)
        
        # 컨텍스트에서 추가 정보 추출하여 tool_input 보완
        current_state = context.get("current_state", {})
        selected_account = current_state.get("selected_account")
        
        if selected_account and base_selection["tool_name"] in ["account_balance", "account_info"]:
            base_selection["tool_input"]["account_number"] = selected_account
        
        return base_selection
    
    def _build_tool_selection_prompt(self, normalized_text: str, intent: str, slot: List[str], target_domain: str, context: Dict[str, Any]) -> str:
        """도구 선택 프롬프트 생성"""
        # Get tools from JSON configuration
        tools = self.config.get("tools", {})
        
        # Format tools list
        tools_list = []
        for tool_key, tool_desc in tools.items():
            tools_list.append(f"- {tool_key}: {tool_desc}")
        tools_list_text = "\n".join(tools_list)
        
        prompt = f"""
다음 사용자 요청을 처리하기 위한 적절한 도구를 선택하고 필요한 입력을 준비해주세요.

사용자 요청: {normalized_text}
의도: {intent}
필요한 정보: {slot}
대상 도메인: {target_domain}

사용 가능한 도구:
{tools_list_text}

다음 JSON 형식으로 응답해주세요:
{{
    "tool_name": "선택된_도구_이름",
    "tool_input": {{
        "필요한_입력_필드": "값"
    }},
    "reasoning": "도구 선택 이유"
}}

도구 선택 기준:
1. 의도(intent)와 가장 잘 매칭되는 도구 선택
2. 필요한 정보(slot)를 고려하여 입력 준비
3. 도메인 특성에 맞는 도구 선택
4. 사용자 경험 최적화
"""
        return prompt
    
    def _build_context_aware_tool_selection_prompt(self, normalized_text: str, intent: str, slot: List[str], target_domain: str, context: Dict[str, Any]) -> str:
        """컨텍스트를 고려한 도구 선택 프롬프트 생성"""
        current_state = context.get("current_state", {})
        conversation_context = context.get("conversation_history", [])
        
        # 대화 컨텍스트 요약
        context_summary = self._summarize_conversation_context(conversation_context)
        
        # Get tools and intent-tool mapping from JSON configuration
        tools = self.config.get("tools", {})
        intent_tool_mapping = self.config.get("intent_tool_mapping", {})
        
        # Format tools list
        tools_list = []
        for tool_key, tool_desc in tools.items():
            tools_list.append(f"- {tool_key}: {tool_desc}")
        tools_list_text = "\n".join(tools_list)
        
        # Format intent-tool mapping list
        intent_tool_mapping_list = []
        for intent_key, tool_key in intent_tool_mapping.items():
            intent_tool_mapping_list.append(f"- {intent_key} -> {tool_key}")
        intent_tool_mapping_list_text = "\n".join(intent_tool_mapping_list)
        
        # Get prompt template from JSON configuration
        prompt_template = self.config.get("prompt_template", {})
        tool_selection_prompt_template = prompt_template.get("tool_selection_prompt", [])
        
        # Handle both string and array formats
        if isinstance(tool_selection_prompt_template, str):
            # If it's a string, format it directly
            prompt = tool_selection_prompt_template.format(
                normalized_text=normalized_text,
                intent=intent,
                slot=slot,
                target_domain=target_domain,
                context_summary=context_summary,
                current_state_info=f"- 선택된 계좌: {current_state.get('selected_account', '없음')}\n- 이전 의도: {current_state.get('last_intent', '없음')}\n- 이전 슬롯: {current_state.get('last_slots', [])}\n- 대화 깊이: {context.get('depth', 0)}",
                intent_tool_mapping_list=intent_tool_mapping_list_text,
                tools_list=tools_list_text
            )
        elif isinstance(tool_selection_prompt_template, list):
            # If it's an array, join with newlines and then format
            prompt_lines = tool_selection_prompt_template
            prompt_text = "\n".join(prompt_lines)
            prompt = prompt_text.format(
                normalized_text=normalized_text,
                intent=intent,
                slot=slot,
                target_domain=target_domain,
                context_summary=context_summary,
                current_state_info=f"- 선택된 계좌: {current_state.get('selected_account', '없음')}\n- 이전 의도: {current_state.get('last_intent', '없음')}\n- 이전 슬롯: {current_state.get('last_slots', [])}\n- 대화 깊이: {context.get('depth', 0)}",
                intent_tool_mapping_list=intent_tool_mapping_list_text,
                tools_list=tools_list_text
            )
        else:
            # Fallback to empty string
            prompt = ""
        
        return prompt
    
    def _summarize_conversation_context(self, conversation_context: List[Dict[str, Any]]) -> str:
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
    
    def _build_context_aware_tool_input(self, tool_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """컨텍스트를 고려한 도구 입력 생성"""
        tool_input = {}
        
        # 현재 상태에서 계좌 정보 추출
        current_state = context.get("current_state", {})
        selected_account = current_state.get("selected_account")
        
        if selected_account and tool_name in ["account_balance", "account_info", "transaction_history"]:
            tool_input["account_number"] = selected_account
        
        # 이전 대화에서 계좌 정보 추출
        conversation_context = context.get("conversation_history", [])
        for entry in conversation_context:
            extracted_info = entry.get("extracted_info", {})
            accounts_mentioned = extracted_info.get("accounts_mentioned", [])
            
            if accounts_mentioned and "account_number" not in tool_input:
                tool_input["account_number"] = accounts_mentioned[0]
        
        return tool_input
    
    async def _execute_tool(self, tool_selection: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """도구 실행"""
        tool_name = tool_selection.get("tool_name", "")
        tool_input = tool_selection.get("tool_input", {})
        
        # 실제 구현에서는 MCP 서버를 통해 도구 실행
        # 여기서는 시뮬레이션
        return await self._simulate_tool_execution(tool_name, tool_input, context)
    
    async def _simulate_tool_execution(self, tool_name: str, tool_input: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """도구 실행 시뮬레이션"""
        # 실제 구현에서는 MCP 서버를 통해 도구 실행
        # 여기서는 기본 응답만 반환
        return {
            "status": "success",
            "tool_name": tool_name,
            "result": f"{tool_name} 실행 결과 (시뮬레이션)",
            "timestamp": "2024-01-15 14:30:00"
        } 