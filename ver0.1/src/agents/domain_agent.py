import re
from typing import Dict, Any
from ..models.agent_models import AgentRequest, AgentResponse, AgentType, DomainType
from ..utils.llm_client import OpenAIClient
from ..Config import config
from .base_agent import BaseAgent


class DomainAgent(BaseAgent):
    """Domain 에이전트 클래스"""
    
    def __init__(self, domain_type: DomainType):
        """Domain 에이전트를 초기화합니다."""
        super().__init__(AgentType(f"domain_{domain_type.value}"))
        self.domain_type = domain_type
        self.llm_client = OpenAIClient(config.DOMAIN_MODEL)
    
    def process(self, request: AgentRequest) -> AgentResponse:
        """요청을 처리합니다."""
        try:
            self.log_input(request)
            
            # LLM을 사용한 작업자 결정
            worker, reasoning = self._determine_worker(request)
            
            response = self.create_response(
                response=f"도메인 '{self.domain_type.value}'에서 작업자 '{worker}'로 작업을 위임합니다.",
                domain=self.domain_type,
                worker=worker,
                reasoning=reasoning
            )
            
            self.log_output(response)
            return response
            
        except Exception as e:
            return self.handle_error(e, request)
    
    def _determine_worker(self, request: AgentRequest) -> tuple[str, str]:
        """작업자를 결정합니다."""
        try:
            # 프롬프트 키 결정
            prompt_key = f"domain_{self.domain_type.value}"
            
            # 프롬프트 로드 및 포맷팅
            prompt = self.prompt_loader.format_prompt(
                "agent_prompt.json",
                prompt_key,
                user_query=request.user_query,
                intent=request.intent_classification.intent if request.intent_classification else "기타",
                slots=str(request.intent_classification.slots) if request.intent_classification else "{}",
                worker="미정",  # 초기에는 미정으로 설정
                reasoning="분석 중"  # 초기에는 분석 중으로 설정
            )
            
            # LLM 호출
            response = self.llm_client.generate(
                system_prompt=prompt["system"],
                user_prompt=prompt["user"]
            )
            
            # 응답 파싱
            worker, reasoning = self._parse_worker_response(response)
            
            return worker, reasoning
            
        except Exception as e:
            self.logger.log_error_with_context(e, f"DomainAgent._determine_worker({self.domain_type.value})")
            return "customer_info", "기본 작업자로 설정"
    
    def _parse_worker_response(self, response: str) -> tuple[str, str]:
        """작업자 응답을 파싱합니다."""
        worker = "customer_info"  # 기본값
        reasoning = "기본 작업자로 설정"
        
        try:
            # 작업자 추출
            worker_match = re.search(r'작업자:\s*(\w+)', response, re.IGNORECASE)
            if worker_match:
                worker = worker_match.group(1).lower()
            
            # 이유 추출
            reason_match = re.search(r'이유:\s*(.+)', response, re.DOTALL)
            if reason_match:
                reasoning = reason_match.group(1).strip()
            
            # 작업자 검증
            valid_workers = self._get_valid_workers()
            if worker not in valid_workers:
                worker = valid_workers[0] if valid_workers else "customer_info"
                reasoning = "유효하지 않은 작업자로 인해 기본 작업자로 설정"
                
        except Exception as e:
            self.logger.log_error_with_context(e, "DomainAgent._parse_worker_response")
        
        return worker, reasoning
    
    def _get_valid_workers(self) -> list[str]:
        """유효한 작업자 목록을 반환합니다."""
        if self.domain_type == DomainType.BANKING:
            return ["customer_info", "financial_info", "transfer", "account", "auto_transfer"]
        elif self.domain_type == DomainType.ASSET_MANAGEMENT:
            return ["investment_products", "loan"]
        else:
            return ["customer_info"] 