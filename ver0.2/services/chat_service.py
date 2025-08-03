import asyncio
import json
import os
from typing import Dict, Any, Optional, AsyncGenerator
from services.agent_manager import AgentManager
from services.session_manager import SessionManager
from services.response_generator import ResponseGenerator
from services.session_optimizer import SessionOptimizer
from utils.logger import service_logger, agent_logger
from datetime import datetime

class ChatService:
    def __init__(self):
        self.session_manager = SessionManager()
        self.agent_manager = AgentManager()
        self.session_optimizer = SessionOptimizer()
        self.response_generator = ResponseGenerator()
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
            
            # Agent Manager를 사용한 워크플로우 실행
            try:
                # 초기 입력 데이터 준비
                initial_input = {
                    "query": user_query,
                    "conversation_context": conversation_history,
                    "current_state": context.get("current_state", {})
                }
                
                # Agent Manager를 통해 워크플로우 실행 (rewriting부터 시작)
                final_result = await self.agent_manager.execute_workflow("rewriting", initial_input, context)
                
                # direct_response가 있는지 확인 (rewriting_agent에서 생성된 직접 답변)
                if final_result.get("direct_response"):
                    # direct_response가 있으면 이를 최종 응답으로 사용
                    domain_result = {
                        "tool_name": "direct_response",
                        "tool_output": {"response": final_result["direct_response"]},
                        "context": context,
                        "enhanced_slots": []
                    }
                else:
                    # 결과에서 최종 도메인 결과 추출
                    domain_result = final_result
                
                # Agent 로그 기록
                agent_log.append(f"Workflow Input: {json.dumps(initial_input, ensure_ascii=False)}")
                agent_log.append(f"Workflow Output: {json.dumps(final_result, ensure_ascii=False)}")
                
                # 컨텍스트 업데이트
                context = self._update_context_with_result(context, "workflow", final_result)
                
            except Exception as e:
                self.logger.error(f"Workflow execution failed: {str(e)}")
                # 기본 결과 생성
                domain_result = {
                    "tool_name": "general_inquiry",
                    "tool_input": {},
                    "tool_output": {"response": "일반 문의에 대한 답변입니다."},
                    "context": context,
                    "enhanced_slots": []
                }
                context = self._update_context_with_result(context, "workflow", domain_result)
            
            # 5. 최종 응답 생성 - 컨텍스트를 고려한 개인화된 응답
            try:
                final_response = await self._generate_final_response(domain_result, user_query, context)
            except Exception as e:
                self.logger.error(f"Final response generation failed: {str(e)}")
                final_response = "죄송합니다. 응답 생성 중 오류가 발생했습니다."
            
            # 세션 파일 최적화 (백그라운드에서 실행)
            asyncio.create_task(self._optimize_session_background(session_id))
            
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
    
    def _clean_context_for_logging(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """로그 기록을 위해 context를 정리 (circular reference 방지)"""
        if not context:
            return {}
        
        clean_context = {}
        for key, value in context.items():
            if key in ['conversation_history', 'agent_results']:
                # 복잡한 객체는 요약 정보만 포함
                if isinstance(value, list):
                    clean_context[key] = f"[{len(value)} items]"
                elif isinstance(value, dict):
                    clean_context[key] = f"{{{len(value)} keys}}"
                else:
                    clean_context[key] = str(type(value))
            else:
                # 단순한 값들은 그대로 복사
                try:
                    json.dumps(value)  # JSON 직렬화 가능한지 테스트
                    clean_context[key] = value
                except (TypeError, ValueError):
                    clean_context[key] = str(value)
        
        return clean_context

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
    
    # 개별 Agent 실행 메서드들은 AgentManager로 대체됨
    
    async def _generate_final_response(self, domain_result: Dict[str, Any], original_query: str, context: Dict[str, Any]) -> str:
        """최종 응답 생성 - 컨텍스트를 고려한 개인화된 응답"""
        tool_output = domain_result.get("tool_output", {})
        tool_name = domain_result.get("tool_name", "")
        customer_info = context.get("customer_info", {})
        
        # ResponseGenerator를 사용하여 응답 생성
        return ResponseGenerator.generate_response(tool_name, tool_output, customer_info, context)
    
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
    
    async def _optimize_session_background(self, session_id: str) -> None:
        """백그라운드에서 세션 파일 최적화"""
        try:
            await self.session_optimizer.optimize_session_file(session_id)
        except Exception as e:
            self.logger.error(f"Background session optimization failed for {session_id}: {str(e)}")
    
    async def get_session_optimization_status(self) -> Dict[str, Any]:
        """세션 최적화 상태 조회"""
        try:
            large_sessions = await self.session_optimizer.get_large_sessions()
            optimization_results = await self.session_optimizer.optimize_all_sessions()
            
            return {
                "large_sessions": large_sessions,
                "optimization_results": optimization_results,
                "total_large_sessions": len(large_sessions)
            }
        except Exception as e:
            self.logger.error(f"Failed to get session optimization status: {str(e)}")
            return {"error": str(e)} 