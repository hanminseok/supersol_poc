from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import json
import uuid
from datetime import datetime

from services.chat_service import ChatService
from services.customer_service import CustomerService
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
customer_service = CustomerService()

# 요청 모델
class ChatRequest(BaseModel):
    session_id: str
    message: str
    customer_id: Optional[str] = None
    customer_info: Optional[Dict[str, Any]] = None

class SessionRequest(BaseModel):
    session_id: str
    customer_id: Optional[str] = None
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
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; height: 100vh; }
            .chat-container { max-width: 1000px; margin: 0 auto; background: white; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); height: calc(100vh - 40px); display: flex; flex-direction: column; }
            .chat-header { background: #1e3a8a; color: white; padding: 20px; border-radius: 10px 10px 0 0; flex-shrink: 0; }

            .chat-messages { flex: 1; overflow-y: auto; padding: 20px; min-height: 0; }
            .message { margin-bottom: 15px; padding: 10px; border-radius: 8px; }
            .user-message { background: #dbeafe; margin-left: 20%; }
            .bot-message { background: #f3f4f6; margin-right: 20%; }
            .agent-log { background: #fef3c7; font-size: 12px; color: #92400e; }
            .chat-input { padding: 20px; border-top: 1px solid #e5e7eb; flex-shrink: 0; }
            .input-group { display: flex; gap: 10px; }
            input[type="text"] { flex: 1; padding: 10px; border: 1px solid #d1d5db; border-radius: 5px; }
            button { padding: 10px 20px; background: #1e3a8a; color: white; border: none; border-radius: 5px; cursor: pointer; }
            button:hover { background: #1e40af; }
            button:disabled { background: #9ca3af; cursor: not-allowed; }
            .customer-selector-header { margin-bottom: 20px; }
            select { padding: 8px; border: 1px solid #d1d5db; border-radius: 5px; }
            .current-customer { background: #10b981; color: white; padding: 5px 10px; border-radius: 5px; margin-left: 10px; }
            
            /* 반응형 디자인을 위한 미디어 쿼리 */
            @media (max-width: 768px) {
                body { padding: 10px; }
                .chat-container { height: calc(100vh - 20px); }
                .user-message, .bot-message { margin-left: 0; margin-right: 0; }
            }
            
            @media (max-height: 600px) {
                .chat-header { padding: 10px; }
                .customer-selector { padding: 10px; }
                .chat-input { padding: 10px; }
            }
        </style>
    </head>
    <body>
        <div class="chat-container">
            <div class="chat-header">
                <h1>[POC]SuperSOL Banking Chat</h1>
                <div class="customer-selector-header">
                    <label for="customerSelect">고객 선택: </label>
                    <select id="customerSelect" onchange="onCustomerSelect()">
                        <option value="">고객을 선택하세요</option>
                    </select>
                    <span id="currentCustomer" class="current-customer" style="display: none;"></span>
                </div>
            </div>
            
            <div class="chat-messages" id="chatMessages"></div>
            <div class="chat-input">
                <div class="input-group">
                    <input type="text" id="messageInput" placeholder="고객을 선택한 후 메시지를 입력하세요..." onkeypress="handleKeyPress(event)" disabled>
                    <button onclick="sendMessage()" id="sendButton" disabled>전송</button>
                </div>
            </div>
        </div>

        <script>
            let ws = null;
            let currentSessionId = '';
            let selectedCustomer = null;
            let customers = [];

            async function loadCustomers() {
                try {
                    const response = await fetch('/customers');
                    const data = await response.json();
                    customers = data.customers;
                    
                    const select = document.getElementById('customerSelect');
                    select.innerHTML = '<option value="">고객을 선택하세요</option>';
                    
                    customers.forEach(customer => {
                        const option = document.createElement('option');
                        option.value = customer.customer_id;
                        option.textContent = `${customer.name} (${customer.customer_id})`;
                        select.appendChild(option);
                    });
                } catch (error) {
                    console.error('고객 정보 로드 실패:', error);
                }
            }

            function onCustomerSelect() {
                const select = document.getElementById('customerSelect');
                const selectedValue = select.value;
                
                if (!selectedValue) {
                    clearCustomerSelection();
                    return;
                }
                
                const customer = customers.find(c => c.customer_id === selectedValue);
                if (customer) {
                    selectedCustomer = customer;
                    
                    // UI 업데이트
                    document.getElementById('currentCustomer').textContent = `${customer.name} 고객`;
                    document.getElementById('currentCustomer').style.display = 'inline';
                    document.getElementById('messageInput').disabled = false;
                    document.getElementById('sendButton').disabled = false;
                    document.getElementById('messageInput').placeholder = `${customer.name} 고객님, 무엇을 도와드릴까요?`;
                    
                    // 세션 생성
                    createSession();
                }
            }
            
            function clearCustomerSelection() {
                selectedCustomer = null;
                
                // UI 초기화
                document.getElementById('customerSelect').value = '';
                document.getElementById('currentCustomer').style.display = 'none';
                document.getElementById('messageInput').disabled = true;
                document.getElementById('sendButton').disabled = true;
                document.getElementById('messageInput').placeholder = '고객을 선택한 후 메시지를 입력하세요...';
                
                // 채팅 메시지 초기화
                document.getElementById('chatMessages').innerHTML = '';
            }

            function connectWebSocket() {
                ws = new WebSocket('ws://localhost:8000/ws');
                
                ws.onopen = function(event) {
                    console.log('WebSocket 연결됨');
                };
                
                ws.onmessage = function(event) {
                    console.log('WebSocket 메시지 수신:', event.data);  // 디버깅용 로그
                    const data = JSON.parse(event.data);
                    handleMessage(data);
                };
                
                ws.onclose = function(event) {
                    console.log('WebSocket 연결 종료');
                };
            }

            let currentResponseDiv = null;  // 현재 응답을 표시할 div
            
            function handleMessage(data) {
                console.log('handleMessage 호출됨, data:', data);  // 디버깅용 로그
                const chatMessages = document.getElementById('chatMessages');
                
                // data가 문자열인 경우 JSON 파싱 시도
                if (typeof data === 'string') {
                    try {
                        data = JSON.parse(data);
                    } catch (e) {
                        console.error('JSON 파싱 오류:', e, '원본 데이터:', data);
                        return;
                    }
                }
                
                if (data.type === 'response') {
                    // 첫 번째 응답 청크인 경우 새로운 div 생성
                    if (!currentResponseDiv) {
                        currentResponseDiv = document.createElement('div');
                        currentResponseDiv.className = 'message bot-message';
                        currentResponseDiv.textContent = '';
                        chatMessages.appendChild(currentResponseDiv);
                    }
                    // 기존 응답에 새로운 내용 추가
                    currentResponseDiv.textContent += data.content;

                } else if (data.type === 'error') {
                    const errorDiv = document.createElement('div');
                    errorDiv.className = 'message bot-message';
                    errorDiv.style.color = 'red';
                    errorDiv.textContent = '❌ ' + data.content;
                    chatMessages.appendChild(errorDiv);
                } else if (data.type === 'complete') {
                    console.log('응답 완료');
                    currentResponseDiv = null;  // 응답 완료 시 초기화
                }
                
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }

            function sendMessage() {
                const messageInput = document.getElementById('messageInput');
                const message = messageInput.value.trim();
                
                if (!selectedCustomer) {
                    alert('고객을 먼저 선택해주세요.');
                    return;
                }
                
                if (message && ws && ws.readyState === WebSocket.OPEN) {
                    const userDiv = document.createElement('div');
                    userDiv.className = 'message user-message';
                    userDiv.textContent = message;
                    document.getElementById('chatMessages').appendChild(userDiv);
                    
                    // 새로운 메시지 전송 시 이전 응답 상태 초기화
                    currentResponseDiv = null;
                    
                    const request = {
                        session_id: currentSessionId || 'session_' + Date.now(),
                        message: message,
                        customer_id: selectedCustomer.customer_id,
                        customer_info: selectedCustomer
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
                document.getElementById('chatMessages').innerHTML = '';
            }

            // 페이지 로드 시 초기화
            window.onload = function() {
                connectWebSocket();
                loadCustomers();
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
                # response는 이미 JSON 형식이므로 직접 전송
                service_logger.info(f"WebSocket 전송: {response[:100]}...")  # 디버깅용 로그
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

@app.get("/customers")
async def get_customers():
    """고객 목록 조회"""
    try:
        customers = customer_service.get_customer_summary()
        return {"customers": customers}
    except Exception as e:
        service_logger.error(f"고객 목록 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/customers/{customer_id}")
async def get_customer_detail(customer_id: str):
    """고객 상세 정보 조회"""
    try:
        customer = customer_service.get_customer_by_id(customer_id)
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        return customer
    except HTTPException:
        raise
    except Exception as e:
        service_logger.error(f"고객 상세 정보 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """헬스 체크"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 