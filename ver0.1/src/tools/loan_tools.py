from typing import Dict, Any, List
from ..models.tool_models import ToolRequest, ToolResponse
from ..utils.data_loader import DataLoader
from .base_tool import BaseTool


class GetLoanInfoTool(BaseTool):
    """대출 정보 조회 도구"""
    
    def __init__(self):
        """대출 정보 조회 도구를 초기화합니다."""
        super().__init__("get_loan_info")
        self.data_loader = DataLoader()
    
    def execute(self, request: ToolRequest) -> ToolResponse:
        """대출 정보를 조회합니다."""
        try:
            self.log_input(request)
            
            # 파라미터 검증
            customer_id = request.parameters.get("customer_id")
            if not customer_id:
                return self.create_error_response("고객 ID가 필요합니다.")
            
            # 데이터 조회
            loans = self.data_loader.get_loan_info(customer_id)
            
            # 응답 생성
            result = {
                "customer_id": customer_id,
                "loans": loans,
                "total_count": len(loans)
            }
            
            response = self.create_success_response(result)
            self.log_output(response)
            return response
            
        except Exception as e:
            return self.handle_error(e, request)


class ApplyLoanTool(BaseTool):
    """대출 신청 도구"""
    
    def __init__(self):
        """대출 신청 도구를 초기화합니다."""
        super().__init__("apply_loan")
    
    def execute(self, request: ToolRequest) -> ToolResponse:
        """대출을 신청합니다."""
        try:
            self.log_input(request)
            
            # 파라미터 검증
            customer_id = request.parameters.get("customer_id")
            loan_type = request.parameters.get("loan_type")
            amount = request.parameters.get("amount")
            term = request.parameters.get("term")
            
            if not all([customer_id, loan_type, amount, term]):
                return self.create_error_response("고객 ID, 대출 유형, 대출 금액, 대출 기간이 모두 필요합니다.")
            
            # 대출 신청 (실제로는 데이터베이스 업데이트)
            result = {
                "status": "success",
                "message": f"대출 신청이 성공적으로 접수되었습니다. (유형: {loan_type}, 금액: {amount}원, 기간: {term}개월)",
                "application_id": f"LOAN_{customer_id}_{loan_type}_{amount}",
                "customer_id": customer_id,
                "loan_type": loan_type,
                "amount": amount,
                "term": term
            }
            
            response = self.create_success_response(result)
            self.log_output(response)
            return response
            
        except Exception as e:
            return self.handle_error(e, request)


class LoanTools:
    """대출 도구 모음"""
    
    def __init__(self):
        """대출 도구들을 초기화합니다."""
        self.get_loan_info = GetLoanInfoTool()
        self.apply_loan = ApplyLoanTool()
    
    def get_tools(self) -> Dict[str, BaseTool]:
        """도구들을 반환합니다."""
        return {
            "get_loan_info": self.get_loan_info,
            "apply_loan": self.apply_loan
        } 