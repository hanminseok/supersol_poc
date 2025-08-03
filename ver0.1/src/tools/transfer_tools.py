from typing import Dict, Any, List
from ..models.tool_models import ToolRequest, ToolResponse
from ..utils.data_loader import DataLoader
from .base_tool import BaseTool


class GetTransferHistoryTool(BaseTool):
    """이체 내역 조회 도구"""
    
    def __init__(self):
        """이체 내역 조회 도구를 초기화합니다."""
        super().__init__("get_transfer_history")
        self.data_loader = DataLoader()
    
    def execute(self, request: ToolRequest) -> ToolResponse:
        """이체 내역을 조회합니다."""
        try:
            self.log_input(request)
            
            # 파라미터 검증
            account_number = request.parameters.get("account_number")
            if not account_number:
                return self.create_error_response("계좌번호가 필요합니다.")
            
            start_date = request.parameters.get("start_date")
            end_date = request.parameters.get("end_date")
            
            # 데이터 조회
            transfers = self.data_loader.get_transfer_history(account_number, start_date, end_date)
            
            # 응답 생성
            result = {
                "account_number": account_number,
                "transfers": transfers,
                "total_count": len(transfers)
            }
            
            response = self.create_success_response(result)
            self.log_output(response)
            return response
            
        except Exception as e:
            return self.handle_error(e, request)


class ExecuteTransferTool(BaseTool):
    """이체 실행 도구"""
    
    def __init__(self):
        """이체 실행 도구를 초기화합니다."""
        super().__init__("execute_transfer")
    
    def execute(self, request: ToolRequest) -> ToolResponse:
        """이체를 실행합니다."""
        try:
            self.log_input(request)
            
            # 파라미터 검증
            from_account = request.parameters.get("from_account")
            to_account = request.parameters.get("to_account")
            amount = request.parameters.get("amount")
            
            if not all([from_account, to_account, amount]):
                return self.create_error_response("출금 계좌, 입금 계좌, 금액이 모두 필요합니다.")
            
            # 이체 실행 (실제로는 데이터베이스 업데이트)
            result = {
                "status": "success",
                "message": f"이체가 성공적으로 실행되었습니다. ({from_account} → {to_account}: {amount}원)",
                "transaction_id": f"TXN_{from_account}_{to_account}_{amount}",
                "from_account": from_account,
                "to_account": to_account,
                "amount": amount
            }
            
            response = self.create_success_response(result)
            self.log_output(response)
            return response
            
        except Exception as e:
            return self.handle_error(e, request)


class TransferTools:
    """이체 도구 모음"""
    
    def __init__(self):
        """이체 도구들을 초기화합니다."""
        self.get_transfer_history = GetTransferHistoryTool()
        self.execute_transfer = ExecuteTransferTool()
    
    def get_tools(self) -> Dict[str, BaseTool]:
        """도구들을 반환합니다."""
        return {
            "get_transfer_history": self.get_transfer_history,
            "execute_transfer": self.execute_transfer
        } 