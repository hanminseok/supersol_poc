import asyncio
import json
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import openai
import deepinfra
from Config import Config
from utils.logger import agent_logger
from models.agent_config import AgentConfig

class BaseAgent(ABC):
    def __init__(self, config: AgentConfig):
        self.config = config
        self.logger = agent_logger
        self._setup_client()
    
    def _setup_client(self):
        """API 클라이언트 설정"""
        if self.config.model_provider == "openai":
            self.client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)
        elif self.config.model_provider == "deepinfra":
            self.client = deepinfra.Client(api_token=Config.DEEPINFRA_API_KEY)
        else:
            raise ValueError(f"Unsupported model provider: {self.config.model_provider}")
    
    async def execute(self, input_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Agent 실행 메인 메서드"""
        self.logger.info(f"Starting {self.config.name} execution")
        
        for attempt in range(self.config.max_retries):
            try:
                # 입력 데이터 검증
                validated_input = self._validate_input(input_data)
                
                # Agent별 처리 로직 실행
                result = await self._process(validated_input, context)
                
                # 출력 데이터 검증
                validated_output = self._validate_output(result)
                
                self.logger.info(f"{self.config.name} execution completed successfully")
                return validated_output
                
            except Exception as e:
                self.logger.error(f"{self.config.name} execution failed (attempt {attempt + 1}/{self.config.max_retries}): {str(e)}")
                
                if attempt < self.config.max_retries - 1:
                    delay = min(
                        self.config.retry_delay * (2 ** attempt),
                        self.config.retry_delay_max
                    )
                    await asyncio.sleep(delay)
                else:
                    raise e
    
    def _validate_input(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """입력 데이터 검증"""
        if self.config.input_format:
            # 기본 검증 로직 (실제로는 더 복잡한 검증이 필요)
            required_fields = list(self.config.input_format.schema.keys())
            for field in required_fields:
                if field not in input_data:
                    raise ValueError(f"Missing required field: {field}")
        
        return input_data
    
    def _validate_output(self, output_data: Dict[str, Any]) -> Dict[str, Any]:
        """출력 데이터 검증"""
        if self.config.output_format:
            # 기본 검증 로직 (실제로는 더 복잡한 검증이 필요)
            required_fields = list(self.config.output_format.schema.keys())
            for field in required_fields:
                if field not in output_data:
                    raise ValueError(f"Missing required output field: {field}")
        
        return output_data
    
    async def _call_llm(self, messages: List[Dict[str, str]], stream: bool = False):
        """LLM 호출"""
        try:
            if self.config.model_provider == "openai":
                if stream:
                    response = await self.client.chat.completions.create(
                        model=self.config.model,
                        messages=messages,
                        temperature=self.config.temperature,
                        stream=True
                    )
                    return response
                else:
                    response = await self.client.chat.completions.create(
                        model=self.config.model,
                        messages=messages,
                        temperature=self.config.temperature
                    )
                    return response.choices[0].message.content
                    
            elif self.config.model_provider == "deepinfra":
                # DeepInfra API 호출 로직
                response = await self.client.chat.completions.create(
                    model=self.config.model,
                    messages=messages,
                    temperature=self.config.temperature
                )
                return response.choices[0].message.content
                
        except Exception as e:
            self.logger.error(f"LLM call failed: {str(e)}")
            raise e
    
    @abstractmethod
    async def _process(self, input_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Agent별 구체적인 처리 로직 (하위 클래스에서 구현)"""
        pass
    
    def _create_system_message(self) -> Dict[str, str]:
        """시스템 메시지 생성"""
        return {
            "role": "system",
            "content": self.config.prompt
        }
    
    def _create_user_message(self, content: str) -> Dict[str, str]:
        """사용자 메시지 생성"""
        return {
            "role": "user",
            "content": content
        } 