import json
import time
from typing import Dict, Any, Optional
import openai
import requests
from ..Config import config
from ..logger import get_logger


class OpenAIClient:
    """OpenAI API 클라이언트"""
    
    def __init__(self, model: str = None):
        """OpenAI 클라이언트를 초기화합니다."""
        self.model = model or "gpt-4o"
        self.client = openai.OpenAI(api_key=config.OPENAI_API_KEY)
        self.logger = get_logger("OpenAIClient")
    
    def generate(self, system_prompt: str, user_prompt: str, max_retries: int = 3) -> str:
        """텍스트를 생성합니다."""
        for attempt in range(max_retries):
            try:
                self.logger.debug(f"OpenAI API 호출 시도 {attempt + 1}/{max_retries}")
                
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_tokens=1000,
                    temperature=0.1
                )
                
                result = response.choices[0].message.content
                self.logger.debug(f"OpenAI API 응답 성공: {result[:100]}...")
                return result
                
            except Exception as e:
                self.logger.error(f"OpenAI API 호출 실패 (시도 {attempt + 1}): {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # 지수 백오프
                else:
                    raise e
        
        return "응답을 생성할 수 없습니다."


class DeepInfraClient:
    """DeepInfra API 클라이언트"""
    
    def __init__(self, model: str):
        """DeepInfra 클라이언트를 초기화합니다."""
        self.model = model
        self.api_key = config.DEEPINFRA_API_KEY
        self.base_url = "https://api.deepinfra.com/v1/openai"
        self.logger = get_logger("DeepInfraClient")
    
    def generate(self, system_prompt: str, user_prompt: str, max_retries: int = 3) -> str:
        """텍스트를 생성합니다."""
        for attempt in range(max_retries):
            try:
                self.logger.debug(f"DeepInfra API 호출 시도 {attempt + 1}/{max_retries}")
                
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                
                data = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "max_tokens": 1000,
                    "temperature": 0.1
                }
                
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()["choices"][0]["message"]["content"]
                    self.logger.debug(f"DeepInfra API 응답 성공: {result[:100]}...")
                    return result
                else:
                    self.logger.error(f"DeepInfra API 오류: {response.status_code} - {response.text}")
                    
            except Exception as e:
                self.logger.error(f"DeepInfra API 호출 실패 (시도 {attempt + 1}): {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # 지수 백오프
                else:
                    raise e
        
        return "응답을 생성할 수 없습니다." 