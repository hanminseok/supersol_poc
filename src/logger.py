import logging
import os
import gzip
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Optional
from .Config import config


class Logger:
    """로깅 시스템을 관리하는 클래스"""
    
    def __init__(self, name: str):
        """로거를 초기화합니다."""
        self.name = name
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, config.LOG_LEVEL))
        
        # 중복 핸들러 방지
        if not self.logger.handlers:
            self._setup_handlers()
    
    def _rotator(self, source, dest):
        """로그 파일을 압축하여 회전시킵니다."""
        if os.path.exists(source):
            with open(source, 'rb') as f_in:
                with gzip.open(dest, 'wb') as f_out:
                    f_out.writelines(f_in)
            os.remove(source)
    
    def _setup_handlers(self) -> None:
        """로깅 핸들러를 설정합니다."""
        # Console Handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            config.LOG_FORMAT,
            datefmt=config.LOG_DATE_FORMAT
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # Agent I/O 로깅 핸들러
        agent_log_path = os.path.join(
            config.LOGS_DIR,
            f"Agent_log_{datetime.now().strftime('%Y%m%d')}.log"
        )
        agent_handler = RotatingFileHandler(
            agent_log_path,
            maxBytes=config.LOG_MAX_BYTES,
            backupCount=config.LOG_BACKUP_COUNT,
            encoding=config.LOG_ENCODING
        )
        # 로그 압축 설정
        agent_handler.namer = lambda name: name + ".gz"
        agent_handler.rotator = self._rotator
        agent_handler.setLevel(logging.DEBUG)
        agent_formatter = logging.Formatter(
            config.LOG_FORMAT,
            datefmt=config.LOG_DATE_FORMAT
        )
        agent_handler.setFormatter(agent_formatter)
        self.logger.addHandler(agent_handler)
        
        # 서비스 로깅 핸들러
        service_log_path = os.path.join(
            config.LOGS_DIR,
            f"Service_log_{datetime.now().strftime('%Y%m%d')}.log"
        )
        service_handler = RotatingFileHandler(
            service_log_path,
            maxBytes=config.LOG_MAX_BYTES,
            backupCount=config.LOG_BACKUP_COUNT,
            encoding=config.LOG_ENCODING
        )
        # 로그 압축 설정
        service_handler.namer = lambda name: name + ".gz"
        service_handler.rotator = self._rotator
        service_handler.setLevel(logging.INFO)
        service_formatter = logging.Formatter(
            config.LOG_FORMAT,
            datefmt=config.LOG_DATE_FORMAT
        )
        service_handler.setFormatter(service_formatter)
        self.logger.addHandler(service_handler)
    
    def debug(self, message: str, **kwargs) -> None:
        """DEBUG 레벨 로그를 기록합니다."""
        self.logger.debug(message, **kwargs)
    
    def info(self, message: str, **kwargs) -> None:
        """INFO 레벨 로그를 기록합니다."""
        self.logger.info(message, **kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        """WARNING 레벨 로그를 기록합니다."""
        self.logger.warning(message, **kwargs)
    
    def error(self, message: str, **kwargs) -> None:
        """ERROR 레벨 로그를 기록합니다."""
        self.logger.error(message, **kwargs)
    
    def critical(self, message: str, **kwargs) -> None:
        """CRITICAL 레벨 로그를 기록합니다."""
        self.logger.critical(message, **kwargs)
    
    def log_agent_input(self, agent_name: str, input_data: str) -> None:
        """에이전트 입력을 로깅합니다."""
        self.info(f"[{agent_name}] Input: {input_data}")
    
    def log_agent_output(self, agent_name: str, output_data: str) -> None:
        """에이전트 출력을 로깅합니다."""
        self.info(f"[{agent_name}] Output: {output_data}")
    
    def log_tool_call(self, tool_name: str, input_data: dict, output_data: dict) -> None:
        """도구 호출을 로깅합니다."""
        self.info(f"[{tool_name}] Input: {input_data}")
        self.info(f"[{tool_name}] Output: {output_data}")
    
    def log_error_with_context(self, error: Exception, context: str = "") -> None:
        """에러와 컨텍스트를 로깅합니다."""
        import traceback
        error_msg = f"Error in {context}: {str(error)}"
        self.error(error_msg)
        self.debug(f"Traceback: {traceback.format_exc()}")


# 전역 로거 인스턴스들
def get_logger(name: str) -> Logger:
    """지정된 이름의 로거를 반환합니다."""
    return Logger(name)


# 주요 로거들
service_logger = get_logger("SuperSOL.Service")
agent_logger = get_logger("SuperSOL.Agent")
tool_logger = get_logger("SuperSOL.Tool")
preprocessing_logger = get_logger("SuperSOL.Preprocessing") 