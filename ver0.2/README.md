# SuperSOL 은행 채팅 서비스

Multi Agent 기반의 은행 고객 지원 채팅 서비스입니다.

## 프로젝트 개요

- **목적**: 은행 앱 내 고객 지원을 위한 AI 채팅 서비스
- **기술**: Multi Agent Architecture, FastAPI, WebSocket, OpenAI API
- **특징**: 실시간 스트리밍 응답, 세션 기반 대화 관리, Agent I/O 로깅

## 시스템 아키텍처

### Multi Agent 구성
1. **Rewriting Agent**: 대화 맥락을 고려한 질문 재작성
2. **Preprocessing Agent**: 질문 표준화 및 의도/슬롯 추출
3. **Supervisor Agent**: 도메인 라우팅 및 전체 프로세스 관리
4. **Domain Agent**: 도메인별 요청 처리 및 도구 선택
5. **Tools**: 실제 은행 서비스 기능 실행

### 채팅 프로세스
1. 사용자 질문 입력
2. Rewriting Agent가 대화 맥락을 고려하여 질문 재작성
3. Preprocessing Agent가 의도와 슬롯 추출
4. Supervisor Agent가 적절한 도메인으로 라우팅
5. Domain Agent가 도구를 선택하여 요청 처리
6. 결과를 종합하여 사용자에게 응답

## 설치 및 실행

### 1. 환경 설정
```bash
# 가상환경 활성화
source ../solenv/bin/activate

# 의존성 설치
pip install -r requirements.txt
```

### 2. 환경변수 설정
1. `env.example` 파일을 `.env`로 복사:
   ```bash
   cp env.example .env
   ```

2. `.env` 파일에서 API 키와 설정을 수정:
   ```bash
   # API Keys (필수)
   OPENAI_API_KEY=your_openai_api_key_here
   DEEPINFRA_API_KEY=your_deepinfra_api_key_here
   
   # 서버 설정 (선택사항)
   HOST=0.0.0.0
   PORT=8000
   
   # 로깅 설정 (선택사항)
   LOG_LEVEL=INFO
   ```

### 3. 서버 실행
```bash
python run.py
```

### 4. 접속
- 웹 인터페이스: http://localhost:8000
- API 문서: http://localhost:8000/docs

## 주요 기능

### 채팅 기능
- **Multi-turn 대화**: 세션별 대화 내역 관리
- **실시간 스트리밍**: 응답이 실시간으로 스트리밍
- **Agent 로깅**: 각 Agent의 처리 과정을 실시간으로 표시

### 세션 관리
- 세션별 대화 내역 저장 (최대 100개)
- 세션 생성/조회/삭제
- 고객 정보 연동

### 로깅 시스템
- **Console Handler**: 모든 로그를 콘솔에 출력
- **Agent I/O 로깅**: Agent_log_{YYYYMMDD}.log
- **서비스 로깅**: Service_log_{YYYYMMDD}.log

## API 엔드포인트

### WebSocket
- `ws://localhost:8000/ws`: 실시간 채팅

### HTTP API
- `GET /`: 웹 인터페이스
- `POST /chat`: HTTP 채팅
- `GET /sessions`: 세션 목록
- `GET /sessions/{session_id}`: 세션 정보
- `DELETE /sessions/{session_id}`: 세션 삭제
- `GET /health`: 헬스 체크

## 프로젝트 구조

```
ver0.2/
├── api/                    # FastAPI 서버
│   ├── main.py            # 메인 서버 파일
│   └── __init__.py
├── agents/                # Multi Agent 구현
│   ├── base_agent.py      # 기본 Agent 클래스
│   ├── rewriting_agent.py # 질문 재작성 Agent
│   ├── preprocessing_agent.py # 전처리 Agent
│   ├── supervisor_agent.py    # 관리 Agent
│   ├── domain_agent.py        # 도메인 Agent
│   └── __init__.py
├── config/                # 설정 파일들
│   └── agents/            # Agent JSON 설정
│       ├── rewriting_agent.json
│       ├── preprocessing_agent.json
│       ├── supervisor_agent.json
│       ├── domain_agent.json
│       └── __init__.py
├── models/                # 데이터 모델
│   ├── agent_config.py    # Agent 설정 관리자
│   └── __init__.py
├── services/              # 비즈니스 로직
│   ├── chat_service.py    # 채팅 서비스
│   ├── session_manager.py # 세션 관리
│   └── __init__.py
├── utils/                 # 유틸리티
│   ├── logger.py          # 로깅 시스템
│   └── __init__.py
├── tests/                 # 테스트 코드
│   ├── test_agent_communication.py # Agent JSON 통신 테스트
│   └── __init__.py
├── sessions/              # 세션 데이터 (자동 생성)
├── logs/                  # 로그 파일 (자동 생성)
├── Config.py              # 환경 설정 파일
├── requirements.txt       # 의존성
├── run.py                 # 실행 스크립트
└── README.md              # 프로젝트 문서
```

## 사용 예시

### 웹 인터페이스 사용
1. 브라우저에서 http://localhost:8000 접속
2. "새 세션 생성" 버튼 클릭
3. 메시지 입력 후 전송
4. 실시간으로 Agent 처리 과정과 응답 확인

### API 사용
```bash
# HTTP 채팅
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test_session", "message": "잔액 조회해줘"}'

# 세션 목록 조회
curl "http://localhost:8000/sessions"
```

## 개발 가이드

### 새로운 Agent 추가
1. `agents/` 디렉토리에 새 Agent 클래스 생성
2. `BaseAgent`를 상속받아 `_process` 메서드 구현
3. `config/agents/` 디렉토리에 JSON 설정 파일 생성
4. `services/chat_service.py`에 통합

### 새로운 도구 추가
1. `tools/` 디렉토리에 도구 구현
2. `models/agent_config.py`의 도구 목록에 추가
3. `agents/domain_agent.py`에서 도구 선택 로직 수정

## 테스트 실행

```bash
# Agent JSON 통신 테스트 실행
python tests/test_agent_communication.py

# 가상환경에서 실행
source venv/bin/activate
python tests/test_agent_communication.py
```

## 로그 확인

```bash
# 실시간 로그 확인
tail -f logs/Service_log_$(date +%Y%m%d).log

# Agent 로그 확인
tail -f logs/Agent_log_$(date +%Y%m%d).log
```

## 문제 해결

### 일반적인 문제
1. **API 키 오류**: Config.py에서 API 키 확인
2. **포트 충돌**: Config.py에서 PORT 변경
3. **의존성 오류**: `pip install -r requirements.txt` 재실행

### 로그 확인
- 서비스 로그: `logs/Service_log_YYYYMMDD.log`
- Agent 로그: `logs/Agent_log_YYYYMMDD.log`

## 라이선스

이 프로젝트는 내부 개발용으로 제작되었습니다. 