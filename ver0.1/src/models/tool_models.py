from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class ToolType(str, Enum):
    """도구 유형 열거형"""
    # 고객정보 도구
    GET_CUSTOMER_INFO = "get_customer_info"
    UPDATE_CUSTOMER_INFO = "update_customer_info"
    
    # 금융정보 도구
    GET_FINANCIAL_INFO = "get_financial_info"
    
    # 이체 도구
    GET_TRANSFER_HISTORY = "get_transfer_history"
    EXECUTE_TRANSFER = "execute_transfer"
    
    # 계좌 도구
    GET_ACCOUNT_INFO = "get_account_info"
    
    # 자동이체 도구
    GET_AUTO_TRANSFER_INFO = "get_auto_transfer_info"
    SETUP_AUTO_TRANSFER = "setup_auto_transfer"
    
    # 투자상품 도구
    GET_INVESTMENT_PRODUCTS = "get_investment_products"
    SUBSCRIBE_INVESTMENT_PRODUCT = "subscribe_investment_product"
    
    # 대출 도구
    GET_LOAN_INFO = "get_loan_info"
    APPLY_LOAN = "apply_loan"


@dataclass
class ToolParameter:
    """도구 파라미터 모델"""
    name: str
    type: str
    description: str
    required: bool = True
    default: Optional[Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "name": self.name,
            "type": self.type,
            "description": self.description,
            "required": self.required,
            "default": self.default
        }


@dataclass
class ToolDefinition:
    """도구 정의 모델"""
    name: str
    description: str
    parameters: List[ToolParameter] = field(default_factory=list)
    returns: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": [param.to_dict() for param in self.parameters],
            "returns": self.returns
        }


@dataclass
class ToolRequest:
    """도구 요청 모델"""
    tool_name: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "tool_name": self.tool_name,
            "parameters": self.parameters,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class ToolResponse:
    """도구 응답 모델"""
    tool_name: str
    result: Dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "tool_name": self.tool_name,
            "result": self.result,
            "success": self.success,
            "error_message": self.error_message,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }
    
    @classmethod
    def create_error_response(cls, tool_name: str, error_message: str) -> 'ToolResponse':
        """에러 응답을 생성합니다."""
        return cls(
            tool_name=tool_name,
            success=False,
            error_message=error_message
        ) 