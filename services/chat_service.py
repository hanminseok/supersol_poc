import asyncio
import json
import os
from typing import Dict, Any, Optional, AsyncGenerator
from agents import RewritingAgent, PreprocessingAgent, SupervisorAgent, DomainAgent
from services.session_manager import SessionManager
from utils.logger import service_logger, agent_logger
from datetime import datetime

class ChatService:
    def __init__(self):
        self.session_manager = SessionManager()
        self.rewriting_agent = RewritingAgent()
        self.preprocessing_agent = PreprocessingAgent()
        self.supervisor_agent = SupervisorAgent()
        self.domain_agent = DomainAgent()
        self.logger = service_logger
    
    async def process_chat(self, session_id: str, user_query: str, customer_info: Optional[Dict[str, Any]] = None) -> AsyncGenerator[str, None]:
        """채팅 처리 메인 메서드 - 멀티턴 질의 지원 및 에러 복구"""
        # 초기 상태 백업
        initial_context = None
        try:
            # 세션 확인/생성
            session_data = await self.session_manager.load_session(session_id)
            if not session_data:
                await self.session_manager.create_session(session_id, customer_info)
            
            # 대화 내역 로드
            conversation_history = await self.session_manager.get_conversation_history(session_id, limit=10)
            
            # 통합 컨텍스트 생성
            context = await self._create_integrated_context(
                session_id=session_id,
                conversation_history=conversation_history,
                customer_info=customer_info
            )
            
            # 초기 상태 백업 (에러 복구용)
            initial_context = context.copy()
            
            # Agent I/O 로그 초기화
            agent_log = []
            
            # 1. Rewriting Agent - 대화 내역을 고려한 재작성
            try:
                rewriting_result = await self._execute_rewriting_agent(user_query, context)
                agent_log.append(f"Rewriting Agent Input: {json.dumps({'query': user_query, 'context': context}, ensure_ascii=False)}")
                agent_log.append(f"Rewriting Agent Output: {json.dumps(rewriting_result, ensure_ascii=False)}")
                
                # 컨텍스트 업데이트
                context = self._update_context_with_result(context, "rewriting", rewriting_result)
            except Exception as e:
                self.logger.error(f"Rewriting agent failed: {str(e)}")
                # 기본 재작성 결과 생성
                rewriting_result = {
                    "rewritten_text": user_query,
                    "topic": "general",
                    "context_used": False
                }
                context = self._update_context_with_result(context, "rewriting", rewriting_result)
            
            # 2. Preprocessing Agent - 컨텍스트를 고려한 전처리
            try:
                preprocessing_result = await self._execute_preprocessing_agent(rewriting_result, context)
                agent_log.append(f"Preprocessing Agent Input: {json.dumps({'rewriting_result': rewriting_result, 'context': context}, ensure_ascii=False)}")
                agent_log.append(f"Preprocessing Agent Output: {json.dumps(preprocessing_result, ensure_ascii=False)}")
                
                # 컨텍스트 업데이트
                context = self._update_context_with_result(context, "preprocessing", preprocessing_result)
            except Exception as e:
                self.logger.error(f"Preprocessing agent failed: {str(e)}")
                # 기본 전처리 결과 생성
                preprocessing_result = {
                    "normalized_text": rewriting_result.get("rewritten_text", user_query),
                    "intent": "general_inquiry",
                    "slot": [],
                    "context_used": False
                }
                context = self._update_context_with_result(context, "preprocessing", preprocessing_result)
            
            # 3. Supervisor Agent - 컨텍스트를 고려한 라우팅
            try:
                supervisor_result = await self._execute_supervisor_agent(preprocessing_result, context)
                agent_log.append(f"Supervisor Agent Input: {json.dumps({'preprocessing_result': preprocessing_result, 'context': context}, ensure_ascii=False)}")
                agent_log.append(f"Supervisor Agent Output: {json.dumps(supervisor_result, ensure_ascii=False)}")
                
                # 컨텍스트 업데이트
                context = self._update_context_with_result(context, "supervisor", supervisor_result)
            except Exception as e:
                self.logger.error(f"Supervisor agent failed: {str(e)}")
                # 기본 라우팅 결과 생성
                supervisor_result = {
                    "target_domain": "general",
                    "normalized_text": preprocessing_result.get("normalized_text", user_query),
                    "intent": preprocessing_result.get("intent", "general_inquiry"),
                    "slot": preprocessing_result.get("slot", []),
                    "context": context,
                    "routing_reasoning": "Default routing due to error"
                }
                context = self._update_context_with_result(context, "supervisor", supervisor_result)
            
            # 4. Domain Agent - 컨텍스트를 고려한 도구 실행
            try:
                domain_result = await self._execute_domain_agent(supervisor_result, context)
                agent_log.append(f"Domain Agent Input: {json.dumps({'supervisor_result': supervisor_result, 'context': context}, ensure_ascii=False)}")
                agent_log.append(f"Domain Agent Output: {json.dumps(domain_result, ensure_ascii=False)}")
                
                # 컨텍스트 업데이트
                context = self._update_context_with_result(context, "domain", domain_result)
            except Exception as e:
                self.logger.error(f"Domain agent failed: {str(e)}")
                # 기본 도구 실행 결과 생성
                domain_result = {
                    "tool_name": "general_inquiry",
                    "tool_input": {},
                    "tool_output": {"response": "일반 문의에 대한 답변입니다."},
                    "context": context,
                    "enhanced_slots": []
                }
                context = self._update_context_with_result(context, "domain", domain_result)
            
            # 5. 최종 응답 생성 - 컨텍스트를 고려한 개인화된 응답
            try:
                final_response = await self._generate_final_response(domain_result, user_query, context)
            except Exception as e:
                self.logger.error(f"Final response generation failed: {str(e)}")
                final_response = "죄송합니다. 응답 생성 중 오류가 발생했습니다."
            
            # 응답 스트리밍
            async for chunk in self._stream_response(final_response):
                yield json.dumps({'type': 'response', 'content': chunk}, ensure_ascii=False)
            
            # 대화 내역 저장 - 컨텍스트 정보 포함
            agent_log_text = "\n".join(agent_log)
            await self.session_manager.save_conversation(session_id, user_query, final_response, agent_log_text, context)
            
            yield json.dumps({'type': 'complete'}, ensure_ascii=False)
            
        except Exception as e:
            self.logger.error(f"Chat processing failed: {str(e)}")
            
            # 에러 복구: 초기 상태로 복구 시도
            if initial_context:
                try:
                    await self.session_manager.update_context(session_id, {
                        "error_recovery": True,
                        "error_message": str(e),
                        "recovery_timestamp": datetime.now().isoformat()
                    })
                    self.logger.info(f"Error recovery attempted for session {session_id}")
                except Exception as recovery_error:
                    self.logger.error(f"Error recovery failed: {str(recovery_error)}")
            
            error_response = f"죄송합니다. 처리 중 오류가 발생했습니다: {str(e)}"
            yield json.dumps({'type': 'error', 'content': error_response}, ensure_ascii=False)
    
    async def _create_integrated_context(self, session_id: str, conversation_history: list, customer_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """통합 컨텍스트 생성 - 멀티턴 질의 지원"""
        # 이전 대화에서 상태 정보 추출
        current_state = self._extract_state_from_history(conversation_history)
        
        # 대화 내역을 풍부한 형태로 변환
        enriched_history = self._enrich_conversation_history(conversation_history)
        
        context = {
            "session_id": session_id,
            "depth": len(conversation_history),
            "current_step": "rewriting",
            "conversation_history": enriched_history,
            "current_state": current_state,
            "customer_info": customer_info or {},
            "agent_results": {},
            "missing_slots": current_state.get("missing_slots", []),
            "pending_action": current_state.get("pending_action"),
            "selected_account": current_state.get("selected_account"),
            "last_intent": current_state.get("last_intent"),
            "last_slots": current_state.get("last_slots", [])
        }
        
        return context
    
    def _extract_state_from_history(self, conversation_history: list) -> Dict[str, Any]:
        """대화 내역에서 상태 정보 추출"""
        if not conversation_history:
            return {
                "selected_account": None,
                "pending_action": None,
                "missing_slots": [],
                "last_intent": None,
                "last_slots": []
            }
        
        # 최근 대화에서 상태 정보 추출
        latest_conversation = conversation_history[-1]
        agent_log = latest_conversation.get("agent_log", "")
        
        # 에이전트 로그에서 상태 정보 파싱
        state = {
            "selected_account": None,
            "pending_action": None,
            "missing_slots": [],
            "last_intent": None,
            "last_slots": []
        }
        
        try:
            # Domain Agent 결과에서 계좌 정보 추출
            if "Domain Agent Output:" in agent_log:
                domain_output_start = agent_log.find("Domain Agent Output:") + len("Domain Agent Output:")
                domain_output_end = agent_log.find("\n", domain_output_start)
                if domain_output_end == -1:
                    domain_output_end = len(agent_log)
                
                domain_output_str = agent_log[domain_output_start:domain_output_end].strip()
                domain_output = json.loads(domain_output_str)
                
                # 계좌 정보 추출
                tool_output = domain_output.get("tool_output", {})
                if "account_number" in tool_output:
                    state["selected_account"] = tool_output["account_number"]
            
            # Preprocessing Agent 결과에서 의도와 슬롯 추출
            if "Preprocessing Agent Output:" in agent_log:
                prep_output_start = agent_log.find("Preprocessing Agent Output:") + len("Preprocessing Agent Output:")
                prep_output_end = agent_log.find("\n", prep_output_start)
                if prep_output_end == -1:
                    prep_output_end = len(agent_log)
                
                prep_output_str = agent_log[prep_output_start:prep_output_end].strip()
                prep_output = json.loads(prep_output_str)
                
                state["last_intent"] = prep_output.get("intent")
                state["last_slots"] = prep_output.get("slot", [])
                
        except (json.JSONDecodeError, KeyError) as e:
            self.logger.warning(f"Failed to extract state from history: {str(e)}")
        
        return state
    
    def _enrich_conversation_history(self, conversation_history: list) -> list:
        """대화 내역을 풍부한 형태로 변환"""
        enriched_history = []
        
        for entry in conversation_history:
            enriched_entry = {
                "timestamp": entry.get("timestamp"),
                "user_query": entry.get("user_query"),
                "agent_response": entry.get("agent_response"),
                "agent_log": entry.get("agent_log"),
                "extracted_info": self._extract_info_from_log(entry.get("agent_log", ""))
            }
            enriched_history.append(enriched_entry)
        
        return enriched_history
    
    def _extract_info_from_log(self, agent_log: str) -> Dict[str, Any]:
        """에이전트 로그에서 유용한 정보 추출"""
        extracted_info = {
            "intent": None,
            "slots": [],
            "tool_name": None,
            "tool_output": {},
            "accounts_mentioned": [],
            "amounts_mentioned": []
        }
        
        try:
            # Preprocessing Agent 결과에서 의도와 슬롯 추출
            if "Preprocessing Agent Output:" in agent_log:
                prep_output_start = agent_log.find("Preprocessing Agent Output:") + len("Preprocessing Agent Output:")
                prep_output_end = agent_log.find("\n", prep_output_start)
                if prep_output_end == -1:
                    prep_output_end = len(agent_log)
                
                prep_output_str = agent_log[prep_output_start:prep_output_end].strip()
                prep_output = json.loads(prep_output_str)
                
                extracted_info["intent"] = prep_output.get("intent")
                extracted_info["slots"] = prep_output.get("slot", [])
            
            # Domain Agent 결과에서 도구 정보 추출
            if "Domain Agent Output:" in agent_log:
                domain_output_start = agent_log.find("Domain Agent Output:") + len("Domain Agent Output:")
                domain_output_end = agent_log.find("\n", domain_output_start)
                if domain_output_end == -1:
                    domain_output_end = len(agent_log)
                
                domain_output_str = agent_log[domain_output_start:domain_output_end].strip()
                domain_output = json.loads(domain_output_str)
                
                extracted_info["tool_name"] = domain_output.get("tool_name")
                extracted_info["tool_output"] = domain_output.get("tool_output", {})
                
                # 계좌 정보 추출
                tool_output = domain_output.get("tool_output", {})
                if "account_number" in tool_output:
                    extracted_info["accounts_mentioned"].append(tool_output["account_number"])
                
                # 금액 정보 추출
                if "amount" in tool_output:
                    extracted_info["amounts_mentioned"].append(tool_output["amount"])
                if "balance" in tool_output:
                    extracted_info["amounts_mentioned"].append(tool_output["balance"])
                
        except (json.JSONDecodeError, KeyError) as e:
            self.logger.warning(f"Failed to extract info from log: {str(e)}")
        
        return extracted_info
    
    def _update_context_with_result(self, context: Dict[str, Any], agent_name: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """에이전트 결과로 컨텍스트 업데이트"""
        context["agent_results"][agent_name] = result
        context["depth"] += 1
        context["current_step"] = agent_name
        
        # 상태 정보 업데이트
        if agent_name == "preprocessing":
            context["last_intent"] = result.get("intent")
            context["last_slots"] = result.get("slot", [])
        elif agent_name == "domain":
            tool_output = result.get("tool_output", {})
            if "account_number" in tool_output:
                context["selected_account"] = tool_output["account_number"]
        
        return context
    
    async def _execute_rewriting_agent(self, user_query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Rewriting Agent 실행 - 컨텍스트를 고려한 재작성"""
        # 대화 내역을 고려한 쿼리 재작성
        conversation_context = []
        for entry in context.get("conversation_history", [])[-3:]:  # 최근 3개 대화만 사용
            conversation_context.append({
                "user_query": entry.get("user_query", ""),
                "extracted_info": entry.get("extracted_info", {})
            })
        
        input_data = {
            "query": user_query,
            "conversation_context": conversation_context,
            "current_state": context.get("current_state", {}),
            "customer_info": context.get("customer_info", {})
        }
        
        return await self.rewriting_agent.execute(input_data, context)
    
    async def _execute_preprocessing_agent(self, rewriting_result: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Preprocessing Agent 실행 - 컨텍스트를 고려한 전처리"""
        input_data = {
            "rewritten_text": rewriting_result.get("rewritten_text", ""),
            "topic": rewriting_result.get("topic", ""),
            "conversation_context": context.get("conversation_history", []),
            "current_state": context.get("current_state", {}),
            "customer_info": context.get("customer_info", {})
        }
        
        return await self.preprocessing_agent.execute(input_data, context)
    
    async def _execute_supervisor_agent(self, preprocessing_result: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Supervisor Agent 실행 - 컨텍스트를 고려한 라우팅"""
        input_data = {
            "normalized_text": preprocessing_result.get("normalized_text", ""),
            "intent": preprocessing_result.get("intent", ""),
            "slot": preprocessing_result.get("slot", []),
            "conversation_context": context.get("conversation_history", []),
            "current_state": context.get("current_state", {}),
            "customer_info": context.get("customer_info", {})
        }
        
        return await self.supervisor_agent.execute(input_data, context)
    
    async def _execute_domain_agent(self, supervisor_result: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Domain Agent 실행 - 컨텍스트를 고려한 도구 실행"""
        input_data = {
            "normalized_text": supervisor_result.get("normalized_text", ""),
            "intent": supervisor_result.get("intent", ""),
            "slot": supervisor_result.get("slot", []),
            "target_domain": supervisor_result.get("target_domain", "general"),
            "conversation_context": context.get("conversation_history", []),
            "current_state": context.get("current_state", {}),
            "customer_info": context.get("customer_info", {})
        }
        
        return await self.domain_agent.execute(input_data, context)
    
    async def _generate_final_response(self, domain_result: Dict[str, Any], original_query: str, context: Dict[str, Any]) -> str:
        """최종 응답 생성 - 컨텍스트를 고려한 개인화된 응답"""
        tool_output = domain_result.get("tool_output", {})
        tool_name = domain_result.get("tool_name", "")
        
        # 고객 정보 추출
        customer_info = context.get("customer_info", {})
        customer_name = customer_info.get("name", "고객") if customer_info else "고객"
        
        # 현재 상태 정보
        current_state = context.get("current_state", {})
        selected_account = current_state.get("selected_account")
        
        # 도구 결과에 따른 응답 생성
        if tool_name == "account_balance":
            balance = tool_output.get("balance", "알 수 없음")
            account_number = tool_output.get("account_number", selected_account or "현재 계좌")
            if customer_info:
                return f"{customer_name}님, {account_number}의 현재 잔액은 {balance}입니다."
            else:
                return f"{account_number}의 현재 잔액은 {balance}입니다."
        
        elif tool_name == "transfer_money":
            status = tool_output.get("status", "실패")
            if status == "success":
                amount = tool_output.get("amount", "0")
                recipient = tool_output.get("recipient", "")
                if customer_info:
                    return f"{customer_name}님, {recipient}에게 {amount} 송금이 완료되었습니다."
                else:
                    return f"{recipient}에게 {amount} 송금이 완료되었습니다."
            else:
                return "송금 처리 중 오류가 발생했습니다."
        
        elif tool_name == "loan_info":
            available_amount = tool_output.get("available_loan_amount", "알 수 없음")
            interest_rate = tool_output.get("interest_rate", "알 수 없음")
            if customer_info:
                return f"{customer_name}님, 대출 가능 금액은 {available_amount}이며, 현재 이자율은 {interest_rate}입니다."
            else:
                return f"대출 가능 금액은 {available_amount}이며, 현재 이자율은 {interest_rate}입니다."
        
        elif tool_name == "investment_info":
            products = tool_output.get("products", [])
            rates = tool_output.get("current_rates", {})
            if customer_info:
                return f"{customer_name}님, 투자 가능한 상품: {', '.join(products)}. 현재 금리: {rates}"
            else:
                return f"투자 가능한 상품: {', '.join(products)}. 현재 금리: {rates}"
        
        elif tool_name == "exchange_rate":
            exchange_rate = tool_output.get("exchange_rate", "알 수 없음")
            converted_amount = tool_output.get("converted_amount", "알 수 없음")
            currency = tool_output.get("currency", "")
            if customer_info:
                return f"{customer_name}님, {currency} 환율은 {exchange_rate}이며, 환전 금액은 {converted_amount}입니다."
            else:
                return f"{currency} 환율은 {exchange_rate}이며, 환전 금액은 {converted_amount}입니다."
        
        elif tool_name == "auto_transfer":
            status = tool_output.get("status", "실패")
            if status == "success":
                amount = tool_output.get("amount", "0")
                schedule = tool_output.get("schedule", "")
                recipient = tool_output.get("recipient", "")
                if customer_info:
                    return f"{customer_name}님, {recipient}에게 {amount} {schedule} 자동이체가 등록되었습니다."
                else:
                    return f"{recipient}에게 {amount} {schedule} 자동이체가 등록되었습니다."
            else:
                return "자동이체 등록 중 오류가 발생했습니다."
        
        elif tool_name == "service_condition":
            conditions = tool_output.get("conditions", "서비스 이용 조건을 확인해주세요.")
            requirements = tool_output.get("requirements", [])
            fees = tool_output.get("fees", "")
            if customer_info:
                response = f"{customer_name}님, {conditions}"
                if requirements:
                    response += f" 필요 서류: {', '.join(requirements)}"
                if fees:
                    response += f" 수수료: {fees}"
                return response
            else:
                response = f"{conditions}"
                if requirements:
                    response += f" 필요 서류: {', '.join(requirements)}"
                if fees:
                    response += f" 수수료: {fees}"
                return response
        
        elif tool_name == "account_info":
            account_number = tool_output.get("account_number", "알 수 없음")
            account_type = tool_output.get("account_type", "알 수 없음")
            if customer_info:
                return f"{customer_name}님, 계좌번호: {account_number}, 계좌종류: {account_type}"
            else:
                return f"계좌번호: {account_number}, 계좌종류: {account_type}"
        
        elif tool_name == "transaction_history":
            transactions = tool_output.get("transactions", [])
            if transactions:
                response = f"최근 거래 내역입니다:\n"
                for i, tx in enumerate(transactions[:5]):  # 최근 5개만 표시
                    response += f"{i+1}. {tx.get('date', '')} - {tx.get('type', '')} {tx.get('amount', '')}원\n"
                return response
            else:
                return "거래 내역이 없습니다."
        
        elif tool_name == "deposit_history":
            deposits = tool_output.get("deposits", [])
            if deposits:
                response = f"최근 입금 내역입니다:\n"
                for i, deposit in enumerate(deposits[:5]):  # 최근 5개만 표시
                    response += f"{i+1}. {deposit.get('date', '')} - {deposit.get('sender', '')} {deposit.get('amount', '')}원\n"
                return response
            else:
                return "입금 내역이 없습니다."
        
        elif tool_name == "auto_transfer_history":
            auto_transfers = tool_output.get("auto_transfers", [])
            if auto_transfers:
                response = f"최근 자동이체 내역입니다:\n"
                for i, transfer in enumerate(auto_transfers[:5]):  # 최근 5개만 표시
                    response += f"{i+1}. {transfer.get('date', '')} - {transfer.get('recipient', '')} {transfer.get('amount', '')}원\n"
                return response
            else:
                return "자동이체 내역이 없습니다."
        
        elif tool_name == "minus_account_info":
            account_number = tool_output.get("account_number", "알 수 없음")
            credit_limit = tool_output.get("credit_limit", "알 수 없음")
            used_amount = tool_output.get("used_amount", "알 수 없음")
            remaining_limit = tool_output.get("remaining_limit", "알 수 없음")
            if customer_info:
                return f"{customer_name}님, {account_number} 마이너스 통장 정보입니다. 신용한도: {credit_limit}원, 사용금액: {used_amount}원, 남은한도: {remaining_limit}원"
            else:
                return f"{account_number} 마이너스 통장 정보입니다. 신용한도: {credit_limit}원, 사용금액: {used_amount}원, 남은한도: {remaining_limit}원"
        
        elif tool_name == "isa_account_info":
            account_number = tool_output.get("account_number", "알 수 없음")
            total_investment = tool_output.get("total_investment", "알 수 없음")
            current_value = tool_output.get("current_value", "알 수 없음")
            return_rate = tool_output.get("return_rate", "알 수 없음")
            if customer_info:
                return f"{customer_name}님, {account_number} ISA 계좌 정보입니다. 총 투자금: {total_investment}원, 현재 가치: {current_value}원, 수익률: {return_rate}%"
            else:
                return f"{account_number} ISA 계좌 정보입니다. 총 투자금: {total_investment}원, 현재 가치: {current_value}원, 수익률: {return_rate}%"
        
        elif tool_name == "mortgage_rate_change":
            changes = tool_output.get("changes", [])
            if changes:
                response = f"주택담보대출 금리 변동 내역입니다:\n"
                for i, change in enumerate(changes[:5]):  # 최근 5개만 표시
                    response += f"{i+1}. {change.get('date', '')} - {change.get('old_rate', '')}% → {change.get('new_rate', '')}%\n"
                return response
            else:
                return "금리 변동 내역이 없습니다."
        
        elif tool_name == "fund_info":
            fund_name = tool_output.get("fund_name", "알 수 없음")
            return_rate = tool_output.get("return_rate", "알 수 없음")
            management_company = tool_output.get("management_company", "알 수 없음")
            if customer_info:
                return f"{customer_name}님, {fund_name} 펀드 정보입니다. 수익률: {return_rate}%, 운용사: {management_company}"
            else:
                return f"{fund_name} 펀드 정보입니다. 수익률: {return_rate}%, 운용사: {management_company}"
        
        elif tool_name == "hot_etf_info":
            etfs = tool_output.get("etfs", [])
            if etfs:
                response = f"인기 ETF 정보입니다:\n"
                for i, etf in enumerate(etfs[:5]):  # 최근 5개만 표시
                    response += f"{i+1}. {etf.get('name', '')} - 수익률: {etf.get('return_rate', '')}%\n"
                return response
            else:
                return "인기 ETF 정보가 없습니다."
        
        elif tool_name == "transfer_limit_change":
            changes = tool_output.get("changes", [])
            if changes:
                response = f"이체 한도 변경 내역입니다:\n"
                for i, change in enumerate(changes[:5]):  # 최근 5개만 표시
                    response += f"{i+1}. {change.get('date', '')} - {change.get('old_limit', '')}원 → {change.get('new_limit', '')}원\n"
                return response
            else:
                return "이체 한도 변경 내역이 없습니다."
        
        elif tool_name == "frequent_deposit_accounts":
            accounts = tool_output.get("accounts", [])
            if accounts:
                response = f"자주 입금한 계좌 목록입니다:\n"
                for i, account in enumerate(accounts[:5]):  # 최근 5개만 표시
                    response += f"{i+1}. {account.get('account_number', '')} - {account.get('count', '')}회 입금\n"
                return response
            else:
                return "자주 입금한 계좌가 없습니다."
        
        elif tool_name == "loan_account_status":
            accounts = tool_output.get("accounts", [])
            if accounts:
                response = f"대출 계좌 상태입니다:\n"
                for i, account in enumerate(accounts[:5]):  # 최근 5개만 표시
                    response += f"{i+1}. {account.get('account_number', '')} - 잔액: {account.get('balance', '')}원, 상태: {account.get('status', '')}\n"
                return response
            else:
                return "대출 계좌가 없습니다."
        
        # 기본 응답 - 도구 결과가 있는 경우
        elif tool_output:
            if isinstance(tool_output, dict):
                # 도구 결과를 문자열로 변환
                result_str = str(tool_output)
                if customer_info:
                    return f"{customer_name}님, {result_str}"
                else:
                    return result_str
            else:
                if customer_info:
                    return f"{customer_name}님, {tool_output}"
                else:
                    return str(tool_output)
        
        # 기본 응답 - 질문에 대한 일반적인 답변
        else:
            if "잔액" in original_query or "계좌" in original_query:
                return "계좌 잔액을 확인해드리겠습니다. 계좌번호를 알려주시면 정확한 잔액을 조회해드릴 수 있습니다."
            elif "송금" in original_query or "이체" in original_query:
                return "송금 서비스를 이용해드리겠습니다. 수신자 정보와 금액을 알려주시면 송금을 진행해드릴 수 있습니다."
            elif "대출" in original_query:
                return "대출 정보를 확인해드리겠습니다. 현재 대출 가능 금액과 이자율을 조회해드릴 수 있습니다."
            elif "환전" in original_query:
                return "환전 정보를 확인해드리겠습니다. 원하시는 통화와 금액을 알려주시면 환율과 환전 금액을 계산해드릴 수 있습니다."
            elif "자동이체" in original_query:
                return "자동이체 서비스를 이용해드리겠습니다. 수신자, 금액, 일정을 알려주시면 자동이체를 등록해드릴 수 있습니다."
            elif "펀드" in original_query or "투자" in original_query:
                return "투자 상품 정보를 확인해드리겠습니다. 현재 다양한 펀드와 ETF 상품의 수익률과 정보를 제공해드릴 수 있습니다."
            else:
                if customer_info:
                    return f"{customer_name}님, {original_query}에 대한 답변입니다. 추가로 궁금한 점이 있으시면 언제든 말씀해 주세요."
                else:
                    return f"{original_query}에 대한 답변입니다. 추가로 궁금한 점이 있으시면 언제든 말씀해 주세요."
    
    async def _stream_response(self, response: str) -> AsyncGenerator[str, None]:
        """응답 스트리밍"""
        # 테스트 모드에서는 단순 텍스트 반환
        if os.getenv('TEST_MODE', 'false').lower() == 'true':
            yield response
            return
        
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
    
    async def get_session_context(self, session_id: str) -> Optional[Dict[str, Any]]:
        """세션 컨텍스트 정보 조회"""
        return await self.session_manager.get_current_context(session_id)
    
    async def update_session_context(self, session_id: str, context_updates: Dict[str, Any]) -> bool:
        """세션 컨텍스트 업데이트"""
        return await self.session_manager.update_context(session_id, context_updates)
    
    async def clear_session_context(self, session_id: str) -> bool:
        """세션 컨텍스트 초기화"""
        return await self.session_manager.clear_context(session_id) 