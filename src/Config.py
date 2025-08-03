import os
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()


# 상수 정의
class Constants:
    """시스템 상수 정의"""
    
    # 로그 관련 상수
    LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT = 5
    LOG_ENCODING = 'utf-8'
    
    # 응답 시간 제한
    RESPONSE_TIMEOUT = 5  # 5초
    
    # 응답 관련 상수
    MAX_RESPONSE_SENTENCES = 3
    MAX_RETRY_ATTEMPTS = 3
    
    # 서버 관련 상수
    DEFAULT_HOST = "0.0.0.0"
    DEFAULT_PORT = 8000
    DEFAULT_DEBUG = True
    
    # 로깅 관련 상수
    DEFAULT_LOG_LEVEL = "INFO"
    LOG_FORMAT = "%(asctime)s [%(levelname)-8s][%(name)-15s] %(message)s"
    LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
    
    # 도메인 상수
    DOMAIN_BANKING = "banking"
    DOMAIN_ASSET_MANAGEMENT = "asset_management"
    
    # 기본 사용자 ID
    DEFAULT_WEB_USER_ID = "web_user"


@dataclass
class Config:
    """환경변수와 설정을 관리하는 클래스"""
    
    # API Keys
    OPENAI_API_KEY: str = ""
    DEEPINFRA_API_KEY: str = ""
    
    # Model Configuration
    SUPERVISOR_MODEL: str = "gpt-4o"
    DOMAIN_MODEL: str = "gpt-4o"
    WORKER_MODEL: str = "Qwen/Qwen3-30B-A3B"
    QUALITY_CHECK_MODEL: str = "gpt-4o"
    
    # Preprocessing Models (DeepInfra 지원 모델명으로 변경)
    NORMALIZATION_MODEL: str = "Qwen/Qwen3-30B-A3B"
    REWRITING_MODEL: str = "Qwen/Qwen3-30B-A3B"
    INTENT_CLASSIFICATION_MODEL: str = "Qwen/Qwen3-30B-A3B"
    
    # Server Configuration
    HOST: str = Constants.DEFAULT_HOST
    PORT: int = Constants.DEFAULT_PORT
    DEBUG: bool = Constants.DEFAULT_DEBUG
    
    # Logging Configuration
    LOG_LEVEL: str = Constants.DEFAULT_LOG_LEVEL
    LOG_FORMAT: str = Constants.LOG_FORMAT
    LOG_DATE_FORMAT: str = Constants.LOG_DATE_FORMAT
    LOG_MAX_BYTES: int = Constants.LOG_MAX_BYTES
    LOG_BACKUP_COUNT: int = Constants.LOG_BACKUP_COUNT
    LOG_ENCODING: str = Constants.LOG_ENCODING
    
    # File Paths
    PROJECT_ROOT: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATA_DIR: str = os.path.join(PROJECT_ROOT, "Data")
    LOGS_DIR: str = os.path.join(PROJECT_ROOT, "logs")
    PROMPTS_DIR: str = os.path.join(PROJECT_ROOT, "src", "prompts")
    
    # Response Configuration
    MAX_RESPONSE_SENTENCES: int = Constants.MAX_RESPONSE_SENTENCES
    MAX_RETRY_ATTEMPTS: int = Constants.MAX_RETRY_ATTEMPTS
    
    def __init__(self):
        """환경변수에서 설정을 로드합니다."""
        self._load_from_env()
    
    def _load_from_env(self) -> None:
        """환경변수에서 설정을 로드합니다."""
        # API Keys
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", self.OPENAI_API_KEY)
        self.DEEPINFRA_API_KEY = os.getenv("DEEPINFRA_API_KEY", self.DEEPINFRA_API_KEY)
        
        # Server Configuration
        self.HOST = os.getenv("HOST", self.HOST)
        self.PORT = int(os.getenv("PORT", str(self.PORT)))
        self.DEBUG = os.getenv("DEBUG", str(self.DEBUG)).lower() == "true"
        
        # Logging Configuration
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", self.LOG_LEVEL)
    
    def validate(self) -> bool:
        """설정의 유효성을 검증합니다."""
        required_fields = [
            "OPENAI_API_KEY",
            "DEEPINFRA_API_KEY"
        ]
        
        for field in required_fields:
            if not getattr(self, field):
                raise ValueError(f"Required configuration field '{field}' is missing or empty")
        
        return True


# 전역 설정 인스턴스
config = Config() 