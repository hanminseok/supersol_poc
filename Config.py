import os
from dotenv import load_dotenv
from pathlib import Path

# .env 파일 경로 설정
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
    print(f"Loaded environment variables from: {env_path}")
else:
    print(f"Warning: .env file not found at {env_path}")
    print("Please copy env.example to .env and configure your settings")

class Config:
    # API Keys
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
    DEEPINFRA_API_KEY = os.getenv('DEEPINFRA_API_KEY', '')
    
    # 서버 설정
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', 8000))
    
    # 로깅 설정
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT = "%(asctime)s [%(levelname)-8s][%(name)-15s] %(message)s"
    LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
    
    # 세션 설정
    MAX_SESSION_HISTORY = int(os.getenv('MAX_SESSION_HISTORY', 100))
    SESSION_DIR = os.getenv('SESSION_DIR', 'sessions')
    
    # 모델 설정
    DEFAULT_MODEL = os.getenv('DEFAULT_MODEL', 'gpt-4')
    DEFAULT_PROVIDER = os.getenv('DEFAULT_PROVIDER', 'openai')
    
    # Agent 설정
    MAX_RETRIES = int(os.getenv('MAX_RETRIES', 3))
    RETRY_DELAY = int(os.getenv('RETRY_DELAY', 1))
    RETRY_DELAY_MAX = int(os.getenv('RETRY_DELAY_MAX', 10))
    RETRY_DELAY_MIN = int(os.getenv('RETRY_DELAY_MIN', 1))
    
    # Supervisor 설정
    MAX_CONTEXT_DEPTH = int(os.getenv('MAX_CONTEXT_DEPTH', 3))
    TOOL_RETRY_ON_FAILURE = os.getenv('TOOL_RETRY_ON_FAILURE', 'true').lower() == 'true'
    TOOL_MAX_RETRIES = int(os.getenv('TOOL_MAX_RETRIES', 2)) 