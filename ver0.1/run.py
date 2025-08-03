#!/usr/bin/env python3
"""
SuperSOL 은행 채팅 서비스 실행 파일
"""

import os
import sys
import argparse
from pathlib import Path

# 가상환경 활성화 확인
def check_venv():
    """가상환경이 활성화되었는지 확인합니다."""
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("경고: solenv 가상환경이 활성화되지 않았습니다.")
        print("다음 명령어로 가상환경을 활성화하세요:")
        print("source solenv/bin/activate")
        print("또는")
        print("conda activate solenv")
        response = input("계속 진행하시겠습니까? (y/N): ")
        if response.lower() != 'y':
            sys.exit(1)

# 가상환경 확인
check_venv()

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.Config import config
from src.logger import service_logger
from src.mcp_server import APIServer
from src.web_ui.web_server import create_web_server


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="SuperSOL 은행 채팅 서비스")
    parser.add_argument("--host", default=config.HOST, help="서버 호스트")
    parser.add_argument("--port", type=int, default=config.PORT, help="서버 포트")
    parser.add_argument("--debug", action="store_true", help="디버그 모드")
    parser.add_argument("--mode", choices=["api", "web", "both"], default="web", 
                       help="실행 모드: api(API 서버만), web(웹 UI만), both(둘 다)")
    
    args = parser.parse_args()
    
    try:
        # 설정 검증
        config.validate()
        
        # 로그 디렉토리 생성
        os.makedirs(config.LOGS_DIR, exist_ok=True)
        
        service_logger.info("SuperSOL 은행 채팅 서비스 시작")
        service_logger.info(f"설정: HOST={args.host}, PORT={args.port}, DEBUG={args.debug}, MODE={args.mode}")
        
        if args.mode in ["api", "both"]:
            # API 서버 생성 및 실행
            api_server = APIServer()
            if args.mode == "both":
                # 백그라운드에서 API 서버 실행
                import threading
                api_thread = threading.Thread(
                    target=api_server.run,
                    args=(args.host, args.port + 1),  # API 서버는 다른 포트 사용
                    daemon=True
                )
                api_thread.start()
                service_logger.info(f"API 서버 백그라운드 실행: http://{args.host}:{args.port + 1}")
            else:
                api_server.run(host=args.host, port=args.port)
        
        if args.mode in ["web", "both"]:
            # 웹 UI 서버 생성 및 실행
            web_server = create_web_server()
            web_server.run(host=args.host, port=args.port, debug=args.debug)
        
    except KeyboardInterrupt:
        service_logger.info("서비스 종료 요청됨")
    except Exception as e:
        service_logger.error(f"서비스 시작 실패: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main() 