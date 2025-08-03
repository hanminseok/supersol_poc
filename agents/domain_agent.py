import json
from typing import Dict, Any, Optional, List
from .base_agent import BaseAgent
from models.agent_config import get_agent_config
from config.config_loader import config_loader

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
            
            # 계좌 관련 슬롯이 없고 이전에 계좌가 언급되었다면 추가
            if not any("account" in s.lower() for s in enhanced_slot) and accounts_mentioned:
                enhanced_slot.extend([f"account_{i}" for i in range(len(accounts_mentioned))])
        
        # 현재 상태에서 선택된 계좌 정보 추가
        selected_account = current_state.get("selected_account")
        if selected_account and not any("account" in s.lower() for s in enhanced_slot):
            enhanced_slot.append("selected_account")
        
        # 이전 의도와 슬롯 정보 추가
        last_intent = current_state.get("last_intent")
        last_slots = current_state.get("last_slots", [])
        
        if last_intent and last_intent not in enhanced_slot:
            enhanced_slot.append(f"previous_intent_{last_intent}")
        
        for last_slot in last_slots:
            if last_slot not in enhanced_slot:
                enhanced_slot.append(f"previous_slot_{last_slot}")
        
        return enhanced_slot
    
    async def _select_tool(self, normalized_text: str, intent: str, slot: List[str], target_domain: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """적절한 도구 선택"""
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
            self.logger.error(f"Failed to parse tool selection from {self.config.name}")
            # 기본 도구 선택
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
            self.logger.error(f"Failed to parse tool selection from {self.config.name}")
            # 기본 도구 선택 - 컨텍스트를 고려한 개선된 선택
            return self._default_tool_selection_with_context(intent, target_domain, context)
    
    def _default_tool_selection(self, intent: str, target_domain: str) -> Dict[str, Any]:
        """기본 도구 선택 로직"""
        # Get intent to tool mapping from configuration
        tool_mapping = config_loader.get_intent_tool_mapping("domain_agent")
        context_settings = config_loader.get_context_settings()
        default_tool = context_settings.get("default_tool", "general_inquiry")
        
        tool_name = tool_mapping.get(intent, default_tool)
        return {
            "tool_name": tool_name,
            "tool_input": {},
            "reasoning": f"Intent '{intent}' mapped to tool '{tool_name}'"
        }
    
    def _default_tool_selection_with_context(self, intent: str, target_domain: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """컨텍스트를 고려한 기본 도구 선택 로직"""
        # Get intent to tool mapping from configuration
        tool_mapping = config_loader.get_intent_tool_mapping("domain_agent")
        context_settings = config_loader.get_context_settings()
        default_tool = context_settings.get("default_tool", "general_inquiry")
        
        tool_name = tool_mapping.get(intent, default_tool)
        
        # 컨텍스트에서 추가 정보 추출하여 도구 입력 보완
        tool_input = self._build_context_aware_tool_input(tool_name, context)
        
        return {
            "tool_name": tool_name,
            "tool_input": tool_input,
            "reasoning": f"Intent '{intent}' mapped to tool '{tool_name}' with context-aware input"
        }
    
    def _build_tool_selection_prompt(self, normalized_text: str, intent: str, slot: List[str], target_domain: str, context: Dict[str, Any]) -> str:
        """도구 선택 프롬프트 생성"""
        # Get tools from configuration
        tools = config_loader.get_tools("domain_agent")
        tools_text = "\n".join([f"- {tool}: {description}" for tool, description in tools.items()])
        
        prompt = f"""
다음 사용자 요청을 처리하기 위한 적절한 도구를 선택하고 필요한 입력을 준비해주세요.

사용자 요청: {normalized_text}
의도: {intent}
필요한 정보: {slot}
대상 도메인: {target_domain}

사용 가능한 도구:
{tools_text}

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
        
        prompt = f"""
다음 사용자 요청을 처리하기 위한 적절한 도구를 선택하고 필요한 입력을 준비해주세요.

사용자 요청: {normalized_text}
의도: {intent}
필요한 정보: {slot}
대상 도메인: {target_domain}

대화 컨텍스트:
{context_summary}

현재 상태:
- 선택된 계좌: {current_state.get('selected_account', '없음')}
- 이전 의도: {current_state.get('last_intent', '없음')}
- 이전 슬롯: {current_state.get('last_slots', [])}
- 대화 깊이: {context.get('depth', 0)}

사용 가능한 도구:
- account_balance: 계좌 잔액 조회
- transfer_money: 송금 처리
- loan_info: 대출 정보 조회
- investment_info: 투자 정보 조회
- account_info: 계좌 정보 조회
- transaction_history: 거래 내역 조회
- deposit_history: 입금 내역 조회
- auto_transfer_history: 자동이체 내역 조회
- minus_account_info: 마이너스 통장 정보 조회
- isa_account_info: ISA 계좌 정보 조회
- mortgage_rate_change: 주택담보대출 금리 변동 조회
- fund_info: 펀드 수익률 및 운용사 정보 조회
- hot_etf_info: 인기 ETF 정보 조회
- transfer_limit_change: 이체 한도 변경 기록 조회
- frequent_deposit_accounts: 자주 입금한 계좌 목록 조회
- loan_account_status: 대출 계좌 상태 조회
- general_inquiry: 일반 문의 처리

다음 JSON 형식으로 응답해주세요:
{{
    "tool_name": "선택된_도구_이름",
    "tool_input": {{
        "필요한_입력_필드": "값"
    }},
    "reasoning": "도구 선택 이유 (컨텍스트 고려사항 포함)"
}}

도구 선택 기준:
1. 의도(intent)와 가장 잘 매칭되는 도구 선택
2. 필요한 정보(slot)를 고려하여 입력 준비
3. 대화 컨텍스트를 고려하여 이전 정보 활용
4. 현재 상태 정보를 활용하여 개인화된 응답 제공
5. 도메인 특성에 맞는 도구 선택
6. 사용자 경험 최적화
"""
        return prompt
    
    def _summarize_conversation_context(self, conversation_context: List[Dict[str, Any]]) -> str:
        """대화 컨텍스트 요약"""
        if not conversation_context:
            return "이전 대화 없음"
        
        summary_parts = []
        
        # Get max conversation entries from configuration
        context_settings = config_loader.get_context_settings()
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
        """컨텍스트를 고려한 도구 입력 구성"""
        tool_input = {}
        current_state = context.get("current_state", {})
        conversation_context = context.get("conversation_history", [])
        
        # 계좌 관련 도구인 경우 선택된 계좌 정보 추가
        if "account" in tool_name:
            selected_account = current_state.get("selected_account")
            if selected_account:
                tool_input["account_number"] = selected_account
        
        # 이전 대화에서 계좌 정보 추출
        for entry in conversation_context:
            extracted_info = entry.get("extracted_info", {})
            accounts_mentioned = extracted_info.get("accounts_mentioned", [])
            if accounts_mentioned and "account_number" not in tool_input:
                tool_input["account_number"] = accounts_mentioned[0]
        
        # 송금 관련 도구인 경우 이전 대화에서 수신자 정보 추출
        if tool_name == "transfer_money":
            for entry in conversation_context:
                extracted_info = entry.get("extracted_info", {})
                # 수신자 정보 추출 로직 (실제 구현에서는 더 정교한 추출 필요)
                if "recipient" in extracted_info:
                    tool_input["recipient"] = extracted_info["recipient"]
        
        return tool_input
    
    async def _execute_tool(self, tool_selection: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """도구 실행 (실제로는 MCP 서버를 통해 실행)"""
        tool_name = tool_selection.get("tool_name", "")
        tool_input = tool_selection.get("tool_input", {})
        
        # 실제 구현에서는 MCP 서버를 통해 도구 실행
        # 여기서는 시뮬레이션된 결과 반환
        return await self._simulate_tool_execution(tool_name, tool_input, context)
    
    async def _simulate_tool_execution(self, tool_name: str, tool_input: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """도구 실행 시뮬레이션"""
        # Get sample response from configuration
        sample_response = config_loader.get_tool_sample_response(tool_name)
        
        if not sample_response:
            # If no sample response found, return default error response
            return config_loader.get_default_error_response()
        
        # For transfer_money tool, update amount and recipient from tool_input
        if tool_name == "transfer_money":
            sample_response["amount"] = tool_input.get("amount", "0")
            sample_response["recipient"] = tool_input.get("recipient", "")
        
        return sample_response 