from typing import Dict, Any, List
from .base_tool import BaseTool
from .customer_info_tools import CustomerInfoTools
from .financial_info_tools import FinancialInfoTools
from .transfer_tools import TransferTools
from .account_tools import AccountTools
from .auto_transfer_tools import AutoTransferTools
from .investment_tools import InvestmentTools
from .loan_tools import LoanTools


class ToolManager:
    """도구 관리자 클래스"""
    
    def __init__(self):
        """도구 관리자를 초기화합니다."""
        self.tools: Dict[str, BaseTool] = {}
        self._initialize_tools()
    
    def _initialize_tools(self) -> None:
        """모든 도구들을 초기화합니다."""
        # 고객정보 도구들
        customer_tools = CustomerInfoTools()
        self.tools.update(customer_tools.get_tools())
        
        # 금융정보 도구들
        financial_tools = FinancialInfoTools()
        self.tools.update(financial_tools.get_tools())
        
        # 이체 도구들
        transfer_tools = TransferTools()
        self.tools.update(transfer_tools.get_tools())
        
        # 계좌 도구들
        account_tools = AccountTools()
        self.tools.update(account_tools.get_tools())
        
        # 자동이체 도구들
        auto_transfer_tools = AutoTransferTools()
        self.tools.update(auto_transfer_tools.get_tools())
        
        # 투자상품 도구들
        investment_tools = InvestmentTools()
        self.tools.update(investment_tools.get_tools())
        
        # 대출 도구들
        loan_tools = LoanTools()
        self.tools.update(loan_tools.get_tools())
    
    def get_tool(self, tool_name: str) -> BaseTool:
        """지정된 이름의 도구를 반환합니다."""
        return self.tools.get(tool_name)
    
    def get_all_tools(self) -> Dict[str, BaseTool]:
        """모든 도구를 반환합니다."""
        return self.tools.copy()
    
    def get_tool_names(self) -> List[str]:
        """모든 도구 이름을 반환합니다."""
        return list(self.tools.keys())
    
    def get_tools_by_category(self, category: str) -> Dict[str, BaseTool]:
        """카테고리별 도구를 반환합니다."""
        category_tools = {}
        
        for tool_name, tool in self.tools.items():
            if tool_name.startswith(category):
                category_tools[tool_name] = tool
        
        return category_tools
    
    def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """도구를 실행합니다."""
        tool = self.get_tool(tool_name)
        
        if not tool:
            raise ValueError(f"도구 '{tool_name}'를 찾을 수 없습니다.")
        
        from ..models.tool_models import ToolRequest
        request = ToolRequest(
            tool_name=tool_name,
            parameters=parameters
        )
        
        response = tool.execute(request)
        return response
    
    def get_tool_info(self, tool_name: str) -> Dict[str, Any]:
        """도구 정보를 반환합니다."""
        tool = self.get_tool(tool_name)
        
        if not tool:
            return {}
        
        return {
            "name": tool.tool_name,
            "type": type(tool).__name__,
            "description": getattr(tool, 'description', '설명 없음')
        }
    
    def get_all_tool_info(self) -> Dict[str, Dict[str, Any]]:
        """모든 도구 정보를 반환합니다."""
        tool_info = {}
        
        for tool_name in self.get_tool_names():
            tool_info[tool_name] = self.get_tool_info(tool_name)
        
        return tool_info 