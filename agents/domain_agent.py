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
        """도메인별 요청 처리 및 도구 선택"""
        normalized_text = input_data.get("normalized_text", "")
        intent = input_data.get("intent", "")
        slot = input_data.get("slot", [])
        target_domain = input_data.get("target_domain", "general")
        
        # 입력 데이터 로깅
        self.logger.info(f"=== {self.config.name} Input ===")
        self.logger.info(f"Normalized Text: {normalized_text}")
        self.logger.info(f"Intent: {intent}")
        self.logger.info(f"Slot: {slot}")
        self.logger.info(f"Target Domain: {target_domain}")
        
        # 컨텍스트 업데이트
        updated_context = self._update_context(context, input_data)
        
        # 도구 선택
        tool_selection = await self._select_tool(normalized_text, intent, slot, target_domain, updated_context)
        
        # 도구 실행 (실제로는 MCP 서버를 통해 실행)
        tool_result = await self._execute_tool(tool_selection, updated_context)
        
        result = {
            "tool_name": tool_selection.get("tool_name", ""),
            "tool_input": tool_selection.get("tool_input", {}),
            "tool_output": tool_result,
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
                "current_step": "domain",
                "status_history": [],
                "agent_call_history": [],
                "missing_slots": []
            }
        
        # 현재 상태 기록
        context["status_history"].append(f"domain_processing_{input_data.get('intent', 'unknown')}")
        context["agent_call_history"].append({
            "agent_name": self.config.name,
            "status": "processing"
        })
        
        return context
    
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
    
    def _default_tool_selection(self, intent: str, target_domain: str) -> Dict[str, Any]:
        """기본 도구 선택 로직"""
        tool_mapping = {
            "check_balance": "account_balance",
            "transfer_money": "transfer_money",
            "loan_inquiry": "loan_info",
            "investment_info": "investment_info",
            "account_info": "account_info"
        }
        
        tool_name = tool_mapping.get(intent, "general_inquiry")
        return {
            "tool_name": tool_name,
            "tool_input": {},
            "reasoning": f"Intent '{intent}' mapped to tool '{tool_name}'"
        }
    
    def _build_tool_selection_prompt(self, normalized_text: str, intent: str, slot: List[str], target_domain: str, context: Dict[str, Any]) -> str:
        """도구 선택 프롬프트 생성"""
        prompt = f"""
다음 사용자 요청을 처리하기 위한 적절한 도구를 선택하고 필요한 입력을 준비해주세요.

사용자 요청: {normalized_text}
의도: {intent}
필요한 정보: {slot}
대상 도메인: {target_domain}

사용 가능한 도구:
- account_balance: 계좌 잔액 조회
- transfer_money: 송금 처리
- loan_info: 대출 정보 조회
- investment_info: 투자 정보 조회
- account_info: 계좌 정보 조회
- general_inquiry: 일반 문의 처리

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
    
    async def _execute_tool(self, tool_selection: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """도구 실행 (실제로는 MCP 서버를 통해 실행)"""
        tool_name = tool_selection.get("tool_name", "")
        tool_input = tool_selection.get("tool_input", {})
        
        # 실제 구현에서는 MCP 서버를 통해 도구 실행
        # 여기서는 시뮬레이션된 결과 반환
        return await self._simulate_tool_execution(tool_name, tool_input, context)
    
    async def _simulate_tool_execution(self, tool_name: str, tool_input: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """도구 실행 시뮬레이션"""
        # 실제 구현에서는 MCP 서버를 통해 도구 실행
        simulation_results = {
            "account_balance": {
                "balance": "1,000,000원",
                "currency": "KRW",
                "last_updated": "2024-01-15 14:30:00"
            },
            "transfer_money": {
                "status": "success",
                "transaction_id": "TXN123456789",
                "amount": tool_input.get("amount", "0"),
                "recipient": tool_input.get("recipient", "")
            },
            "loan_info": {
                "available_loan_amount": "50,000,000원",
                "interest_rate": "3.5%",
                "loan_types": ["신용대출", "담보대출", "전세자금대출"]
            },
            "investment_info": {
                "products": ["정기예금", "펀드", "주식", "채권"],
                "current_rates": {"정기예금": "2.5%", "펀드": "5-8%"}
            },
            "account_info": {
                "account_number": "123-456-789",
                "account_type": "입출금통장",
                "opening_date": "2020-01-15"
            },
            "general_inquiry": {
                "response": "일반 문의에 대한 답변입니다.",
                "category": "general"
            }
        }
        
        return simulation_results.get(tool_name, {"error": "Unknown tool"}) 