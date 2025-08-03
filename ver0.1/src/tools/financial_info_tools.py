from typing import Dict, Any
from ..models.tool_models import ToolRequest, ToolResponse
from ..utils.data_loader import DataLoader
from .base_tool import BaseTool


class GetFinancialInfoTool(BaseTool):
    """금융정보 조회 도구"""
    
    def __init__(self):
        """금융정보 조회 도구를 초기화합니다."""
        super().__init__("get_financial_info")
        self.data_loader = DataLoader()
    
    def execute(self, request: ToolRequest) -> ToolResponse:
        """금융정보를 조회합니다."""
        try:
            self.log_input(request)
            
            # 파라미터 검증
            customer_id = request.parameters.get("customer_id")
            if not customer_id:
                return self.create_error_response("고객 ID가 필요합니다.")
            
            # 데이터 조회
            financial_info = self.data_loader.get_financial_info(customer_id)
            
            if not financial_info:
                return self.create_error_response(f"고객 ID '{customer_id}'에 해당하는 금융정보를 찾을 수 없습니다.")
            
            # 응답 생성
            result = {
                "customer_id": financial_info.get("customer_id"),
                "credit_score": financial_info.get("credit_score"),
                "income": financial_info.get("income"),
                "assets": financial_info.get("assets"),
                "liabilities": financial_info.get("liabilities")
            }
            
            response = self.create_success_response(result)
            self.log_output(response)
            return response
            
        except Exception as e:
            return self.handle_error(e, request)


class FinancialInfoTools:
    """금융정보 도구 모음"""
    
    def __init__(self):
        """금융정보 도구들을 초기화합니다."""
        self.get_financial_info = GetFinancialInfoTool()
    
    def get_tools(self) -> Dict[str, BaseTool]:
        """도구들을 반환합니다."""
        return {
            "get_financial_info": self.get_financial_info
        } 