from typing import Dict, Any
from ..models.tool_models import ToolRequest, ToolResponse
from ..utils.data_loader import DataLoader
from .base_tool import BaseTool


class GetCustomerInfoTool(BaseTool):
    """고객정보 조회 도구"""
    
    def __init__(self):
        """고객정보 조회 도구를 초기화합니다."""
        super().__init__("get_customer_info")
        self.data_loader = DataLoader()
    
    def execute(self, request: ToolRequest) -> ToolResponse:
        """고객정보를 조회합니다."""
        try:
            self.log_input(request)
            
            # 파라미터 검증
            customer_id = request.parameters.get("customer_id")
            if not customer_id:
                return self.create_error_response("고객 ID가 필요합니다.")
            
            # 데이터 조회
            customer_info = self.data_loader.get_customer_info(customer_id)
            
            if not customer_info:
                return self.create_error_response(f"고객 ID '{customer_id}'에 해당하는 정보를 찾을 수 없습니다.")
            
            # 응답 생성
            result = {
                "customer_id": customer_info.get("customer_id"),
                "name": customer_info.get("name"),
                "phone": customer_info.get("phone"),
                "email": customer_info.get("email"),
                "address": customer_info.get("address")
            }
            
            response = self.create_success_response(result)
            self.log_output(response)
            return response
            
        except Exception as e:
            return self.handle_error(e, request)


class UpdateCustomerInfoTool(BaseTool):
    """고객정보 수정 도구"""
    
    def __init__(self):
        """고객정보 수정 도구를 초기화합니다."""
        super().__init__("update_customer_info")
        self.data_loader = DataLoader()
    
    def execute(self, request: ToolRequest) -> ToolResponse:
        """고객정보를 수정합니다."""
        try:
            self.log_input(request)
            
            # 파라미터 검증
            customer_id = request.parameters.get("customer_id")
            field = request.parameters.get("field")
            value = request.parameters.get("value")
            
            if not all([customer_id, field, value]):
                return self.create_error_response("고객 ID, 수정할 필드, 새로운 값이 모두 필요합니다.")
            
            # 수정 가능한 필드 검증
            allowed_fields = ["name", "phone", "email", "address"]
            if field not in allowed_fields:
                return self.create_error_response(f"수정할 수 없는 필드입니다. 가능한 필드: {', '.join(allowed_fields)}")
            
            # 기존 정보 확인
            customer_info = self.data_loader.get_customer_info(customer_id)
            if not customer_info:
                return self.create_error_response(f"고객 ID '{customer_id}'에 해당하는 정보를 찾을 수 없습니다.")
            
            # 수정 실행 (실제로는 데이터베이스 업데이트)
            result = {
                "status": "success",
                "message": f"고객정보가 성공적으로 수정되었습니다. ({field}: {value})",
                "customer_id": customer_id,
                "updated_field": field,
                "new_value": value
            }
            
            response = self.create_success_response(result)
            self.log_output(response)
            return response
            
        except Exception as e:
            return self.handle_error(e, request)


class CustomerInfoTools:
    """고객정보 도구 모음"""
    
    def __init__(self):
        """고객정보 도구들을 초기화합니다."""
        self.get_customer_info = GetCustomerInfoTool()
        self.update_customer_info = UpdateCustomerInfoTool()
    
    def get_tools(self) -> Dict[str, BaseTool]:
        """도구들을 반환합니다."""
        return {
            "get_customer_info": self.get_customer_info,
            "update_customer_info": self.update_customer_info
        } 