from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from ..models.agent_models import AgentRequest, AgentResponse, AgentType
from ..logger import agent_logger
from ..utils.prompt_loader import PromptLoader


class BaseAgent(ABC):
    """기본 에이전트 클래스"""
    
    def __init__(self, agent_type: AgentType):
        """기본 에이전트를 초기화합니다."""
        self.agent_type = agent_type
        self.logger = agent_logger
        self.prompt_loader = PromptLoader()
    
    @abstractmethod
    def process(self, request: AgentRequest) -> AgentResponse:
        """요청을 처리합니다."""
        pass
    
    def log_input(self, request: AgentRequest) -> None:
        """입력을 로깅합니다."""
        self.logger.log_agent_input(
            self.agent_type.value,
            f"Query: {request.user_query}, Intent: {request.intent_classification.intent if request.intent_classification else 'None'}"
        )
    
    def log_output(self, response: AgentResponse) -> None:
        """출력을 로깅합니다."""
        self.logger.log_agent_output(
            self.agent_type.value,
            f"Response: {response.response}, Domain: {response.domain.value if response.domain else 'None'}, Worker: {response.worker or 'None'}"
        )
    
    def create_response(self, response: str, domain: Optional[str] = None, 
                       worker: Optional[str] = None, tool_calls: Optional[list] = None,
                       reasoning: Optional[str] = None) -> AgentResponse:
        """응답을 생성합니다."""
        return AgentResponse(
            agent_type=self.agent_type,
            response=response,
            domain=domain,
            worker=worker,
            tool_calls=tool_calls or [],
            reasoning=reasoning
        )
    
    def handle_error(self, error: Exception, request: AgentRequest) -> AgentResponse:
        """에러를 처리합니다."""
        self.logger.log_error_with_context(error, f"{self.agent_type.value}.process")
        
        error_message = f"죄송합니다. {self.agent_type.value} 처리 중 오류가 발생했습니다. 다시 시도해주세요."
        
        return self.create_response(
            response=error_message,
            reasoning=f"Error: {str(error)}"
        ) 