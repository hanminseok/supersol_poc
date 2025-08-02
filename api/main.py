from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import json
import uuid
from datetime import datetime

from services.chat_service import ChatService
from utils.logger import service_logger

app = FastAPI(title="SuperSOL Banking Chat Service", version="1.0.0")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 서비스 인스턴스
chat_service = ChatService()

# 요청 모델
class ChatRequest(BaseModel):
    session_id: str
    message: str
    customer_info: Optional[Dict[str, Any]] = None

class SessionRequest(BaseModel):
    session_id: str
    customer_info: Optional[Dict[str, Any]] = None

# WebSocket 연결 관리
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

manager = ConnectionManager()

@app.get("/")
async def get():
    """기본 HTML 페이지"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>SuperSOL Banking Chat</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }
            .chat-container { max-width: 800px; margin: 0 auto; background: white; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .chat-header { background: #1e3a8a; color: white; padding: 20px; border-radius: 10px 10px 0 0; }
            .chat-messages { height: 400px; overflow-y: auto; padding: 20px; }
            .message { margin-bottom: 15px; padding: 10px; border-radius: 8px; }
            .user-message { background: #dbeafe; margin-left: 20%; }
            .bot-message { background: #f3f4f6; margin-right: 20%; }
            .agent-log { background: #fef3c7; font-size: 12px; color: #92400e; }
            .chat-input { padding: 20px; border-top: 1px solid #e5e7eb; }
            .input-group { display: flex; gap: 10px; }
            input[type="text"] { flex: 1; padding: 10px; border: 1px solid #d1d5db; border-radius: 5px; }
            button { padding: 10px 20px; background: #1e3a8a; color: white; border: none; border-radius: 5px; cursor: pointer; }
            button:hover { background: #1e40af; }
            .session-selector { margin-bottom: 20px; }
            select { padding: 8px; border: 1px solid #d1d5db; border-radius: 5px; }
        </style>
    </head>
    <body>
        <div class="chat-container">
            <div class="chat-header">
                <h1>🏦 SuperSOL Banking Chat</h1>
                <div class="session-selector">
                    <label for="sessionSelect">세션 선택: </label>
                    <select id="sessionSelect">
                        <option value="">새 세션</option>
                    </select>
                    <button onclick="createSession()">새 세션 생성</button>
                </div>
            </div>
            <div class="chat-messages" id="chatMessages"></div>
            <div class="chat-input">
                <div class="input-group">
                    <input type="text" id="messageInput" placeholder="메시지를 입력하세요..." onkeypress="handleKeyPress(event)">
                    <button onclick="sendMessage()">전송</button>
                </div>
            </div>
        </div>

        <script>
            let ws = null;
            let currentSessionId = '';

            function connectWebSocket() {
                ws = new WebSocket('ws://localhost:8000/ws');
                
                ws.onopen = function(event) {
                    console.log('WebSocket 연결됨');
                };
                
                ws.onmessage = function(event) {
                    const data = JSON.parse(event.data);
                    handleMessage(data);
                };
                
                ws.onclose = function(event) {
                    console.log('WebSocket 연결 종료');
                };
            }

            function handleMessage(data) {
                const chatMessages = document.getElementById('chatMessages');
                
                if (data.type === 'response') {
                    const messageDiv = document.createElement('div');
                    messageDiv.className = 'message bot-message';
                    messageDiv.textContent = data.content;
                    chatMessages.appendChild(messageDiv);
                } else if (data.type === 'agent_log') {
                    const logDiv = document.createElement('div');
                    logDiv.className = 'message agent-log';
                    logDiv.textContent = '🤖 ' + data.content;
                    chatMessages.appendChild(logDiv);
                } else if (data.type === 'error') {
                    const errorDiv = document.createElement('div');
                    errorDiv.className = 'message bot-message';
                    errorDiv.style.color = 'red';
                    errorDiv.textContent = '❌ ' + data.content;
                    chatMessages.appendChild(errorDiv);
                }
                
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }

            function sendMessage() {
                const messageInput = document.getElementById('messageInput');
                const message = messageInput.value.trim();
                
                if (message && ws && ws.readyState === WebSocket.OPEN) {
                    const userDiv = document.createElement('div');
                    userDiv.className = 'message user-message';
                    userDiv.textContent = message;
                    document.getElementById('chatMessages').appendChild(userDiv);
                    
                    const request = {
                        session_id: currentSessionId || 'session_' + Date.now(),
                        message: message
                    };
                    
                    ws.send(JSON.stringify(request));
                    messageInput.value = '';
                }
            }

            function handleKeyPress(event) {
                if (event.key === 'Enter') {
                    sendMessage();
                }
            }

            function createSession() {
                currentSessionId = 'session_' + Date.now();
                document.getElementById('sessionSelect').value = currentSessionId;
                document.getElementById('chatMessages').innerHTML = '';
            }

            // 페이지 로드 시 WebSocket 연결
            window.onload = function() {
                connectWebSocket();
            };
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 엔드포인트"""
    await manager.connect(websocket)
    service_logger.info("WebSocket 연결됨")
    
    try:
        while True:
            data = await websocket.receive_text()
            request = json.loads(data)
            
            # 채팅 처리
            async for response in chat_service.process_chat(
                session_id=request.get("session_id", f"session_{uuid.uuid4()}"),
                user_query=request.get("message", ""),
                customer_info=request.get("customer_info")
            ):
                await manager.send_personal_message(response, websocket)
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        service_logger.info("WebSocket 연결 종료")
    except Exception as e:
        service_logger.error(f"WebSocket 오류: {str(e)}")
        await manager.send_personal_message(
            f"data: {json.dumps({'type': 'error', 'content': '서버 오류가 발생했습니다.'}, ensure_ascii=False)}\n\n",
            websocket
        )

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """HTTP 채팅 엔드포인트"""
    try:
        response_chunks = []
        async for chunk in chat_service.process_chat(
            session_id=request.session_id,
            user_query=request.message,
            customer_info=request.customer_info
        ):
            response_chunks.append(chunk)
        
        return {"response": "".join(response_chunks)}
        
    except Exception as e:
        service_logger.error(f"Chat endpoint 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sessions")
async def get_sessions():
    """세션 목록 조회"""
    try:
        sessions = await chat_service.get_session_list()
        return {"sessions": sessions}
    except Exception as e:
        service_logger.error(f"세션 목록 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sessions/{session_id}")
async def get_session_info(session_id: str):
    """세션 정보 조회"""
    try:
        session_info = await chat_service.get_session_info(session_id)
        if not session_info:
            raise HTTPException(status_code=404, detail="Session not found")
        return session_info
    except HTTPException:
        raise
    except Exception as e:
        service_logger.error(f"세션 정보 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """세션 삭제"""
    try:
        success = await chat_service.delete_session(session_id)
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        return {"message": "Session deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        service_logger.error(f"세션 삭제 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """헬스 체크"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 