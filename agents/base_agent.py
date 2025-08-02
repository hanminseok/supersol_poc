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
            # OpenAI 클라이언트 설정
            try:
                self.client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)
            except TypeError as e:
                if "proxies" in str(e):
                    # httpx 버전 호환성 문제 해결
                    import httpx
                    self.client = openai.OpenAI(
                        api_key=Config.OPENAI_API_KEY,
                        http_client=httpx.Client()
                    )
                else:
                    raise e
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
                
                # Agent 입출력 로깅
                self.logger.log_agent_io(
                    agent_name=self.config.name,
                    input_data=validated_input,
                    output_data=validated_output
                )
                
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
        """입력 데이터 검증 - 개선된 버전"""
        if not isinstance(input_data, dict):
            raise ValueError("Input data must be a dictionary")
        
        if self.config.input_format:
            schema = self.config.input_format.schema
            self._validate_schema(input_data, schema, "input")
        
        return input_data
    
    def _validate_output(self, output_data: Dict[str, Any]) -> Dict[str, Any]:
        """출력 데이터 검증 - 개선된 버전"""
        if not isinstance(output_data, dict):
            raise ValueError("Output data must be a dictionary")
        
        if self.config.output_format:
            schema = self.config.output_format.schema
            self._validate_schema(output_data, schema, "output")
        
        return output_data
    
    def _validate_schema(self, data: Dict[str, Any], schema: Dict[str, Any], data_type: str):
        """스키마 검증 - 재귀적으로 중첩 구조 검증"""
        for field_name, field_schema in schema.items():
            if field_name not in data:
                raise ValueError(f"Missing required {data_type} field: {field_name}")
            
            field_value = data[field_name]
            self._validate_field(field_value, field_schema, f"{data_type}.{field_name}")
    
    def _validate_field(self, value: Any, schema: Any, field_path: str):
        """필드 값 검증"""
        if isinstance(schema, list):
            # 리스트 타입 검증
            if not isinstance(value, list):
                raise ValueError(f"Field {field_path} must be a list")
            
            if len(schema) > 0:
                # 리스트 내 요소 타입 검증
                element_schema = schema[0]
                for i, element in enumerate(value):
                    self._validate_field(element, element_schema, f"{field_path}[{i}]")
        
        elif isinstance(schema, dict):
            # 객체 타입 검증
            if not isinstance(value, dict):
                raise ValueError(f"Field {field_path} must be a dictionary")
            
            for key, val in value.items():
                if key in schema:
                    self._validate_field(val, schema[key], f"{field_path}.{key}")
        
        elif schema == "string":
            if not isinstance(value, str):
                raise ValueError(f"Field {field_path} must be a string")
        
        elif schema == "int":
            if not isinstance(value, int):
                raise ValueError(f"Field {field_path} must be an integer")
        
        elif schema == "object":
            if not isinstance(value, dict):
                raise ValueError(f"Field {field_path} must be an object")
    
    async def _call_llm(self, messages: List[Dict[str, str]], stream: bool = False):
        """LLM 호출"""
        try:
            if self.config.model_provider == "openai":
                if stream:
                    response = self.client.chat.completions.create(
                        model=self.config.model,
                        messages=messages,
                        temperature=self.config.temperature,
                        stream=True
                    )
                    return response
                else:
                    response = self.client.chat.completions.create(
                        model=self.config.model,
                        messages=messages,
                        temperature=self.config.temperature
                    )
                    content = response.choices[0].message.content
                    if not content or content.strip() == "":
                        raise ValueError("Empty response from LLM")
                    return content
                    
            elif self.config.model_provider == "deepinfra":
                # DeepInfra API 호출 로직
                response = self.client.chat.completions.create(
                    model=self.config.model,
                    messages=messages,
                    temperature=self.config.temperature
                )
                content = response.choices[0].message.content
                if not content or content.strip() == "":
                    raise ValueError("Empty response from LLM")
                return content
                
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