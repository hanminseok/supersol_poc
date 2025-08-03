from typing import Dict, Any
from ..models.tool_models import ToolRequest, ToolResponse
from ..utils.data_loader import DataLoader
from .base_tool import BaseTool


class GetAccountInfoTool(BaseTool):
    """계좌 정보 조회 도구"""
    
    def __init__(self):
        """계좌 정보 조회 도구를 초기화합니다."""
        super().__init__("get_account_info")
        self.data_loader = DataLoader()
    
    def execute(self, request: ToolRequest) -> ToolResponse:
        """계좌 정보를 조회합니다."""
        try:
            self.log_input(request)
            
            # 파라미터 검증
            account_number = request.parameters.get("account_number")
            if not account_number:
                return self.create_error_response("계좌번호가 필요합니다.")
            
            # 데이터 조회
            account_info = self.data_loader.get_account_info(account_number)
            
            if not account_info:
                return self.create_error_response(f"계좌번호 '{account_number}'에 해당하는 정보를 찾을 수 없습니다.")
            
            # 응답 생성
            result = {
                "account_number": account_info.get("account_number"),
                "account_type": account_info.get("account_type"),
                "balance": account_info.get("balance"),
                "currency": account_info.get("currency"),
                "status": account_info.get("status")
            }
            
            response = self.create_success_response(result)
            self.log_output(response)
            return response
            
        except Exception as e:
            return self.handle_error(e, request)


class AccountTools:
    """계좌 도구 모음"""
    
    def __init__(self):
        """계좌 도구들을 초기화합니다."""
        self.get_account_info = GetAccountInfoTool()
    
    def get_tools(self) -> Dict[str, BaseTool]:
        """도구들을 반환합니다."""
        return {
            "get_account_info": self.get_account_info
        } 