import logging
import logging.handlers
import os
from datetime import datetime
from Config import Config

class Logger:
    def __init__(self, name):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, Config.LOG_LEVEL))
        
        # 로그 포맷 설정
        formatter = logging.Formatter(
            Config.LOG_FORMAT,
            datefmt=Config.LOG_DATE_FORMAT
        )
        
        # Console Handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # 로그 디렉토리 생성
        os.makedirs('logs', exist_ok=True)
        
        # Agent I/O 로깅용 File Handler
        agent_handler = logging.handlers.TimedRotatingFileHandler(
            filename=f'logs/Agent_log_{datetime.now().strftime("%Y%m%d")}.log',
            when='midnight',
            interval=1,
            backupCount=30,
            encoding='utf-8'
        )
        agent_handler.setLevel(logging.INFO)
        agent_handler.setFormatter(formatter)
        self.logger.addHandler(agent_handler)
        
        # 서비스 로깅용 File Handler
        service_handler = logging.handlers.TimedRotatingFileHandler(
            filename=f'logs/Service_log_{datetime.now().strftime("%Y%m%d")}.log',
            when='midnight',
            interval=1,
            backupCount=30,
            encoding='utf-8'
        )
        service_handler.setLevel(logging.INFO)
        service_handler.setFormatter(formatter)
        self.logger.addHandler(service_handler)
    
    def debug(self, message):
        self.logger.debug(message)
    
    def info(self, message):
        self.logger.info(message)
    
    def warning(self, message):
        self.logger.warning(message)
    
    def error(self, message, exc_info=True):
        self.logger.error(message, exc_info=exc_info)
    
    def critical(self, message, exc_info=True):
        self.logger.critical(message, exc_info=exc_info)

# 전역 로거 인스턴스
service_logger = Logger("SuperSOL_Service")
agent_logger = Logger("SuperSOL_Agent") 