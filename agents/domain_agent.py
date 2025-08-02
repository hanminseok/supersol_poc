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
        try:
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
            "account_info": "account_info",
            "transaction_history": "transaction_history",
            "deposit_history": "deposit_history",
            "auto_transfer_history": "auto_transfer_history",
            "minus_account_info": "minus_account_info",
            "isa_account_info": "isa_account_info",
            "mortgage_rate_change": "mortgage_rate_change",
            "fund_info": "fund_info",
            "hot_etf_info": "hot_etf_info",
            "transfer_limit_change": "transfer_limit_change",
            "frequent_deposit_accounts": "frequent_deposit_accounts",
            "loan_account_status": "loan_account_status"
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
            "transaction_history": {
                "transactions": [
                    {
                        "date": "2024-01-15",
                        "type": "입금",
                        "amount": "500,000원",
                        "sender": "김철수",
                        "description": "급여"
                    },
                    {
                        "date": "2024-01-14",
                        "type": "출금",
                        "amount": "100,000원",
                        "recipient": "ATM",
                        "description": "현금출금"
                    },
                    {
                        "date": "2024-01-13",
                        "type": "입금",
                        "amount": "200,000원",
                        "sender": "이영희",
                        "description": "환불"
                    }
                ],
                "total_count": 3
            },
            "deposit_history": {
                "deposits": [
                    {
                        "date": "2024-01-15",
                        "amount": "500,000원",
                        "sender": "김철수",
                        "sender_account": "123-456-001",
                        "description": "급여",
                        "time": "09:30:15"
                    },
                    {
                        "date": "2024-01-13",
                        "amount": "200,000원",
                        "sender": "이영희",
                        "sender_account": "987-654-321",
                        "description": "환불",
                        "time": "14:22:45"
                    },
                    {
                        "date": "2024-01-10",
                        "amount": "1,000,000원",
                        "sender": "박민수",
                        "sender_account": "111-222-333",
                        "description": "이체",
                        "time": "16:15:30"
                    }
                ],
                "total_count": 3,
                "total_amount": "1,700,000원"
            },
            "auto_transfer_history": {
                "auto_transfers": [
                    {
                        "date": "2024-01-15",
                        "type": "출금",
                        "amount": "50,000원",
                        "recipient": "카드값",
                        "description": "신용카드 자동이체",
                        "status": "완료"
                    },
                    {
                        "date": "2024-01-10",
                        "type": "출금",
                        "amount": "300,000원",
                        "recipient": "월세",
                        "description": "월세 자동이체",
                        "status": "완료"
                    },
                    {
                        "date": "2024-01-05",
                        "type": "출금",
                        "amount": "100,000원",
                        "recipient": "보험료",
                        "description": "생명보험 자동이체",
                        "status": "완료"
                    }
                ],
                "total_count": 3,
                "total_amount": "450,000원"
            },
            "minus_account_info": {
                "account_number": "123-456-789",
                "account_type": "마이너스 통장",
                "credit_limit": "10,000,000원",
                "used_amount": "3,500,000원",
                "remaining_limit": "6,500,000원",
                "interest_rate": "5.5%",
                "next_interest_date": "2024-02-15",
                "current_balance": "-3,500,000원"
            },
            "isa_account_info": {
                "account_number": "ISA-001-234",
                "account_type": "ISA 계좌",
                "total_balance": "15,000,000원",
                "invested_amount": "12,000,000원",
                "current_profit": "3,000,000원",
                "profit_rate": "25.0%",
                "annual_return": "8.5%",
                "investment_products": [
                    {
                        "name": "TIGER AI반도체 ETF",
                        "amount": "5,000,000원",
                        "profit": "1,200,000원",
                        "profit_rate": "31.6%"
                    },
                    {
                        "name": "미국 S&P 500 ETF",
                        "amount": "4,000,000원",
                        "profit": "800,000원",
                        "profit_rate": "25.0%"
                    },
                    {
                        "name": "한국 KOSPI ETF",
                        "amount": "3,000,000원",
                        "profit": "1,000,000원",
                        "profit_rate": "50.0%"
                    }
                ]
            },
            "mortgage_rate_change": {
                "loan_type": "주택담보대출",
                "current_rate": "3.8%",
                "previous_rate": "4.2%",
                "change_amount": "-0.4%",
                "change_date": "2024-01-10",
                "change_reason": "중앙은행 기준금리 인하",
                "rate_history": [
                    {
                        "date": "2024-01-10",
                        "rate": "3.8%",
                        "change": "-0.4%"
                    },
                    {
                        "date": "2023-12-15",
                        "rate": "4.2%",
                        "change": "+0.2%"
                    },
                    {
                        "date": "2023-11-20",
                        "rate": "4.0%",
                        "change": "+0.1%"
                    }
                ]
            },
            "fund_info": {
                "total_fund_count": 5,
                "total_investment": "25,000,000원",
                "total_profit": "2,500,000원",
                "average_profit_rate": "10.0%",
                "funds": [
                    {
                        "name": "미래에셋 글로벌 테크 펀드",
                        "company": "미래에셋자산운용",
                        "investment_amount": "8,000,000원",
                        "current_value": "9,200,000원",
                        "profit": "1,200,000원",
                        "profit_rate": "15.0%",
                        "risk_level": "중위험"
                    },
                    {
                        "name": "KB국민 글로벌 주식 펀드",
                        "company": "KB자산운용",
                        "investment_amount": "6,000,000원",
                        "current_value": "6,600,000원",
                        "profit": "600,000원",
                        "profit_rate": "10.0%",
                        "risk_level": "중위험"
                    },
                    {
                        "name": "신한 글로벌 채권 펀드",
                        "company": "신한자산운용",
                        "investment_amount": "5,000,000원",
                        "current_value": "5,250,000원",
                        "profit": "250,000원",
                        "profit_rate": "5.0%",
                        "risk_level": "저위험"
                    },
                    {
                        "name": "NH농협 글로벌 부동산 펀드",
                        "company": "NH투자증권",
                        "investment_amount": "4,000,000원",
                        "current_value": "4,400,000원",
                        "profit": "400,000원",
                        "profit_rate": "10.0%",
                        "risk_level": "중위험"
                    },
                    {
                        "name": "하나 글로벌 원자재 펀드",
                        "company": "하나자산운용",
                        "investment_amount": "2,000,000원",
                        "current_value": "2,050,000원",
                        "profit": "50,000원",
                        "profit_rate": "2.5%",
                        "risk_level": "고위험"
                    }
                ]
            },
            "hot_etf_info": {
                "market_trend": "AI 반도체 및 기술주 중심의 상승세",
                "top_etfs": [
                    {
                        "name": "TIGER AI반도체 ETF",
                        "ticker": "233740",
                        "current_price": "45,200원",
                        "daily_change": "+2.8%",
                        "monthly_return": "+15.3%",
                        "yearly_return": "+45.2%",
                        "volume": "높음",
                        "category": "AI/반도체"
                    },
                    {
                        "name": "KODEX 2차전지산업 ETF",
                        "ticker": "305720",
                        "current_price": "32,800원",
                        "daily_change": "+1.5%",
                        "monthly_return": "+8.7%",
                        "yearly_return": "+28.9%",
                        "volume": "높음",
                        "category": "2차전지"
                    },
                    {
                        "name": "TIGER 미국나스닥100 ETF",
                        "ticker": "233130",
                        "current_price": "28,500원",
                        "daily_change": "+1.2%",
                        "monthly_return": "+6.2%",
                        "yearly_return": "+22.1%",
                        "volume": "중간",
                        "category": "미국기술주"
                    },
                    {
                        "name": "KODEX 미국S&P500선물 ETF",
                        "ticker": "143850",
                        "current_price": "15,200원",
                        "daily_change": "+0.8%",
                        "monthly_return": "+4.1%",
                        "yearly_return": "+18.5%",
                        "volume": "높음",
                        "category": "미국주식"
                    },
                    {
                        "name": "TIGER 중국항셍테크 ETF",
                        "ticker": "305080",
                        "current_price": "12,800원",
                        "daily_change": "+3.2%",
                        "monthly_return": "+12.8%",
                        "yearly_return": "+35.6%",
                        "volume": "중간",
                        "category": "중국기술주"
                    }
                ]
            },
            "transfer_limit_change": {
                "current_limit": "10,000,000원",
                "limit_changes": [
                    {
                        "date": "2024-01-12",
                        "previous_limit": "5,000,000원",
                        "new_limit": "10,000,000원",
                        "change_amount": "+5,000,000원",
                        "reason": "고객 요청",
                        "status": "승인됨"
                    },
                    {
                        "date": "2023-12-20",
                        "previous_limit": "3,000,000원",
                        "new_limit": "5,000,000원",
                        "change_amount": "+2,000,000원",
                        "reason": "자동 한도 상향",
                        "status": "승인됨"
                    }
                ],
                "total_changes": 2
            },
            "frequent_deposit_accounts": {
                "frequent_accounts": [
                    {
                        "account_number": "123-456-001",
                        "account_holder": "김철수",
                        "bank_name": "신한은행",
                        "deposit_count": 15,
                        "total_amount": "7,500,000원",
                        "last_deposit_date": "2024-01-15",
                        "frequency": "매주"
                    },
                    {
                        "account_number": "987-654-321",
                        "account_holder": "이영희",
                        "bank_name": "국민은행",
                        "deposit_count": 8,
                        "total_amount": "2,400,000원",
                        "last_deposit_date": "2024-01-13",
                        "frequency": "월 2-3회"
                    },
                    {
                        "account_number": "111-222-333",
                        "account_holder": "박민수",
                        "bank_name": "우리은행",
                        "deposit_count": 5,
                        "total_amount": "5,000,000원",
                        "last_deposit_date": "2024-01-10",
                        "frequency": "월 1-2회"
                    },
                    {
                        "account_number": "555-666-777",
                        "account_holder": "최지영",
                        "bank_name": "하나은행",
                        "deposit_count": 3,
                        "total_amount": "900,000원",
                        "last_deposit_date": "2024-01-08",
                        "frequency": "월 1회"
                    }
                ],
                "total_accounts": 4
            },
            "loan_account_status": {
                "total_loan_accounts": 3,
                "active_accounts": 2,
                "closed_accounts": 1,
                "loan_accounts": [
                    {
                        "account_number": "LOAN-001-234",
                        "loan_type": "신용대출",
                        "status": "활성",
                        "balance": "15,000,000원",
                        "interest_rate": "4.2%",
                        "opening_date": "2023-06-15",
                        "closing_date": None
                    },
                    {
                        "account_number": "LOAN-002-345",
                        "loan_type": "담보대출",
                        "status": "활성",
                        "balance": "50,000,000원",
                        "interest_rate": "3.8%",
                        "opening_date": "2023-03-20",
                        "closing_date": None
                    },
                    {
                        "account_number": "LOAN-003-456",
                        "loan_type": "전세자금대출",
                        "status": "해지",
                        "balance": "0원",
                        "interest_rate": "3.5%",
                        "opening_date": "2022-09-10",
                        "closing_date": "2024-01-05"
                    }
                ]
            },
            "general_inquiry": {
                "response": "일반 문의에 대한 답변입니다.",
                "category": "general"
            }
        }
        
        return simulation_results.get(tool_name, {"error": "Unknown tool"}) 