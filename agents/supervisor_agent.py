import json
import asyncio
from typing import Dict, Any, Optional, List
from .base_agent import BaseAgent
from models.agent_config import get_agent_config
from config.config_loader import config_loader

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
            self.logger.error(f"Failed to parse routing decision from {self.config.name}")
            # 기본 라우팅 결정 - 컨텍스트를 고려한 개선된 결정
            return self._default_context_aware_routing(intent, context)
    
    def _default_context_aware_routing(self, intent: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """컨텍스트를 고려한 기본 라우팅 로직"""
        # Get intent to domain mapping from configuration
        domain_mapping = config_loader.get_intent_domain_mapping("supervisor_agent")
        context_settings = config_loader.get_context_settings()
        default_domain = context_settings.get("default_domain", "general")
        
        target_domain = domain_mapping.get(intent, default_domain)
        
        # 컨텍스트를 고려한 추가 분석
        reasoning = f"Intent '{intent}' mapped to domain '{target_domain}'"
        
        # 이전 대화에서 도메인 정보 추출
        conversation_context = context.get("conversation_history", [])
        if conversation_context:
            last_conversation = conversation_context[-1]
            extracted_info = last_conversation.get("extracted_info", {})
            last_tool = extracted_info.get("tool_name", "")
            
            if last_tool:
                reasoning += f" (previous tool: {last_tool})"
        
        return {
            "target_domain": target_domain,
            "reasoning": reasoning
        }
    
    def _build_context_aware_routing_prompt(self, normalized_text: str, intent: str, slot: List[str], context: Dict[str, Any]) -> str:
        """컨텍스트를 고려한 라우팅 프롬프트 생성"""
        conversation_context = context.get("conversation_history", [])
        current_state = context.get("current_state", {})
        
        # 대화 컨텍스트 요약
        context_summary = self._summarize_conversation_context(conversation_context)
        
        # 현재 상태 정보
        current_state_info = self._format_current_state(current_state)
        
        # Get domains from configuration
        domains = config_loader.get_banking_domains()
        domains_text = "\n".join([f"- {domain}: {description}" for domain, description in domains.items()])
        
        prompt = f"""
다음 사용자 요청을 분석하여 적절한 도메인으로 라우팅해주세요.

사용자 요청: {normalized_text}
의도: {intent}
필요한 정보: {slot}
대화 깊이: {context.get('depth', 0)}

대화 컨텍스트:
{context_summary}

현재 상태:
{current_state_info}

사용 가능한 도메인:
{domains_text}

다음 JSON 형식으로 응답해주세요:
{{
    "target_domain": "선택된_도메인",
    "reasoning": "라우팅 결정 이유 (컨텍스트 고려사항 포함)"
}}

라우팅 기준:
1. 의도(intent)를 우선적으로 고려
2. 필요한 정보(slot)를 고려
3. 대화 컨텍스트를 고려하여 일관성 유지
4. 이전 대화에서 사용된 도구와 도메인을 고려
5. 현재 상태 정보를 활용하여 개인화된 라우팅
6. 사용자 경험을 최적화

컨텍스트 활용 가이드:
1. 이전 대화에서 계좌 관련 작업이었다면 계좌 도메인 유지 고려
2. 투자 관련 대화가 이어졌다면 투자 도메인 유지 고려
3. 대출 관련 문의가 이어졌다면 대출 도메인 유지 고려
4. 새로운 주제로 전환되는 경우 적절한 도메인으로 라우팅
"""
        return prompt
    
    def _summarize_conversation_context(self, conversation_context: list) -> str:
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
        """입력 부족 상황 처리"""
        if self.config.fallback_strategy:
            strategy = self.config.fallback_strategy.missing_input
            
            if strategy.get("check_tool_availability", False):
                # 도구를 통해 정보 추출 가능한지 확인
                available_tools = await self._check_tool_availability(missing_slots)
                
                if available_tools and strategy.get("if_available") == "call_tool":
                    return await self._extract_missing_info(available_tools, context)
                else:
                    return {
                        "action": "ask_user",
                        "missing_slots": missing_slots,
                        "message": f"다음 정보가 필요합니다: {', '.join(missing_slots)}"
                    }
        
        return {
            "action": "ask_user",
            "missing_slots": missing_slots,
            "message": f"다음 정보가 필요합니다: {', '.join(missing_slots)}"
        }
    
    async def _check_tool_availability(self, missing_slots: List[str]) -> List[str]:
        """도구 가용성 확인 (실제 구현에서는 도구 레지스트리 확인)"""
        # 간단한 예시 - 실제로는 도구 레지스트리에서 확인
        available_tools = []
        for slot in missing_slots:
            if slot in ["account_number", "balance"]:
                available_tools.append("account_lookup")
            elif slot in ["recipient", "amount"]:
                available_tools.append("user_info_lookup")
        
        return available_tools
    
    async def _extract_missing_info(self, tools: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        """도구를 통한 정보 추출"""
        # 실제 구현에서는 도구 실행
        return {
            "action": "extract_info",
            "tools": tools,
            "context": context
        } 