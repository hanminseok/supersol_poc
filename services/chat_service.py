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
        
        input_data = {
            "query": query_context + [user_query],
            "customer_info": customer_info
        }
        
        return await self.rewriting_agent.execute(input_data)
    
    async def _execute_preprocessing_agent(self, rewriting_result: Dict[str, Any], customer_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Preprocessing Agent 실행"""
        input_data = {
            "rewritten_text": rewriting_result.get("rewritten_text", ""),
            "topic": rewriting_result.get("topic", ""),
            "customer_info": customer_info
        }
        
        return await self.preprocessing_agent.execute(input_data)
    
    async def _execute_supervisor_agent(self, preprocessing_result: Dict[str, Any], customer_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Supervisor Agent 실행"""
        input_data = {
            "normalized_text": preprocessing_result.get("normalized_text", ""),
            "intent": preprocessing_result.get("intent", ""),
            "slot": preprocessing_result.get("slot", []),
            "customer_info": customer_info
        }
        
        return await self.supervisor_agent.execute(input_data)
    
    async def _execute_domain_agent(self, supervisor_result: Dict[str, Any], customer_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Domain Agent 실행"""
        input_data = {
            "normalized_text": supervisor_result.get("normalized_text", ""),
            "intent": supervisor_result.get("intent", ""),
            "slot": supervisor_result.get("slot", []),
            "target_domain": supervisor_result.get("target_domain", "general"),
            "customer_info": customer_info
        }
        
        return await self.domain_agent.execute(input_data)
    
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