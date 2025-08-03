from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import uuid
from ..Config import config
from ..logger import service_logger
from .chat_service import ChatService


class ChatRequest(BaseModel):
    """채팅 요청 모델"""
    message: str
    session_id: Optional[str] = None
    user_id: str = "default_user"


class ChatResponse(BaseModel):
    """채팅 응답 모델"""
    session_id: str
    response: str
    domain: Optional[str] = None
    worker: Optional[str] = None
    metadata: Dict[str, Any] = {}


class SessionHistoryResponse(BaseModel):
    """세션 히스토리 응답 모델"""
    session_id: str
    messages: List[Dict[str, Any]]


class HealthResponse(BaseModel):
    """헬스 체크 응답 모델"""
    status: str
    message: str


class APIServer:
    """FastAPI 서버 클래스"""
    
    def __init__(self):
        """API 서버를 초기화합니다."""
        self.app = FastAPI(
            title="SuperSOL 은행 채팅 서비스",
            description="멀티 에이전트 기반 은행 채팅 서비스 API",
            version="1.0.0"
        )
        
        # CORS 설정
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # 서비스 초기화
        self.chat_service = ChatService()
        self.logger = service_logger
        
        # 라우터 설정
        self._setup_routes()
    
    def _setup_routes(self):
        """API 라우트를 설정합니다."""
        
        @self.app.post("/chat", response_model=ChatResponse)
        async def chat(request: ChatRequest):
            """채팅 메시지를 처리합니다."""
            try:
                # 세션 ID 생성 (제공되지 않은 경우)
                session_id = request.session_id or str(uuid.uuid4())
                
                # 메시지 처리
                result = self.chat_service.process_message(
                    session_id=session_id,
                    user_id=request.user_id,
                    message=request.message
                )
                
                return ChatResponse(**result)
                
            except Exception as e:
                self.logger.log_error_with_context(e, "API.chat")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/session/{session_id}/history", response_model=SessionHistoryResponse)
        async def get_session_history(session_id: str):
            """세션 히스토리를 조회합니다."""
            try:
                messages = self.chat_service.get_session_history(session_id)
                
                return SessionHistoryResponse(
                    session_id=session_id,
                    messages=messages
                )
                
            except Exception as e:
                self.logger.log_error_with_context(e, f"API.get_session_history({session_id})")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.delete("/session/{session_id}")
        async def clear_session(session_id: str):
            """세션을 클리어합니다."""
            try:
                success = self.chat_service.clear_session(session_id)
                
                if success:
                    return {"message": f"세션 {session_id}가 클리어되었습니다."}
                else:
                    raise HTTPException(status_code=404, detail=f"세션 {session_id}를 찾을 수 없습니다.")
                
            except HTTPException:
                raise
            except Exception as e:
                self.logger.log_error_with_context(e, f"API.clear_session({session_id})")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/health", response_model=HealthResponse)
        async def health_check():
            """헬스 체크를 수행합니다."""
            try:
                return HealthResponse(
                    status="healthy",
                    message="SuperSOL 은행 채팅 서비스가 정상적으로 작동 중입니다."
                )
                
            except Exception as e:
                self.logger.log_error_with_context(e, "API.health_check")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/")
        async def root():
            """루트 엔드포인트"""
            return {
                "message": "SuperSOL 은행 채팅 서비스 API",
                "version": "1.0.0",
                "docs": "/docs"
            }
    
    def run(self, host: str = None, port: int = None):
        """서버를 실행합니다."""
        import uvicorn
        
        host = host or config.HOST
        port = port or config.PORT
        
        self.logger.info(f"SuperSOL 서버 시작: {host}:{port}")
        
        uvicorn.run(
            self.app,
            host=host,
            port=port,
            log_level="info"
        ) 