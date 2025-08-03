
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
