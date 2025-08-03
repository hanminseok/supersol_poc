from abc import ABC, abstractmethod
from typing import Dict, Any
from ..models.tool_models import ToolRequest, ToolResponse
from ..logger import tool_logger


class BaseTool(ABC):
    """기본 도구 클래스"""
    
    def __init__(self, tool_name: str):
        """기본 도구를 초기화합니다."""
        self.tool_name = tool_name
        self.logger = tool_logger
    
    @abstractmethod
    def execute(self, request: ToolRequest) -> ToolResponse:
        """도구를 실행합니다."""
        pass
    
    def log_input(self, request: ToolRequest) -> None:
        """입력을 로깅합니다."""
        self.logger.log_tool_call(
            self.tool_name,
            request.parameters,
            {}
        )
    
    def log_output(self, response: ToolResponse) -> None:
        """출력을 로깅합니다."""
        self.logger.log_tool_call(
            self.tool_name,
            {},
            response.result
        )
    
    def create_success_response(self, result: Dict[str, Any]) -> ToolResponse:
        """성공 응답을 생성합니다."""
        return ToolResponse(
            tool_name=self.tool_name,
            result=result,
            success=True
        )
    
    def create_error_response(self, error_message: str) -> ToolResponse:
        """에러 응답을 생성합니다."""
        return ToolResponse.create_error_response(
            self.tool_name,
            error_message
        )
    
    def handle_error(self, error: Exception, request: ToolRequest) -> ToolResponse:
        """에러를 처리합니다."""
        self.logger.log_error_with_context(error, f"{self.tool_name}.execute")
        
        error_message = f"{self.tool_name} 실행 중 오류가 발생했습니다: {str(error)}"
        
        return self.create_error_response(error_message) 