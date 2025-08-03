import re
import json
from typing import Dict, Any
from ..Config import config
from ..logger import preprocessing_logger
from ..utils.llm_client import DeepInfraClient


class TextNormalizer:
    """텍스트 정규화 클래스"""
    
    def __init__(self):
        """텍스트 정규화기를 초기화합니다."""
        self.llm_client = DeepInfraClient(config.NORMALIZATION_MODEL)
        self.logger = preprocessing_logger
    
    def normalize(self, text: str) -> str:
        """텍스트를 정규화합니다."""
        try:
            self.logger.info(f"텍스트 정규화 시작: {text[:50]}...")
            
            # 기본 정규화 (LLM 호출 없이)
            normalized = self._basic_normalize(text)
            
            # LLM을 사용한 고급 정규화
            if len(text) > 10:  # 짧은 텍스트는 기본 정규화만 사용
                normalized = self._llm_normalize(normalized)
            
            self.logger.info(f"텍스트 정규화 완료: {normalized[:50]}...")
            return normalized
            
        except Exception as e:
            self.logger.log_error_with_context(e, "TextNormalizer.normalize")
            return text  # 에러 시 원본 텍스트 반환
    
    def _basic_normalize(self, text: str) -> str:
        """기본 정규화를 수행합니다."""
        # 특수문자 제거 (한글, 영문, 숫자, 공백만 유지)
        text = re.sub(r'[^\w\s가-힣]', '', text)
        
        # 중복 공백 제거
        text = re.sub(r'\s+', ' ', text)
        
        # 앞뒤 공백 제거
        text = text.strip()
        
        # 대소문자 통일 (소문자로)
        text = text.lower()
        
        return text
    
    def _llm_normalize(self, text: str) -> str:
        """LLM을 사용한 고급 정규화를 수행합니다."""
        try:
            # 프롬프트 로드
            with open(f"{config.PROMPTS_DIR}/preprocessing_prompt.json", 'r', encoding='utf-8') as f:
                prompts = json.load(f)
            
            prompt_data = prompts["text_normalization"]
            
            # 프롬프트 구성
            system_prompt = prompt_data["system"]
            user_prompt = prompt_data["user"].format(input_text=text)
            
            # LLM 호출
            response = self.llm_client.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt
            )
            
            # 응답 파싱
            if "정규화된 텍스트:" in response:
                normalized_text = response.split("정규화된 텍스트:")[1].strip()
                return normalized_text
            else:
                return text
                
        except Exception as e:
            self.logger.log_error_with_context(e, "TextNormalizer._llm_normalize")
            return text 