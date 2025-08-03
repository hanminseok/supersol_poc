from typing import Dict, Any, List
from ..models.tool_models import ToolRequest, ToolResponse
from ..utils.data_loader import DataLoader
from .base_tool import BaseTool


class GetInvestmentProductsTool(BaseTool):
    """투자상품 조회 도구"""
    
    def __init__(self):
        """투자상품 조회 도구를 초기화합니다."""
        super().__init__("get_investment_products")
        self.data_loader = DataLoader()
    
    def execute(self, request: ToolRequest) -> ToolResponse:
        """투자상품을 조회합니다."""
        try:
            self.log_input(request)
            
            # 파라미터 추출
            product_type = request.parameters.get("product_type")
            risk_level = request.parameters.get("risk_level")
            
            # 데이터 조회
            products = self.data_loader.get_investment_products(product_type, risk_level)
            
            # 응답 생성
            result = {
                "products": products,
                "total_count": len(products),
                "filters": {
                    "product_type": product_type,
                    "risk_level": risk_level
                }
            }
            
            response = self.create_success_response(result)
            self.log_output(response)
            return response
            
        except Exception as e:
            return self.handle_error(e, request)


class SubscribeInvestmentProductTool(BaseTool):
    """투자상품 가입 도구"""
    
    def __init__(self):
        """투자상품 가입 도구를 초기화합니다."""
        super().__init__("subscribe_investment_product")
    
    def execute(self, request: ToolRequest) -> ToolResponse:
        """투자상품에 가입합니다."""
        try:
            self.log_input(request)
            
            # 파라미터 검증
            product_id = request.parameters.get("product_id")
            customer_id = request.parameters.get("customer_id")
            amount = request.parameters.get("amount")
            
            if not all([product_id, customer_id, amount]):
                return self.create_error_response("상품 ID, 고객 ID, 투자 금액이 모두 필요합니다.")
            
            # 투자상품 가입 (실제로는 데이터베이스 업데이트)
            result = {
                "status": "success",
                "message": f"투자상품 가입이 성공적으로 완료되었습니다. (상품: {product_id}, 금액: {amount}원)",
                "subscription_id": f"SUB_{customer_id}_{product_id}_{amount}",
                "product_id": product_id,
                "customer_id": customer_id,
                "amount": amount
            }
            
            response = self.create_success_response(result)
            self.log_output(response)
            return response
            
        except Exception as e:
            return self.handle_error(e, request)


class InvestmentTools:
    """투자상품 도구 모음"""
    
    def __init__(self):
        """투자상품 도구들을 초기화합니다."""
        self.get_investment_products = GetInvestmentProductsTool()
        self.subscribe_investment_product = SubscribeInvestmentProductTool()
    
    def get_tools(self) -> Dict[str, BaseTool]:
        """도구들을 반환합니다."""
        return {
            "get_investment_products": self.get_investment_products,
            "subscribe_investment_product": self.subscribe_investment_product
        } 