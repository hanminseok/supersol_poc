"""
웹 UI 서버
FastAPI 기반 채팅 인터페이스
"""

import asyncio
import json
import re
from typing import Dict, Any, List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, validator
import uvicorn
from pathlib import Path

from ..mcp_server.chat_service import ChatService
from ..logger import Logger
from ..Config import config

# 로거 설정
logger = Logger(__name__)

class ChatMessage(BaseModel):
    """채팅 메시지 모델"""
    message: str
    session_id: str = "default"
    
    @validator('message')
    def validate_message(cls, v):
        """메시지 유효성 검증"""
        if not v or not v.strip():
            raise ValueError('메시지는 비어있을 수 없습니다.')
        if len(v) > 1000:
            raise ValueError('메시지는 1000자를 초과할 수 없습니다.')
        # XSS 방지를 위한 기본적인 필터링
        if re.search(r'<script|javascript:|on\w+\s*=', v, re.IGNORECASE):
            raise ValueError('잘못된 메시지 형식입니다.')
        return v.strip()
    
    @validator('session_id')
    def validate_session_id(cls, v):
        """세션 ID 유효성 검증"""
        if not v or not v.strip():
            return "default"
        if len(v) > 100:
            raise ValueError('세션 ID는 100자를 초과할 수 없습니다.')
        # 세션 ID 형식 검증
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('세션 ID는 영문자, 숫자, 언더스코어, 하이픈만 사용 가능합니다.')
        return v.strip()

class ChatResponse(BaseModel):
    """채팅 응답 모델"""
    response: str
    session_id: str
    status: str = "success"
    error: str = None

class WebUIServer:
    """웹 UI 서버 클래스"""
    
    def __init__(self):
        self.app = FastAPI(
            title="SuperSOL 은행 채팅 서비스",
            description="멀티 에이전트 기반 은행 고객 지원 채팅 서비스",
            version="1.0.0"
        )
        self.chat_service = ChatService()
        self.active_connections: List[WebSocket] = []
        
        # CORS 설정
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        self._setup_routes()
        self._setup_static_files()
    
    def _setup_routes(self):
        """라우트 설정"""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def get_chat_interface():
            """채팅 인터페이스 HTML 반환"""
            return self._get_chat_html()
        
        @self.app.post("/api/chat", response_model=ChatResponse)
        async def chat_endpoint(chat_message: ChatMessage):
            """채팅 API 엔드포인트"""
            try:
                logger.info(f"채팅 요청 수신: {chat_message.message[:50]}...")
                
                # 채팅 서비스 호출
                chat_response = self.chat_service.process_message(
                    chat_message.session_id,
                    config.DEFAULT_WEB_USER_ID,  # 기본 사용자 ID
                    chat_message.message
                )
                
                # 응답에서 메시지 텍스트 추출
                response_text = chat_response.get("response", "응답을 생성할 수 없습니다.")
                logger.info(f"채팅 응답 생성 완료: {response_text[:50]}...")
                
                return ChatResponse(
                    response=response_text,
                    session_id=chat_message.session_id
                )
                
            except Exception as e:
                logger.error(f"채팅 처리 중 오류 발생: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.websocket("/ws/chat")
        async def websocket_endpoint(websocket: WebSocket):
            """웹소켓 채팅 엔드포인트"""
            await websocket.accept()
            self.active_connections.append(websocket)
            
            try:
                while True:
                    # 클라이언트로부터 메시지 수신
                    data = await websocket.receive_text()
                    message_data = json.loads(data)
                    
                    logger.info(f"웹소켓 메시지 수신: {message_data.get('message', '')[:50]}...")
                    
                    # 스트리밍 응답 시작
                    await websocket.send_text(json.dumps({
                        "type": "start",
                        "session_id": message_data.get("session_id", "default")
                    }))
                    
                    # 채팅 서비스 호출 (스트리밍)
                    chat_response = self.chat_service.process_message(
                        message_data.get("session_id", "default"),
                        config.DEFAULT_WEB_USER_ID,  # 기본 사용자 ID
                        message_data.get("message", "")
                    )
                    
                    # 응답에서 메시지 텍스트 추출
                    response_text = chat_response.get("response", "응답을 생성할 수 없습니다.")
                    
                    # 응답 전송
                    await websocket.send_text(json.dumps({
                        "type": "response",
                        "response": response_text,
                        "session_id": message_data.get("session_id", "default")
                    }))
                    
                    # 응답 완료
                    await websocket.send_text(json.dumps({
                        "type": "end",
                        "session_id": message_data.get("session_id", "default")
                    }))
                    
            except WebSocketDisconnect:
                self.active_connections.remove(websocket)
                logger.info("웹소켓 연결 종료")
            except Exception as e:
                logger.error(f"웹소켓 처리 중 오류: {str(e)}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "error": str(e)
                }))
        
        @self.app.get("/api/health")
        async def health_check():
            """헬스 체크 엔드포인트"""
            return {"status": "healthy", "service": "SuperSOL Chat"}
        
        @self.app.get("/api/status")
        async def get_status():
            """서비스 상태 확인"""
            return {
                "active_connections": len(self.active_connections),
                "service_status": "running"
            }
    
    def _setup_static_files(self):
        """정적 파일 설정"""
        static_dir = Path(__file__).parent / "static"
        static_dir.mkdir(exist_ok=True)
        
        # CSS 파일 생성
        css_file = static_dir / "style.css"
        if not css_file.exists():
            self._create_css_file(css_file)
        
        # JS 파일 생성
        js_file = static_dir / "script.js"
        if not js_file.exists():
            self._create_js_file(js_file)
        
        self.app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    
    def _create_css_file(self, css_file: Path):
        """CSS 파일 생성"""
        css_content = """
/* SuperSOL 은행 채팅 서비스 스타일 */
:root {
    --primary-blue: #1e3a8a;
    --secondary-blue: #3b82f6;
    --light-blue: #dbeafe;
    --accent-blue: #60a5fa;
    --text-dark: #1f2937;
    --text-light: #6b7280;
    --bg-white: #ffffff;
    --bg-gray: #f9fafb;
    --border-color: #e5e7eb;
    --shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    background: linear-gradient(135deg, var(--light-blue) 0%, var(--bg-white) 100%);
    min-height: 100vh;
    color: var(--text-dark);
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
}

.header {
    text-align: center;
    margin-bottom: 30px;
    padding: 20px;
    background: var(--bg-white);
    border-radius: 12px;
    box-shadow: var(--shadow);
}

.header h1 {
    color: var(--primary-blue);
    font-size: 2.5rem;
    margin-bottom: 10px;
}

.header p {
    color: var(--text-light);
    font-size: 1.1rem;
}

.chat-container {
    background: var(--bg-white);
    border-radius: 12px;
    box-shadow: var(--shadow);
    overflow: hidden;
    height: 600px;
    display: flex;
    flex-direction: column;
}

.chat-header {
    background: var(--primary-blue);
    color: white;
    padding: 20px;
    text-align: center;
}

.chat-header h2 {
    font-size: 1.5rem;
    margin-bottom: 5px;
}

.chat-header p {
    opacity: 0.9;
    font-size: 0.9rem;
}

.chat-messages {
    flex: 1;
    padding: 20px;
    overflow-y: auto;
    background: var(--bg-gray);
}

.message {
    margin-bottom: 20px;
    display: flex;
    align-items: flex-start;
}

.message.user {
    justify-content: flex-end;
}

.message.bot {
    justify-content: flex-start;
}

.message-content {
    max-width: 70%;
    padding: 15px 20px;
    border-radius: 18px;
    position: relative;
    word-wrap: break-word;
}

.message.user .message-content {
    background: var(--secondary-blue);
    color: white;
    border-bottom-right-radius: 5px;
}

.message.bot .message-content {
    background: var(--bg-white);
    color: var(--text-dark);
    border: 1px solid var(--border-color);
    border-bottom-left-radius: 5px;
}

.message-time {
    font-size: 0.75rem;
    opacity: 0.7;
    margin-top: 5px;
}

.chat-input-container {
    padding: 20px;
    background: var(--bg-white);
    border-top: 1px solid var(--border-color);
}

.chat-input-form {
    display: flex;
    gap: 10px;
}

.chat-input {
    flex: 1;
    padding: 15px 20px;
    border: 2px solid var(--border-color);
    border-radius: 25px;
    font-size: 1rem;
    outline: none;
    transition: border-color 0.3s ease;
}

.chat-input:focus {
    border-color: var(--secondary-blue);
}

.send-button {
    padding: 15px 25px;
    background: var(--secondary-blue);
    color: white;
    border: none;
    border-radius: 25px;
    font-size: 1rem;
    cursor: pointer;
    transition: background-color 0.3s ease;
    white-space: nowrap;
}

.send-button:hover {
    background: var(--primary-blue);
}

.send-button:disabled {
    background: var(--text-light);
    cursor: not-allowed;
}

.loading {
    display: flex;
    align-items: center;
    gap: 10px;
    color: var(--text-light);
    font-style: italic;
}

.loading-dots {
    display: flex;
    gap: 4px;
}

.loading-dots span {
    width: 8px;
    height: 8px;
    background: var(--secondary-blue);
    border-radius: 50%;
    animation: loading 1.4s infinite ease-in-out;
}

.loading-dots span:nth-child(1) { animation-delay: -0.32s; }
.loading-dots span:nth-child(2) { animation-delay: -0.16s; }

@keyframes loading {
    0%, 80%, 100% { transform: scale(0); }
    40% { transform: scale(1); }
}

.error-message {
    background: #fee2e2;
    color: #dc2626;
    padding: 15px;
    border-radius: 8px;
    margin: 10px 0;
    border: 1px solid #fecaca;
}

.success-message {
    background: #dcfce7;
    color: #16a34a;
    padding: 15px;
    border-radius: 8px;
    margin: 10px 0;
    border: 1px solid #bbf7d0;
}

/* 반응형 디자인 */
@media (max-width: 768px) {
    .container {
        padding: 10px;
    }
    
    .header h1 {
        font-size: 2rem;
    }
    
    .chat-container {
        height: 500px;
    }
    
    .message-content {
        max-width: 85%;
    }
    
    .chat-input-form {
        flex-direction: column;
    }
    
    .send-button {
        width: 100%;
    }
}

/* 스크롤바 스타일링 */
.chat-messages::-webkit-scrollbar {
    width: 6px;
}

.chat-messages::-webkit-scrollbar-track {
    background: var(--bg-gray);
}

.chat-messages::-webkit-scrollbar-thumb {
    background: var(--border-color);
    border-radius: 3px;
}

.chat-messages::-webkit-scrollbar-thumb:hover {
    background: var(--text-light);
}

/* 접근성 스타일 */
.sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
}

/* 포커스 스타일 */
.chat-input:focus,
.send-button:focus {
    outline: 2px solid var(--secondary-blue);
    outline-offset: 2px;
}

/* 고대비 모드 지원 */
@media (prefers-contrast: high) {
    :root {
        --primary-blue: #000080;
        --secondary-blue: #0000ff;
        --text-dark: #000000;
        --text-light: #333333;
    }
}

/* 다크 모드 지원 */
@media (prefers-color-scheme: dark) {
    :root {
        --primary-blue: #60a5fa;
        --secondary-blue: #3b82f6;
        --light-blue: #1e3a8a;
        --text-dark: #f9fafb;
        --text-light: #d1d5db;
        --bg-white: #1f2937;
        --bg-gray: #111827;
        --border-color: #374151;
    }
}
"""
        
        with open(css_file, 'w', encoding='utf-8') as f:
            f.write(css_content)
    
    def _create_js_file(self, js_file: Path):
        """JavaScript 파일 생성"""
        js_content = """
// SuperSOL 은행 채팅 서비스 JavaScript

class ChatUI {
    constructor() {
        this.messagesContainer = document.getElementById('chat-messages');
        this.inputForm = document.getElementById('chat-input-form');
        this.inputField = document.getElementById('chat-input');
        this.sendButton = document.getElementById('send-button');
        this.websocket = null;
        this.sessionId = this.generateSessionId();
        
        this.initializeEventListeners();
        this.initializeWebSocket();
        this.addWelcomeMessage();
    }
    
    generateSessionId() {
        return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }
    
    initializeEventListeners() {
        this.inputForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.sendMessage();
        });
        
        this.inputField.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        this.inputField.addEventListener('input', () => {
            this.sendButton.disabled = !this.inputField.value.trim();
        });
    }
    
    initializeWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/chat`;
        
        this.websocket = new WebSocket(wsUrl);
        
        this.websocket.onopen = () => {
            console.log('WebSocket 연결됨');
        };
        
        this.websocket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleWebSocketMessage(data);
        };
        
        this.websocket.onerror = (error) => {
            console.error('WebSocket 오류:', error);
            this.showError('연결 오류가 발생했습니다.');
        };
        
        this.websocket.onclose = () => {
            console.log('WebSocket 연결 종료');
            // 3초 후 재연결 시도
            setTimeout(() => {
                this.initializeWebSocket();
            }, 3000);
        };
    }
    
    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'start':
                this.showLoading();
                break;
            case 'response':
                this.hideLoading();
                this.addBotMessage(data.response);
                break;
            case 'end':
                this.hideLoading();
                break;
            case 'error':
                this.hideLoading();
                this.showError(data.error);
                break;
        }
    }
    
    sendMessage() {
        const message = this.inputField.value.trim();
        if (!message) return;
        
        // 사용자 메시지 추가
        this.addUserMessage(message);
        
        // 입력 필드 초기화
        this.inputField.value = '';
        this.sendButton.disabled = true;
        
        // WebSocket을 통한 메시지 전송
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            this.websocket.send(JSON.stringify({
                message: message,
                session_id: this.sessionId
            }));
        } else {
            // WebSocket이 연결되지 않은 경우 HTTP API 사용
            this.sendMessageViaHTTP(message);
        }
    }
    
    async sendMessageViaHTTP(message) {
        try {
            this.showLoading();
            
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    session_id: this.sessionId
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            this.hideLoading();
            this.addBotMessage(data.response);
            
        } catch (error) {
            console.error('메시지 전송 오류:', error);
            this.hideLoading();
            this.showError('메시지 전송 중 오류가 발생했습니다.');
        }
    }
    
    addUserMessage(message) {
        const messageElement = this.createMessageElement(message, 'user');
        this.messagesContainer.appendChild(messageElement);
        this.scrollToBottom();
    }
    
    addBotMessage(message) {
        const messageElement = this.createMessageElement(message, 'bot');
        this.messagesContainer.appendChild(messageElement);
        this.scrollToBottom();
    }
    
    createMessageElement(message, type) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.textContent = message;
        
        const timeDiv = document.createElement('div');
        timeDiv.className = 'message-time';
        timeDiv.textContent = new Date().toLocaleTimeString();
        
        contentDiv.appendChild(timeDiv);
        messageDiv.appendChild(contentDiv);
        
        return messageDiv;
    }
    
    addWelcomeMessage() {
        const welcomeMessage = `안녕하세요! SuperSOL 은행 채팅 서비스입니다. 
        
무엇을 도와드릴까요?

• 계좌 조회 및 이체
• 자동이체 설정
• 투자상품 문의
• 대출 상담
• 고객정보 관리

언제든지 질문해 주세요!`;
        
        this.addBotMessage(welcomeMessage);
    }
    
    showLoading() {
        // 기존 로딩 메시지 제거
        this.hideLoading();
        
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'message bot';
        loadingDiv.id = 'loading-message';
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content loading';
        contentDiv.innerHTML = `
            <div>답변을 생성하고 있습니다</div>
            <div class="loading-dots">
                <span></span>
                <span></span>
                <span></span>
            </div>
        `;
        
        loadingDiv.appendChild(contentDiv);
        this.messagesContainer.appendChild(loadingDiv);
        this.scrollToBottom();
    }
    
    hideLoading() {
        const loadingMessage = document.getElementById('loading-message');
        if (loadingMessage) {
            loadingMessage.remove();
        }
    }
    
    showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.textContent = message;
        
        this.messagesContainer.appendChild(errorDiv);
        this.scrollToBottom();
        
        // 5초 후 오류 메시지 제거
        setTimeout(() => {
            errorDiv.remove();
        }, 5000);
    }
    
    scrollToBottom() {
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }
}

// 페이지 로드 시 채팅 UI 초기화
document.addEventListener('DOMContentLoaded', () => {
    new ChatUI();
});
"""
        
        with open(js_file, 'w', encoding='utf-8') as f:
            f.write(js_content)
    
    def _get_chat_html(self) -> str:
        """채팅 인터페이스 HTML 반환"""
        return """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SuperSOL 은행 채팅 서비스</title>
    <meta name="description" content="멀티 에이전트 기반 은행 고객 지원 채팅 서비스">
    <link rel="stylesheet" href="/static/style.css">
    <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🏦</text></svg>">
</head>
<body>
    <div class="container">
        <header class="header" role="banner">
            <h1>🏦 SuperSOL 은행</h1>
            <p>멀티 에이전트 기반 고객 지원 채팅 서비스</p>
        </header>
        
        <main class="chat-container" role="main">
            <div class="chat-header">
                <h2>💬 실시간 채팅 상담</h2>
                <p>AI 어시스턴트가 도와드립니다</p>
            </div>
            
            <div class="chat-messages" id="chat-messages" role="log" aria-live="polite" aria-label="채팅 메시지">
                <!-- 메시지들이 여기에 표시됩니다 -->
            </div>
            
            <div class="chat-input-container">
                <form class="chat-input-form" id="chat-input-form" role="search">
                    <label for="chat-input" class="sr-only">메시지 입력</label>
                    <input 
                        type="text" 
                        class="chat-input" 
                        id="chat-input" 
                        name="message"
                        placeholder="질문을 입력하세요..."
                        autocomplete="off"
                        aria-describedby="send-button"
                        required
                    >
                    <button type="submit" class="send-button" id="send-button" disabled aria-label="메시지 전송">
                        전송
                    </button>
                </form>
            </div>
        </main>
    </div>
    
    <script src="/static/script.js"></script>
</body>
</html>
"""
    
    def run(self, host: str = "0.0.0.0", port: int = 8000, debug: bool = False):
        """웹 서버 실행"""
        logger.info(f"웹 UI 서버 시작: http://{host}:{port}")
        uvicorn.run(
            self.app,
            host=host,
            port=port,
            log_level="info" if not debug else "debug"
        )

def create_web_server() -> WebUIServer:
    """웹 UI 서버 인스턴스 생성"""
    return WebUIServer()

if __name__ == "__main__":
    server = create_web_server()
    server.run(debug=True) 