import json
from typing import List, Dict, Any
from ..Config import config
from ..logger import preprocessing_logger
from ..utils.llm_client import DeepInfraClient


class QueryRewriter:
    """질의 재작성 클래스"""
    
    def __init__(self):
        """질의 재작성기를 초기화합니다."""
        self.llm_client = DeepInfraClient(config.REWRITING_MODEL)
        self.logger = preprocessing_logger
    
    def rewrite(self, query: str, conversation_history: List[str] = None) -> str:
        """질의를 재작성합니다."""
        try:
            self.logger.info(f"질의 재작성 시작: {query[:50]}...")
            
            if conversation_history is None:
                conversation_history = []
            
            # LLM을 사용한 질의 재작성
            rewritten_query = self._llm_rewrite(query, conversation_history)
            
            self.logger.info(f"질의 재작성 완료: {rewritten_query[:50]}...")
            return rewritten_query
            
        except Exception as e:
            self.logger.log_error_with_context(e, "QueryRewriter.rewrite")
            return query  # 에러 시 원본 질의 반환
    
    def _llm_rewrite(self, query: str, conversation_history: List[str]) -> str:
        """LLM을 사용한 질의 재작성을 수행합니다."""
        try:
            # 프롬프트 로드
            with open(f"{config.PROMPTS_DIR}/preprocessing_prompt.json", 'r', encoding='utf-8') as f:
                prompts = json.load(f)
            
            prompt_data = prompts["query_rewriting"]
            
            # 대화 히스토리 포맷팅
            history_text = ""
            if conversation_history:
                history_text = "\n".join([f"- {msg}" for msg in conversation_history[-5:]])  # 최근 5개만 사용
            
            # 프롬프트 구성
            system_prompt = prompt_data["system"]
            user_prompt = prompt_data["user"].format(
                conversation_history=history_text,
                current_query=query
            )
            
            # LLM 호출
            response = self.llm_client.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt
            )
            
            # 응답 파싱
            if "재작성된 질의:" in response:
                rewritten_query = response.split("재작성된 질의:")[1].strip()
                return rewritten_query
            else:
                return query
                
        except Exception as e:
            self.logger.log_error_with_context(e, "QueryRewriter._llm_rewrite")
            return query 