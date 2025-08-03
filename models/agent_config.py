import json
import os
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class InputFormat(BaseModel):
    type: str
    schema: Dict[str, Any]
    context: Optional[Dict[str, Any]] = None

class OutputFormat(BaseModel):
    type: str
    schema: Dict[str, Any]
    context: Optional[Dict[str, Any]] = None

class FallbackStrategy(BaseModel):
    max_context_depth: int = 3
    missing_input: Dict[str, Any]
    tool_failure: Dict[str, Any]
    no_tool_found: Dict[str, Any]

class AgentConfig(BaseModel):
    name: str
    type: str
    description: str
    prompt: str
    role: str
    next_agent: list
    model: str
    model_provider: str
    temperature: float = 0.7
    language: str = "ko"
    style: str = "formal"
    max_retries: int = 3
    retry_delay: int = 1
    retry_delay_max: int = 10
    retry_delay_min: int = 1
    input_format: Optional[InputFormat] = None
    output_format: Optional[OutputFormat] = None
    domain_list: Optional[list] = None
    tool_list: Optional[list] = None
    fallback_strategy: Optional[FallbackStrategy] = None
    expected_output: Optional[str] = None

class AgentConfigManager:
    def __init__(self, config_dir: str = "config/agents"):
        self.config_dir = config_dir
        self._configs: Dict[str, AgentConfig] = {}
        self._load_configs()
    
    def _load_configs(self):
        """JSON 파일에서 Agent 설정들을 로드"""
        if not os.path.exists(self.config_dir):
            raise FileNotFoundError(f"Agent config directory not found: {self.config_dir}")
        
        for filename in os.listdir(self.config_dir):
            if filename.endswith('.json') and filename != 'tools.json':  # tools.json 제외
                agent_name = filename[:-5]  # .json 제거
                config_path = os.path.join(self.config_dir, filename)
                
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config_data = json.load(f)
                    
                    # Pydantic 모델로 변환
                    agent_config = AgentConfig(**config_data)
                    self._configs[agent_name] = agent_config
                    
                except Exception as e:
                    print(f"Error loading config for {agent_name}: {str(e)}")
    
    def get_config(self, agent_name: str) -> Optional[AgentConfig]:
        """Agent 설정 조회"""
        return self._configs.get(agent_name)
    
    def get_all_configs(self) -> Dict[str, AgentConfig]:
        """모든 Agent 설정 조회"""
        return self._configs.copy()
    
    def list_agents(self) -> list:
        """사용 가능한 Agent 목록 조회"""
        return list(self._configs.keys())
    
    def reload_configs(self):
        """설정 파일들을 다시 로드"""
        self._configs.clear()
        self._load_configs()

# 전역 Agent 설정 관리자 인스턴스
agent_config_manager = AgentConfigManager()

# 편의 함수들
def get_agent_config(agent_name: str) -> Optional[AgentConfig]:
    """Agent 설정 조회 편의 함수"""
    return agent_config_manager.get_config(agent_name)

def get_all_agent_configs() -> Dict[str, AgentConfig]:
    """모든 Agent 설정 조회 편의 함수"""
    return agent_config_manager.get_all_configs()

def list_available_agents() -> list:
    """사용 가능한 Agent 목록 조회 편의 함수"""
    return agent_config_manager.list_agents() 