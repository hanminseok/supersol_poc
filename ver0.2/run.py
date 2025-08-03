#!/usr/bin/env python3
"""
SuperSOL 은행 채팅 서비스 실행 스크립트
"""

import uvicorn
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from Config import Config
from utils.logger import service_logger

def main():
    """메인 실행 함수"""
    try:
        service_logger.info("SuperSOL 은행 채팅 서비스 시작")
        service_logger.info(f"서버 주소: {Config.HOST}:{Config.PORT}")
        
        # uvicorn 서버 실행
        uvicorn.run(
            "api.main:app",
            host=Config.HOST,
            port=Config.PORT,
            reload=True,  # 개발 모드에서 자동 리로드
            log_level=Config.LOG_LEVEL.lower()
        )
        
    except KeyboardInterrupt:
        service_logger.info("서버 종료 요청됨")
    except Exception as e:
        service_logger.error(f"서버 실행 중 오류 발생: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 