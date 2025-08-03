import re
from typing import Dict, Any, List
from ..models.agent_models import AgentRequest, AgentResponse, AgentType
from ..models.tool_models import ToolRequest, ToolResponse
from ..utils.llm_client import DeepInfraClient
from ..Config import config
from ..tools import (
    CustomerInfoTools, FinancialInfoTools, TransferTools, 
    AccountTools, AutoTransferTools, InvestmentTools, LoanTools
)
from .base_agent import BaseAgent


class WorkerAgent(BaseAgent):
    """Worker 에이전트 클래스"""
    
    def __init__(self, worker_type: str):
        """Worker 에이전트를 초기화합니다."""
        super().__init__(AgentType(f"worker_{worker_type}"))
        self.worker_type = worker_type
        self.llm_client = DeepInfraClient(config.WORKER_MODEL)
        self.tools = self._initialize_tools()
    
    def process(self, request: AgentRequest) -> AgentResponse:
        """요청을 처리합니다."""
        try:
            self.log_input(request)
            
            # LLM을 사용한 도구 호출 결정
            tool_calls, response_text = self._determine_tool_calls(request)
            
            # 도구 실행
            tool_results = self._execute_tools(tool_calls)
            
            # 최종 응답 생성
            final_response = self._generate_final_response(request, tool_results, response_text)
            
            response = self.create_response(
                response=final_response,
                tool_calls=tool_calls,
                reasoning=f"작업자 '{self.worker_type}'가 {len(tool_calls)}개의 도구를 호출했습니다."
            )
            
            self.log_output(response)
            return response
            
        except Exception as e:
            return self.handle_error(e, request)
    
    def _initialize_tools(self) -> Dict[str, Any]:
        """도구들을 초기화합니다."""
        tools = {}
        
        # 고객정보 도구들
        customer_tools = CustomerInfoTools()
        tools.update(customer_tools.get_tools())
        
        # 금융정보 도구들
        financial_tools = FinancialInfoTools()
        tools.update(financial_tools.get_tools())
        
        # 이체 도구들
        transfer_tools = TransferTools()
        tools.update(transfer_tools.get_tools())
        
        # 계좌 도구들
        account_tools = AccountTools()
        tools.update(account_tools.get_tools())
        
        # 자동이체 도구들
        auto_transfer_tools = AutoTransferTools()
        tools.update(auto_transfer_tools.get_tools())
        
        # 투자상품 도구들
        investment_tools = InvestmentTools()
        tools.update(investment_tools.get_tools())
        
        # 대출 도구들
        loan_tools = LoanTools()
        tools.update(loan_tools.get_tools())
        
        return tools
    
    def _determine_tool_calls(self, request: AgentRequest) -> tuple[List[Dict[str, Any]], str]:
        """도구 호출을 결정합니다."""
        try:
            # 프롬프트 로드 및 포맷팅
            prompt = self.prompt_loader.format_prompt(
                "agent_prompt.json",
                f"worker_{self.worker_type}",
                user_query=request.user_query,
                intent=request.intent_classification.intent if request.intent_classification else "기타",
                slots=str(request.intent_classification.slots) if request.intent_classification else "{}"
            )
            
            # LLM 호출
            response = self.llm_client.generate(
                system_prompt=prompt["system"],
                user_prompt=prompt["user"]
            )
            
            # 응답 파싱
            tool_calls, response_text = self._parse_tool_response(response)
            
            return tool_calls, response_text
            
        except Exception as e:
            self.logger.log_error_with_context(e, f"WorkerAgent._determine_tool_calls({self.worker_type})")
            return [], "도구 호출을 결정할 수 없습니다."
    
    def _parse_tool_response(self, response: str) -> tuple[List[Dict[str, Any]], str]:
        """도구 응답을 파싱합니다."""
        tool_calls = []
        response_text = response
        
        try:
            # 도구 호출 추출 (간단한 구현)
            if "도구 호출:" in response:
                tool_section = response.split("도구 호출:")[1].split("응답:")[0].strip()
                response_text = response.split("응답:")[1].strip() if "응답:" in response else response
                
                # 간단한 도구 호출 파싱
                tool_calls = self._parse_tool_calls(tool_section)
                
        except Exception as e:
            self.logger.log_error_with_context(e, "WorkerAgent._parse_tool_response")
        
        return tool_calls, response_text
    
    def _parse_tool_calls(self, tool_section: str) -> List[Dict[str, Any]]:
        """도구 호출 섹션을 파싱합니다."""
        tool_calls = []
        
        try:
            # 간단한 키워드 기반 파싱
            if "get_customer_info" in tool_section.lower():
                # 고객 ID 추출 시도
                import re
                customer_id_match = re.search(r'customer_id[:\s]*(\w+)', tool_section, re.IGNORECASE)
                customer_id = customer_id_match.group(1) if customer_id_match else "default_customer"
                
                tool_calls.append({
                    "tool_name": "get_customer_info",
                    "parameters": {"customer_id": customer_id}
                })
                
        except Exception as e:
            self.logger.log_error_with_context(e, "WorkerAgent._parse_tool_calls")
        
        return tool_calls
    
    def _execute_tools(self, tool_calls: List[Dict[str, Any]]) -> List[ToolResponse]:
        """도구들을 실행합니다."""
        results = []
        
        for tool_call in tool_calls:
            try:
                tool_name = tool_call.get("tool_name")
                parameters = tool_call.get("parameters", {})
                
                if tool_name in self.tools:
                    tool = self.tools[tool_name]
                    tool_request = ToolRequest(
                        tool_name=tool_name,
                        parameters=parameters
                    )
                    
                    tool_response = tool.execute(tool_request)
                    results.append(tool_response)
                else:
                    # 도구가 없는 경우 에러 응답 생성
                    error_response = ToolResponse.create_error_response(
                        tool_name,
                        f"도구 '{tool_name}'를 찾을 수 없습니다."
                    )
                    results.append(error_response)
                    
            except Exception as e:
                self.logger.log_error_with_context(e, f"WorkerAgent._execute_tools({tool_call})")
                error_response = ToolResponse.create_error_response(
                    tool_call.get("tool_name", "unknown"),
                    str(e)
                )
                results.append(error_response)
        
        return results
    
    def _generate_final_response(self, request: AgentRequest, tool_results: List[ToolResponse], base_response: str) -> str:
        """최종 응답을 생성합니다."""
        try:
            # 도구 실행 결과가 있는 경우
            if tool_results:
                successful_results = [r for r in tool_results if r.success]
                
                if successful_results:
                    # 성공한 결과들을 기반으로 응답 생성
                    result_summary = []
                    for result in successful_results:
                        if result.result:
                            result_summary.append(f"{result.tool_name}: {str(result.result)}")
                    
                    if result_summary:
                        return f"요청하신 정보입니다: {'; '.join(result_summary)}"
                
                # 실패한 결과가 있는 경우
                failed_results = [r for r in tool_results if not r.success]
                if failed_results:
                    error_messages = [f"{r.tool_name}: {r.error_message}" for r in failed_results]
                    return f"일부 정보를 가져올 수 없었습니다: {'; '.join(error_messages)}"
            
            # 기본 응답 반환
            return base_response if base_response else "요청을 처리했습니다."
            
        except Exception as e:
            self.logger.log_error_with_context(e, "WorkerAgent._generate_final_response")
            return "응답을 생성하는 중 오류가 발생했습니다." 