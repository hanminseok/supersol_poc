import json
import os
from typing import Dict, Any
from ..Config import config
from ..logger import get_logger


class PromptLoader:
    """프롬프트 로더 클래스"""
    
    def __init__(self):
        """프롬프트 로더를 초기화합니다."""
        self.prompts_dir = config.PROMPTS_DIR
        self.logger = get_logger("PromptLoader")
        self._cached_prompts = {}
    
    def load_prompts(self, prompt_file: str) -> Dict[str, Any]:
        """프롬프트 파일을 로드합니다."""
        try:
            # 캐시 확인
            if prompt_file in self._cached_prompts:
                return self._cached_prompts[prompt_file]
            
            file_path = os.path.join(self.prompts_dir, prompt_file)
            
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"프롬프트 파일을 찾을 수 없습니다: {file_path}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                prompts = json.load(f)
            
            # 캐시에 저장
            self._cached_prompts[prompt_file] = prompts
            
            self.logger.debug(f"프롬프트 파일 로드 완료: {prompt_file}")
            return prompts
            
        except Exception as e:
            self.logger.log_error_with_context(e, f"PromptLoader.load_prompts({prompt_file})")
            return {}
    
    def get_prompt(self, prompt_file: str, prompt_key: str) -> Dict[str, str]:
        """특정 프롬프트를 가져옵니다."""
        try:
            prompts = self.load_prompts(prompt_file)
            
            if prompt_key not in prompts:
                raise KeyError(f"프롬프트 키를 찾을 수 없습니다: {prompt_key}")
            
            return prompts[prompt_key]
            
        except Exception as e:
            self.logger.log_error_with_context(e, f"PromptLoader.get_prompt({prompt_file}, {prompt_key})")
            return {
                "system": "시스템 프롬프트를 로드할 수 없습니다.",
                "user": "사용자 프롬프트를 로드할 수 없습니다.",
                "assistant": "어시스턴트 프롬프트를 로드할 수 없습니다."
            }
    
    def format_prompt(self, prompt_file: str, prompt_key: str, **kwargs) -> Dict[str, str]:
        """프롬프트를 포맷팅합니다."""
        try:
            prompt_template = self.get_prompt(prompt_file, prompt_key)
            formatted_prompt = {}
            
            for key, template in prompt_template.items():
                try:
                    formatted_prompt[key] = template.format(**kwargs)
                except KeyError as e:
                    self.logger.warning(f"프롬프트 포맷팅 중 누락된 키: {e}")
                    formatted_prompt[key] = template
            
            return formatted_prompt
            
        except Exception as e:
            self.logger.log_error_with_context(e, f"PromptLoader.format_prompt({prompt_file}, {prompt_key})")
            return {
                "system": "프롬프트 포맷팅에 실패했습니다.",
                "user": "프롬프트 포맷팅에 실패했습니다.",
                "assistant": "프롬프트 포맷팅에 실패했습니다."
            }
    
    def clear_cache(self) -> None:
        """프롬프트 캐시를 클리어합니다."""
        self._cached_prompts.clear()
        self.logger.debug("프롬프트 캐시 클리어 완료") 