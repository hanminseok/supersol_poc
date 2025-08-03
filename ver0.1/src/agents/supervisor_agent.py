import re
from typing import Dict, Any
from ..models.agent_models import AgentRequest, AgentResponse, AgentType, DomainType
from ..utils.llm_client import OpenAIClient
from ..Config import config
from .base_agent import BaseAgent


class SupervisorAgent(BaseAgent):
    """
    Supervisor 에이전트 클래스
    
    최상위 의사결정자로서 사용자 질문을 분석하고 적절한 도메인 에이전트에게 작업을 위임합니다.
    OpenAI GPT-4o 모델을 사용하여 컨텍스트 분석 및 도메인 결정을 수행합니다.
    
    Attributes:
        llm_client (OpenAIClient): OpenAI API 클라이언트
        prompt_loader: 프롬프트 로더 인스턴스
        logger: 로깅 인스턴스
    """
    
    def __init__(self):
        """
        Supervisor 에이전트를 초기화합니다.
        
        OpenAI GPT-4o 모델을 사용하여 LLM 클라이언트를 설정합니다.
        """
        super().__init__(AgentType.SUPERVISOR)
        self.llm_client = OpenAIClient(config.SUPERVISOR_MODEL)
    
    def process(self, request: AgentRequest) -> AgentResponse:
        """
        사용자 요청을 처리하고 적절한 도메인을 결정합니다.
        
        Args:
            request (AgentRequest): 처리할 에이전트 요청
            
        Returns:
            AgentResponse: 도메인 결정 결과와 위임 정보
            
        Raises:
            Exception: 처리 중 오류 발생 시
        """
        try:
            self.log_input(request)
            
            # 컨텍스트 추출
            context = self._extract_context(request)
            
            # LLM을 사용한 도메인 결정
            domain, reasoning = self._determine_domain(request, context)
            
            response = self.create_response(
                response=f"도메인 '{domain}'으로 작업을 위임합니다.",
                domain=DomainType(domain),
                reasoning=reasoning
            )
            
            self.log_output(response)
            return response
            
        except Exception as e:
            return self.handle_error(e, request)
    
    def _extract_context(self, request: AgentRequest) -> str:
        """컨텍스트를 추출합니다."""
        context_parts = []
        
        # 의도 기반 컨텍스트
        if request.intent_classification:
            intent = request.intent_classification.intent
            confidence = request.intent_classification.confidence
            
            if intent != "기타":
                context_parts.append(f"사용자 의도: {intent} (신뢰도: {confidence:.2f})")
            
            # 슬롯 기반 컨텍스트
            if request.intent_classification.slots:
                slot_contexts = []
                for key, value in request.intent_classification.slots.items():
                    slot_contexts.append(f"{key}: {value}")
                context_parts.append(f"추출된 정보: {', '.join(slot_contexts)}")
        
        # 대화 히스토리 기반 컨텍스트
        if request.conversation_history:
            context_parts.append(f"대화 히스토리: {len(request.conversation_history)}개 메시지")
        
        return "; ".join(context_parts) if context_parts else "일반적인 질의"
    
    def _determine_domain(self, request: AgentRequest, context: str) -> tuple[str, str]:
        """도메인을 결정합니다."""
        try:
            # 프롬프트 로드 및 포맷팅
            prompt = self.prompt_loader.format_prompt(
                "agent_prompt.json",
                "supervisor",
                user_query=request.user_query,
                conversation_history="\n".join(request.conversation_history[-3:]),  # 최근 3개만
                context=context,
                intent=request.intent_classification.intent if request.intent_classification else "기타",
                slots=str(request.intent_classification.slots) if request.intent_classification else "{}",
                domain="미정"  # 초기에는 미정으로 설정
            )
            
            # LLM 호출
            response = self.llm_client.generate(
                system_prompt=prompt["system"],
                user_prompt=prompt["user"]
            )
            
            # 응답 파싱
            domain, reasoning = self._parse_domain_response(response)
            
            return domain, reasoning
            
        except Exception as e:
            self.logger.log_error_with_context(e, "SupervisorAgent._determine_domain")
            return "banking", "기본 도메인으로 설정"
    
    def _parse_domain_response(self, response: str) -> tuple[str, str]:
        """도메인 응답을 파싱합니다."""
        domain = "banking"  # 기본값
        reasoning = "기본 도메인으로 설정"
        
        try:
            # 도메인 추출
            domain_match = re.search(r'도메인:\s*(\w+)', response, re.IGNORECASE)
            if domain_match:
                domain = domain_match.group(1).lower()
            
            # 이유 추출
            reason_match = re.search(r'이유:\s*(.+)', response, re.DOTALL)
            if reason_match:
                reasoning = reason_match.group(1).strip()
            
            # 도메인 검증
            if domain not in ["banking", "asset_management"]:
                domain = "banking"
                reasoning = "유효하지 않은 도메인으로 인해 기본 도메인으로 설정"
                
        except Exception as e:
            self.logger.log_error_with_context(e, "SupervisorAgent._parse_domain_response")
        
        return domain, reasoning 