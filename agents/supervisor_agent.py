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
        """질문 분석 및 도메인 라우팅"""
        normalized_text = input_data.get("normalized_text", "")
        intent = input_data.get("intent", "")
        slot = input_data.get("slot", [])
        
        # 입력 데이터 로깅
        self.logger.info(f"=== {self.config.name} Input ===")
        self.logger.info(f"Normalized Text: {normalized_text}")
        self.logger.info(f"Intent: {intent}")
        self.logger.info(f"Slot: {slot}")
        
        # 컨텍스트 업데이트
        updated_context = self._update_context(context, input_data)
        
        # 라우팅 결정
        routing_decision = await self._make_routing_decision(normalized_text, intent, slot, updated_context)
        
        result = {
            "target_domain": routing_decision.get("target_domain", "general"),
            "normalized_text": normalized_text,
            "intent": intent,
            "slot": slot,
            "context": updated_context
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
        
        # 현재 상태 기록
        context["status_history"].append(f"supervisor_processing_{input_data.get('intent', 'unknown')}")
        context["agent_call_history"].append({
            "agent_name": self.config.name,
            "status": "processing"
        })
        
        return context
    
    async def _make_routing_decision(self, normalized_text: str, intent: str, slot: List[str], context: Dict[str, Any]) -> Dict[str, Any]:
        """라우팅 결정"""
        prompt = self._build_routing_prompt(normalized_text, intent, slot, context)
        
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
            # 기본 라우팅 결정
            return self._default_routing(intent)
    
    def _default_routing(self, intent: str) -> Dict[str, Any]:
        """기본 라우팅 로직"""
        domain_mapping = {
            "check_balance": "account",
            "transfer_money": "banking",
            "loan_inquiry": "loan",
            "investment_info": "investment",
            "account_info": "account"
        }
        
        target_domain = domain_mapping.get(intent, "general")
        return {
            "target_domain": target_domain,
            "reasoning": f"Intent '{intent}' mapped to domain '{target_domain}'"
        }
    
    def _build_routing_prompt(self, normalized_text: str, intent: str, slot: List[str], context: Dict[str, Any]) -> str:
        """라우팅 프롬프트 생성"""
        prompt = f"""
다음 사용자 요청을 분석하여 적절한 도메인으로 라우팅해주세요.

사용자 요청: {normalized_text}
의도: {intent}
필요한 정보: {slot}
대화 깊이: {context.get('depth', 0)}

사용 가능한 도메인:
- banking: 일반 은행 서비스 (송금, 결제 등)
- account: 계좌 관련 서비스 (잔액 조회, 계좌 정보 등)
- loan: 대출 관련 서비스 (대출 문의, 대출 조건 등)
- investment: 투자 관련 서비스 (투자 상품 정보, 포트폴리오 등)
- general: 일반 문의 및 기타 서비스

다음 JSON 형식으로 응답해주세요:
{{
    "target_domain": "선택된_도메인",
    "reasoning": "라우팅 결정 이유"
}}

라우팅 기준:
1. 의도(intent)를 우선적으로 고려
2. 필요한 정보(slot)를 고려
3. 대화 맥락을 고려
4. 사용자 경험을 최적화
"""
        return prompt
    
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