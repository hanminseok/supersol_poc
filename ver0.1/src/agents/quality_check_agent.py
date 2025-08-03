import re
from typing import Dict, Any
from ..models.agent_models import AgentRequest, AgentResponse, AgentType
from ..utils.llm_client import OpenAIClient
from ..Config import config
from .base_agent import BaseAgent


class QualityCheckAgent(BaseAgent):
    """답변 품질 점검 에이전트 클래스"""
    
    def __init__(self):
        """Quality Check 에이전트를 초기화합니다."""
        super().__init__(AgentType.QUALITY_CHECK)
        self.llm_client = OpenAIClient(config.QUALITY_CHECK_MODEL)
    
    def process(self, request: AgentRequest) -> AgentResponse:
        """요청을 처리합니다."""
        try:
            self.log_input(request)
            
            # 품질 점검 수행
            quality_score, improvement_suggestions = self._check_quality(request)
            
            # 개선 제안이 있는 경우 태그 추가
            response_text = request.user_query
            if improvement_suggestions:
                response_text = f"[답변점검Agent] {improvement_suggestions}\n\n{request.user_query}"
            
            response = self.create_response(
                response=response_text,
                reasoning=f"품질 점수: {quality_score}, 개선 제안: {improvement_suggestions}"
            )
            
            self.log_output(response)
            return response
            
        except Exception as e:
            return self.handle_error(e, request)
    
    def _check_quality(self, request: AgentRequest) -> tuple[float, str]:
        """답변 품질을 점검합니다."""
        try:
            # 프롬프트 로드 및 포맷팅
            prompt = self.prompt_loader.format_prompt(
                "agent_prompt.json",
                "quality_check",
                agent_response=request.user_query,
                user_query=request.user_query
            )
            
            # LLM 호출
            response = self.llm_client.generate(
                system_prompt=prompt["system"],
                user_prompt=prompt["user"]
            )
            
            # 응답 파싱
            quality_score, improvement_suggestions = self._parse_quality_response(response)
            
            return quality_score, improvement_suggestions
            
        except Exception as e:
            self.logger.log_error_with_context(e, "QualityCheckAgent._check_quality")
            return 0.5, "품질 점검을 수행할 수 없습니다."
    
    def _parse_quality_response(self, response: str) -> tuple[float, str]:
        """품질 점검 응답을 파싱합니다."""
        quality_score = 0.5  # 기본값
        improvement_suggestions = ""
        
        try:
            # 품질 점수 추출
            score_match = re.search(r'품질 점검 결과:\s*([0-9.]+)', response)
            if score_match:
                quality_score = float(score_match.group(1))
            
            # 개선 권장사항 추출
            suggestions_match = re.search(r'개선 권장사항:\s*(.+)', response, re.DOTALL)
            if suggestions_match:
                improvement_suggestions = suggestions_match.group(1).strip()
            
            # [답변점검Agent] 태그 확인
            if "[답변점검Agent]" in response:
                agent_section = response.split("[답변점검Agent]")[1].split("\n\n")[0].strip()
                improvement_suggestions = agent_section
                
        except Exception as e:
            self.logger.log_error_with_context(e, "QualityCheckAgent._parse_quality_response")
        
        return quality_score, improvement_suggestions
    
    def check_response_quality(self, original_query: str, agent_response: str) -> Dict[str, Any]:
        """응답 품질을 점검합니다."""
        try:
            # 품질 점검 요청 생성
            request = AgentRequest(
                agent_type=AgentType.QUALITY_CHECK,
                user_query=agent_response,  # 여기서는 agent_response를 user_query로 사용
                metadata={"original_query": original_query}
            )
            
            # 품질 점검 수행
            quality_response = self.process(request)
            
            # 결과 구성
            result = {
                "quality_score": 0.5,  # 기본값
                "improvement_suggestions": "",
                "needs_improvement": False,
                "original_response": agent_response,
                "improved_response": quality_response.response
            }
            
            # 품질 점수와 개선 제안 추출
            if quality_response.reasoning:
                reasoning_parts = quality_response.reasoning.split(", ")
                for part in reasoning_parts:
                    if "품질 점수:" in part:
                        try:
                            score_text = part.split(":")[1].strip()
                            result["quality_score"] = float(score_text)
                        except:
                            pass
                    elif "개선 제안:" in part:
                        suggestion_text = part.split(":", 1)[1].strip()
                        result["improvement_suggestions"] = suggestion_text
            
            # 개선 필요 여부 판단
            result["needs_improvement"] = (
                result["quality_score"] < 0.7 or 
                bool(result["improvement_suggestions"])
            )
            
            return result
            
        except Exception as e:
            self.logger.log_error_with_context(e, "QualityCheckAgent.check_response_quality")
            return {
                "quality_score": 0.5,
                "improvement_suggestions": "품질 점검을 수행할 수 없습니다.",
                "needs_improvement": False,
                "original_response": agent_response,
                "improved_response": agent_response
            } 