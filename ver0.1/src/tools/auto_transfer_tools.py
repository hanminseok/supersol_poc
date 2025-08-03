from typing import Dict, Any, List
from ..models.tool_models import ToolRequest, ToolResponse
from ..utils.data_loader import DataLoader
from .base_tool import BaseTool


class GetAutoTransferInfoTool(BaseTool):
    """자동이체 정보 조회 도구"""
    
    def __init__(self):
        """자동이체 정보 조회 도구를 초기화합니다."""
        super().__init__("get_auto_transfer_info")
        self.data_loader = DataLoader()
    
    def execute(self, request: ToolRequest) -> ToolResponse:
        """자동이체 정보를 조회합니다."""
        try:
            self.log_input(request)
            
            # 파라미터 검증
            account_number = request.parameters.get("account_number")
            if not account_number:
                return self.create_error_response("계좌번호가 필요합니다.")
            
            # 데이터 조회
            auto_transfers = self.data_loader.get_auto_transfer_info(account_number)
            
            # 응답 생성
            result = {
                "account_number": account_number,
                "auto_transfers": auto_transfers,
                "total_count": len(auto_transfers)
            }
            
            response = self.create_success_response(result)
            self.log_output(response)
            return response
            
        except Exception as e:
            return self.handle_error(e, request)


class SetupAutoTransferTool(BaseTool):
    """자동이체 설정 도구"""
    
    def __init__(self):
        """자동이체 설정 도구를 초기화합니다."""
        super().__init__("setup_auto_transfer")
    
    def execute(self, request: ToolRequest) -> ToolResponse:
        """자동이체를 설정합니다."""
        try:
            self.log_input(request)
            
            # 파라미터 검증
            from_account = request.parameters.get("from_account")
            to_account = request.parameters.get("to_account")
            amount = request.parameters.get("amount")
            frequency = request.parameters.get("frequency")
            start_date = request.parameters.get("start_date")
            
            if not all([from_account, to_account, amount, frequency, start_date]):
                return self.create_error_response("모든 파라미터가 필요합니다.")
            
            # 자동이체 설정 (실제로는 데이터베이스 업데이트)
            result = {
                "status": "success",
                "message": f"자동이체가 성공적으로 설정되었습니다. ({from_account} → {to_account}: {amount}원, {frequency})",
                "auto_transfer_id": f"AUTO_{from_account}_{to_account}_{amount}",
                "from_account": from_account,
                "to_account": to_account,
                "amount": amount,
                "frequency": frequency,
                "start_date": start_date
            }
            
            response = self.create_success_response(result)
            self.log_output(response)
            return response
            
        except Exception as e:
            return self.handle_error(e, request)


class AutoTransferTools:
    """자동이체 도구 모음"""
    
    def __init__(self):
        """자동이체 도구들을 초기화합니다."""
        self.get_auto_transfer_info = GetAutoTransferInfoTool()
        self.setup_auto_transfer = SetupAutoTransferTool()
    
    def get_tools(self) -> Dict[str, BaseTool]:
        """도구들을 반환합니다."""
        return {
            "get_auto_transfer_info": self.get_auto_transfer_info,
            "setup_auto_transfer": self.setup_auto_transfer
        } 