from typing import Dict, Any, List
from ..preprocessing import PreprocessingPipeline
from ..agents import SupervisorAgent
from ..models.chat_models import ChatMessage, ChatSession, MessageRole
from ..models.agent_models import AgentRequest, AgentType
from ..logger import service_logger


class ChatService:
    """채팅 서비스 클래스"""
    
    def __init__(self):
        """채팅 서비스를 초기화합니다."""
        self.preprocessing_pipeline = PreprocessingPipeline()
        self.supervisor_agent = SupervisorAgent()
        self.logger = service_logger
        self.sessions: Dict[str, ChatSession] = {}
    
    def process_message(self, session_id: str, user_id: str, message: str) -> Dict[str, Any]:
        """메시지를 처리합니다."""
        try:
            self.logger.info(f"메시지 처리 시작: session_id={session_id}, user_id={user_id}")
            
            # 세션 관리
            session = self._get_or_create_session(session_id, user_id)
            
            # 사용자 메시지 추가
            user_message = ChatMessage(
                role=MessageRole.USER,
                content=message
            )
            session.add_message(user_message)
            
            # 전처리 파이프라인 실행
            preprocessing_result = self.preprocessing_pipeline.process(
                query=message,
                conversation_history=[msg.content for msg in session.get_conversation_history()]
            )
            
            # 에이전트 요청 생성
            agent_request = AgentRequest(
                agent_type=AgentType.SUPERVISOR,
                user_query=preprocessing_result["rewritten_query"],
                conversation_history=[msg.content for msg in session.get_conversation_history()],
                intent_classification=preprocessing_result["intent_classification"]
            )
            
            # Supervisor 에이전트 처리
            agent_response = self.supervisor_agent.process(agent_request)
            
            # 응답 메시지 생성
            assistant_message = ChatMessage(
                role=MessageRole.ASSISTANT,
                content=agent_response.response,
                metadata={
                    "agent_type": agent_response.agent_type.value,
                    "domain": agent_response.domain.value if agent_response.domain else None,
                    "worker": agent_response.worker,
                    "reasoning": agent_response.reasoning
                }
            )
            session.add_message(assistant_message)
            
            # 응답 구성
            response = {
                "session_id": session_id,
                "response": agent_response.response,
                "domain": agent_response.domain.value if agent_response.domain else None,
                "worker": agent_response.worker,
                "metadata": {
                    "original_query": preprocessing_result["original_query"],
                    "normalized_query": preprocessing_result["normalized_query"],
                    "rewritten_query": preprocessing_result["rewritten_query"],
                    "intent": preprocessing_result["intent_classification"].intent,
                    "confidence": preprocessing_result["intent_classification"].confidence,
                    "reasoning": agent_response.reasoning
                }
            }
            
            self.logger.info(f"메시지 처리 완료: session_id={session_id}")
            return response
            
        except Exception as e:
            self.logger.log_error_with_context(e, f"ChatService.process_message({session_id})")
            
            # 에러 응답
            error_message = ChatMessage(
                role=MessageRole.ASSISTANT,
                content="죄송합니다. 메시지 처리 중 오류가 발생했습니다. 다시 시도해주세요."
            )
            session.add_message(error_message)
            
            return {
                "session_id": session_id,
                "response": "죄송합니다. 메시지 처리 중 오류가 발생했습니다. 다시 시도해주세요.",
                "error": str(e)
            }
    
    def _get_or_create_session(self, session_id: str, user_id: str) -> ChatSession:
        """세션을 가져오거나 생성합니다."""
        if session_id not in self.sessions:
            self.sessions[session_id] = ChatSession(
                session_id=session_id,
                user_id=user_id
            )
            self.logger.info(f"새 세션 생성: session_id={session_id}, user_id={user_id}")
        
        return self.sessions[session_id]
    
    def get_session_history(self, session_id: str) -> List[Dict[str, Any]]:
        """세션 히스토리를 반환합니다."""
        try:
            if session_id not in self.sessions:
                return []
            
            session = self.sessions[session_id]
            return [msg.to_dict() for msg in session.messages]
            
        except Exception as e:
            self.logger.log_error_with_context(e, f"ChatService.get_session_history({session_id})")
            return []
    
    def clear_session(self, session_id: str) -> bool:
        """세션을 클리어합니다."""
        try:
            if session_id in self.sessions:
                del self.sessions[session_id]
                self.logger.info(f"세션 클리어: session_id={session_id}")
                return True
            return False
            
        except Exception as e:
            self.logger.log_error_with_context(e, f"ChatService.clear_session({session_id})")
            return False 