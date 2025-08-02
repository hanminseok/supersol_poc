import asyncio
import json
from typing import Dict, Any, Optional, AsyncGenerator
from agents import RewritingAgent, PreprocessingAgent, SupervisorAgent, DomainAgent
from services.session_manager import SessionManager
from utils.logger import service_logger, agent_logger

class ChatService:
    def __init__(self):
        self.session_manager = SessionManager()
        self.rewriting_agent = RewritingAgent()
        self.preprocessing_agent = PreprocessingAgent()
        self.supervisor_agent = SupervisorAgent()
        self.domain_agent = DomainAgent()
        self.logger = service_logger
    
    async def process_chat(self, session_id: str, user_query: str, customer_info: Optional[Dict[str, Any]] = None) -> AsyncGenerator[str, None]:
        """채팅 처리 메인 메서드"""
        try:
            # 세션 확인/생성
            session_data = await self.session_manager.load_session(session_id)
            if not session_data:
                await self.session_manager.create_session(session_id, customer_info)
            
            # 대화 내역 로드
            conversation_history = await self.session_manager.get_conversation_history(session_id, limit=10)
            
            # Agent I/O 로그 초기화
            agent_log = []
            
            # 1. Rewriting Agent
            rewriting_result = await self._execute_rewriting_agent(user_query, conversation_history, customer_info)
            agent_log.append(f"Rewriting Agent Input: {json.dumps({'query': user_query, 'conversation_history': conversation_history, 'customer_info': customer_info}, ensure_ascii=False)}")
            agent_log.append(f"Rewriting Agent Output: {json.dumps(rewriting_result, ensure_ascii=False)}")
            
            # 2. Preprocessing Agent
            preprocessing_result = await self._execute_preprocessing_agent(rewriting_result, customer_info)
            agent_log.append(f"Preprocessing Agent Input: {json.dumps({'rewriting_result': rewriting_result, 'customer_info': customer_info}, ensure_ascii=False)}")
            agent_log.append(f"Preprocessing Agent Output: {json.dumps(preprocessing_result, ensure_ascii=False)}")
            
            # 3. Supervisor Agent
            supervisor_result = await self._execute_supervisor_agent(preprocessing_result, customer_info)
            agent_log.append(f"Supervisor Agent Input: {json.dumps({'preprocessing_result': preprocessing_result, 'customer_info': customer_info}, ensure_ascii=False)}")
            agent_log.append(f"Supervisor Agent Output: {json.dumps(supervisor_result, ensure_ascii=False)}")
            
            # 4. Domain Agent
            domain_result = await self._execute_domain_agent(supervisor_result, customer_info)
            agent_log.append(f"Domain Agent Input: {json.dumps({'supervisor_result': supervisor_result, 'customer_info': customer_info}, ensure_ascii=False)}")
            agent_log.append(f"Domain Agent Output: {json.dumps(domain_result, ensure_ascii=False)}")
            
            # 5. 최종 응답 생성
            final_response = await self._generate_final_response(domain_result, user_query, customer_info)
            
            # 응답 스트리밍
            async for chunk in self._stream_response(final_response):
                yield json.dumps({'type': 'response', 'content': chunk}, ensure_ascii=False)
            
            # 대화 내역 저장
            agent_log_text = "\n".join(agent_log)
            await self.session_manager.save_conversation(session_id, user_query, final_response, agent_log_text)
            
            yield json.dumps({'type': 'complete'}, ensure_ascii=False)
            
        except Exception as e:
            self.logger.error(f"Chat processing failed: {str(e)}")
            error_response = f"죄송합니다. 처리 중 오류가 발생했습니다: {str(e)}"
            yield json.dumps({'type': 'error', 'content': error_response}, ensure_ascii=False)
    
    async def _execute_rewriting_agent(self, user_query: str, conversation_history: list, customer_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Rewriting Agent 실행"""
        # 대화 내역을 쿼리 형태로 변환
        query_context = []
        for entry in conversation_history[-5:]:  # 최근 5개 대화만 사용
            query_context.append(entry.get("user_query", ""))
        
        # 컨텍스트 구성
        context = {
            "session_id": "test_session",  # 실제로는 세션 ID 사용
            "depth": 0,
            "current_step": "rewriting",
            "conversation_history": conversation_history[-5:],
            "customer_info": customer_info
        }
        
        input_data = {
            "query": query_context + [user_query],
            "customer_info": customer_info
        }
        
        return await self.rewriting_agent.execute(input_data, context)
    
    async def _execute_preprocessing_agent(self, rewriting_result: Dict[str, Any], customer_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Preprocessing Agent 실행"""
        # 컨텍스트 구성
        context = {
            "session_id": "test_session",
            "depth": 1,
            "current_step": "preprocessing",
            "rewriting_result": rewriting_result,
            "customer_info": customer_info
        }
        
        input_data = {
            "rewritten_text": rewriting_result.get("rewritten_text", ""),
            "topic": rewriting_result.get("topic", ""),
            "customer_info": customer_info
        }
        
        return await self.preprocessing_agent.execute(input_data, context)
    
    async def _execute_supervisor_agent(self, preprocessing_result: Dict[str, Any], customer_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Supervisor Agent 실행"""
        # 컨텍스트 구성
        context = {
            "session_id": "test_session",
            "depth": 2,
            "current_step": "supervisor",
            "preprocessing_result": preprocessing_result,
            "customer_info": customer_info
        }
        
        input_data = {
            "normalized_text": preprocessing_result.get("normalized_text", ""),
            "intent": preprocessing_result.get("intent", ""),
            "slot": preprocessing_result.get("slot", []),
            "customer_info": customer_info
        }
        
        return await self.supervisor_agent.execute(input_data, context)
    
    async def _execute_domain_agent(self, supervisor_result: Dict[str, Any], customer_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Domain Agent 실행"""
        # 컨텍스트 구성
        context = {
            "session_id": "test_session",
            "depth": 3,
            "current_step": "domain",
            "supervisor_result": supervisor_result,
            "customer_info": customer_info
        }
        
        input_data = {
            "normalized_text": supervisor_result.get("normalized_text", ""),
            "intent": supervisor_result.get("intent", ""),
            "slot": supervisor_result.get("slot", []),
            "target_domain": supervisor_result.get("target_domain", "general"),
            "customer_info": customer_info
        }
        
        return await self.domain_agent.execute(input_data, context)
    
    async def _generate_final_response(self, domain_result: Dict[str, Any], original_query: str, customer_info: Optional[Dict[str, Any]] = None) -> str:
        """최종 응답 생성"""
        tool_output = domain_result.get("tool_output", {})
        tool_name = domain_result.get("tool_name", "")
        
        # 고객 정보가 있는 경우 개인화된 응답 생성
        customer_name = customer_info.get("name", "고객") if customer_info else "고객"
        
        # 도구 결과에 따른 응답 생성
        if tool_name == "account_balance":
            balance = tool_output.get("balance", "알 수 없음")
            if customer_info:
                return f"{customer_name}님, 현재 계좌 잔액은 {balance}원입니다."
            else:
                return f"현재 계좌 잔액은 {balance}원입니다."
        
        elif tool_name == "transfer_money":
            status = tool_output.get("status", "실패")
            if status == "success":
                amount = tool_output.get("amount", "0")
                recipient = tool_output.get("recipient", "")
                if customer_info:
                    return f"{customer_name}님, {recipient}에게 {amount}원 송금이 완료되었습니다."
                else:
                    return f"{recipient}에게 {amount}원 송금이 완료되었습니다."
            else:
                return "송금 처리 중 오류가 발생했습니다."
        
        elif tool_name == "loan_info":
            available_amount = tool_output.get("available_loan_amount", "알 수 없음")
            interest_rate = tool_output.get("interest_rate", "알 수 없음")
            if customer_info:
                return f"{customer_name}님, 대출 가능 금액은 {available_amount}원이며, 현재 이자율은 {interest_rate}%입니다."
            else:
                return f"대출 가능 금액은 {available_amount}원이며, 현재 이자율은 {interest_rate}%입니다."
        
        elif tool_name == "investment_info":
            products = tool_output.get("products", [])
            rates = tool_output.get("current_rates", {})
            if customer_info:
                return f"{customer_name}님, 투자 가능한 상품: {', '.join(products)}. 현재 금리: {rates}"
            else:
                return f"투자 가능한 상품: {', '.join(products)}. 현재 금리: {rates}"
        
        elif tool_name == "account_info":
            account_number = tool_output.get("account_number", "알 수 없음")
            account_type = tool_output.get("account_type", "알 수 없음")
            if customer_info:
                return f"{customer_name}님, 계좌번호: {account_number}, 계좌종류: {account_type}"
            else:
                return f"계좌번호: {account_number}, 계좌종류: {account_type}"
        
        elif tool_name == "transaction_history":
            transactions = tool_output.get("transactions", [])
            if not transactions:
                return "최근 거래 내역이 없습니다."
            
            response = "최근 거래 내역입니다:\n"
            for i, tx in enumerate(transactions[:5], 1):  # 최근 5개만 표시
                response += f"{i}. {tx['date']} - {tx['type']}: {tx['amount']} ({tx.get('sender', tx.get('recipient', 'N/A'))})\n"
            
            if customer_info:
                return f"{customer_name}님, {response}"
            else:
                return response
        
        elif tool_name == "loan_account_status":
            total_loan_accounts = tool_output.get("total_loan_accounts", 0)
            active_accounts = tool_output.get("active_accounts", 0)
            closed_accounts = tool_output.get("closed_accounts", 0)
            loan_accounts = tool_output.get("loan_accounts", [])
            
            response = f"대출 계좌 현황입니다:\n"
            response += f"총 대출 계좌 수: {total_loan_accounts}개\n"
            response += f"활성 계좌: {active_accounts}개\n"
            response += f"해지된 계좌: {closed_accounts}개\n\n"
            
            if loan_accounts:
                response += "대출 계좌 상세 정보:\n"
                for i, account in enumerate(loan_accounts, 1):
                    response += f"{i}. {account['loan_type']} ({account['account_number']})\n"
                    response += f"   상태: {account['status']}\n"
                    response += f"   잔액: {account['balance']}\n"
                    response += f"   이자율: {account['interest_rate']}\n"
                    response += f"   개설일: {account['opening_date']}\n"
                    if account['closing_date']:
                        response += f"   해지일: {account['closing_date']}\n"
                    response += "\n"
            
            if customer_info:
                return f"{customer_name}님, {response}"
            else:
                return response
        
        elif tool_name == "frequent_deposit_accounts":
            frequent_accounts = tool_output.get("frequent_accounts", [])
            total_accounts = tool_output.get("total_accounts", 0)
            
            response = f"최근에 자주 입금한 계좌 목록입니다:\n"
            response += f"총 계좌 수: {total_accounts}개\n\n"
            
            if frequent_accounts:
                for i, account in enumerate(frequent_accounts, 1):
                    response += f"{i}. {account['account_holder']} ({account['bank_name']})\n"
                    response += f"   계좌번호: {account['account_number']}\n"
                    response += f"   입금 횟수: {account['deposit_count']}회\n"
                    response += f"   총 입금액: {account['total_amount']}\n"
                    response += f"   입금 빈도: {account['frequency']}\n"
                    response += f"   최근 입금일: {account['last_deposit_date']}\n\n"
            else:
                response += "자주 입금한 계좌가 없습니다."
            
            if customer_info:
                return f"{customer_name}님, {response}"
            else:
                return response
        
        elif tool_name == "transfer_limit_change":
            current_limit = tool_output.get("current_limit", "알 수 없음")
            limit_changes = tool_output.get("limit_changes", [])
            total_changes = tool_output.get("total_changes", 0)
            
            response = f"이체 한도 변경 기록입니다:\n"
            response += f"현재 이체 한도: {current_limit}\n"
            response += f"총 변경 횟수: {total_changes}회\n\n"
            
            if limit_changes:
                response += "변경 내역:\n"
                for i, change in enumerate(limit_changes, 1):
                    response += f"{i}. {change['date']}\n"
                    response += f"   이전 한도: {change['previous_limit']}\n"
                    response += f"   변경 후 한도: {change['new_limit']}\n"
                    response += f"   변경 금액: {change['change_amount']}\n"
                    response += f"   변경 사유: {change['reason']}\n"
                    response += f"   상태: {change['status']}\n\n"
            else:
                response += "이번 달 이체 한도 변경 기록이 없습니다."
            
            if customer_info:
                return f"{customer_name}님, {response}"
            else:
                return response
        
        elif tool_name == "hot_etf_info":
            market_trend = tool_output.get("market_trend", "알 수 없음")
            top_etfs = tool_output.get("top_etfs", [])
            
            response = f"현재 시장 동향: {market_trend}\n\n"
            response += "인기 ETF TOP 5:\n"
            
            if top_etfs:
                for i, etf in enumerate(top_etfs, 1):
                    response += f"{i}. {etf['name']} ({etf['ticker']})\n"
                    response += f"   현재가: {etf['current_price']}\n"
                    response += f"   일간변동: {etf['daily_change']}\n"
                    response += f"   월간수익률: {etf['monthly_return']}\n"
                    response += f"   연간수익률: {etf['yearly_return']}\n"
                    response += f"   거래량: {etf['volume']}\n"
                    response += f"   카테고리: {etf['category']}\n\n"
            
            if customer_info:
                return f"{customer_name}님, {response}"
            else:
                return response
        
        elif tool_name == "fund_info":
            total_fund_count = tool_output.get("total_fund_count", 0)
            total_investment = tool_output.get("total_investment", "알 수 없음")
            total_profit = tool_output.get("total_profit", "알 수 없음")
            average_profit_rate = tool_output.get("average_profit_rate", "알 수 없음")
            funds = tool_output.get("funds", [])
            
            response = f"펀드 투자 현황입니다:\n"
            response += f"보유 펀드 수: {total_fund_count}개\n"
            response += f"총 투자금액: {total_investment}\n"
            response += f"총 수익: {total_profit}\n"
            response += f"평균 수익률: {average_profit_rate}\n\n"
            
            if funds:
                response += "펀드별 상세 정보:\n"
                for i, fund in enumerate(funds, 1):
                    response += f"{i}. {fund['name']}\n"
                    response += f"   운용사: {fund['company']}\n"
                    response += f"   투자금액: {fund['investment_amount']}\n"
                    response += f"   현재가치: {fund['current_value']}\n"
                    response += f"   수익: {fund['profit']} ({fund['profit_rate']})\n"
                    response += f"   위험도: {fund['risk_level']}\n\n"
            
            if customer_info:
                return f"{customer_name}님, {response}"
            else:
                return response
        
        elif tool_name == "mortgage_rate_change":
            loan_type = tool_output.get("loan_type", "주택담보대출")
            current_rate = tool_output.get("current_rate", "알 수 없음")
            previous_rate = tool_output.get("previous_rate", "알 수 없음")
            change_amount = tool_output.get("change_amount", "알 수 없음")
            change_date = tool_output.get("change_date", "알 수 없음")
            change_reason = tool_output.get("change_reason", "알 수 없음")
            rate_history = tool_output.get("rate_history", [])
            
            response = f"{loan_type} 금리 변동 정보입니다:\n"
            response += f"현재 금리: {current_rate}\n"
            response += f"이전 금리: {previous_rate}\n"
            response += f"변동폭: {change_amount}\n"
            response += f"변동일: {change_date}\n"
            response += f"변동 사유: {change_reason}\n\n"
            
            if rate_history:
                response += "최근 금리 변동 이력:\n"
                for i, history in enumerate(rate_history[:3], 1):  # 최근 3개만 표시
                    response += f"{i}. {history['date']}: {history['rate']} ({history['change']})\n"
            
            if customer_info:
                return f"{customer_name}님, {response}"
            else:
                return response
        
        elif tool_name == "isa_account_info":
            total_balance = tool_output.get("total_balance", "알 수 없음")
            current_profit = tool_output.get("current_profit", "알 수 없음")
            profit_rate = tool_output.get("profit_rate", "알 수 없음")
            annual_return = tool_output.get("annual_return", "알 수 없음")
            investment_products = tool_output.get("investment_products", [])
            
            response = f"ISA 계좌 수익 정보입니다:\n"
            response += f"총 계좌 잔액: {total_balance}\n"
            response += f"현재 수익: {current_profit}\n"
            response += f"수익률: {profit_rate}\n"
            response += f"연간 수익률: {annual_return}\n\n"
            
            if investment_products:
                response += "투자 상품별 수익:\n"
                for i, product in enumerate(investment_products[:3], 1):  # 상위 3개만 표시
                    response += f"{i}. {product['name']}: {product['profit']} ({product['profit_rate']})\n"
            
            if customer_info:
                return f"{customer_name}님, {response}"
            else:
                return response
        
        elif tool_name == "minus_account_info":
            account_number = tool_output.get("account_number", "알 수 없음")
            remaining_limit = tool_output.get("remaining_limit", "알 수 없음")
            next_interest_date = tool_output.get("next_interest_date", "알 수 없음")
            interest_rate = tool_output.get("interest_rate", "알 수 없음")
            current_balance = tool_output.get("current_balance", "알 수 없음")
            
            response = f"마이너스 통장 정보입니다:\n"
            response += f"계좌번호: {account_number}\n"
            response += f"현재 잔액: {current_balance}\n"
            response += f"남은 한도: {remaining_limit}\n"
            response += f"이자율: {interest_rate}\n"
            response += f"다음 이자 납입일: {next_interest_date}"
            
            if customer_info:
                return f"{customer_name}님, {response}"
            else:
                return response
        
        elif tool_name == "auto_transfer_history":
            auto_transfers = tool_output.get("auto_transfers", [])
            if not auto_transfers:
                return "이번 달 자동이체 내역이 없습니다."
            
            response = "이번 달 자동이체 내역입니다:\n"
            for i, transfer in enumerate(auto_transfers[:5], 1):  # 최근 5개만 표시
                response += f"{i}. {transfer['date']} - {transfer['description']}: {transfer['amount']} ({transfer['recipient']})\n"
            
            total_amount = tool_output.get("total_amount", "0원")
            response += f"\n총 자동이체 금액: {total_amount}"
            
            if customer_info:
                return f"{customer_name}님, {response}"
            else:
                return response
        
        elif tool_name == "deposit_history":
            deposits = tool_output.get("deposits", [])
            if not deposits:
                return "최근 입금 내역이 없습니다."
            
            response = "최근 입금 내역입니다:\n"
            for i, deposit in enumerate(deposits[:5], 1):  # 최근 5개만 표시
                response += f"{i}. {deposit['date']} {deposit['time']} - {deposit['amount']} (송금자: {deposit['sender']}, 계좌: {deposit['sender_account']})\n"
            
            total_amount = tool_output.get("total_amount", "0원")
            response += f"\n총 입금액: {total_amount}"
            
            if customer_info:
                return f"{customer_name}님, {response}"
            else:
                return response
        
        else:
            # 일반 문의에 대한 응답
            response = tool_output.get("response", "죄송합니다. 해당 문의에 대한 답변을 준비 중입니다.")
            if customer_info and "고객" in response:
                response = response.replace("고객", customer_name)
            return response
    
    async def _stream_response(self, response: str) -> AsyncGenerator[str, None]:
        """응답 스트리밍"""
        # 문자별로 스트리밍하여 자연스러운 타이핑 효과 구현
        for char in response:
            yield char
            await asyncio.sleep(0.03)  # 빠른 타이핑 효과
    
    async def get_session_list(self) -> list:
        """세션 목록 조회"""
        return await self.session_manager.list_sessions()
    
    async def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """세션 정보 조회"""
        return await self.session_manager.get_session_info(session_id)
    
    async def delete_session(self, session_id: str) -> bool:
        """세션 삭제"""
        return await self.session_manager.delete_session(session_id) 