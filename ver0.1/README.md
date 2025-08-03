# SuperSOL 은행 채팅 서비스

멀티 에이전트 기반의 은행 고객 지원 채팅 서비스입니다.

## 🏗️ 아키텍처

### 3단계 에이전트 시스템

1. **Supervisor Agent** (최상위 의사결정자)
   - OpenAI GPT-4o 모델 사용
   - 사용자 질문 분석 및 도메인 결정
   - 적절한 Domain Agent에게 작업 위임

2. **Domain Agent** (비즈니스 도메인 전문가)
   - OpenAI GPT-4o 모델 사용
   - 은행 업무, 자산관리 도메인 처리
   - Worker Agent에게 작업 위임

3. **Worker Agent** (작업 실행자)
   - DeepInfra Qwen/Qwen3-30B-A3B LLM 모델 사용
   - 7개 작업자 유형: 고객정보, 금융정보, 이체, 계좌, 자동이체, 투자상품, 대출
   - 적절한 도구들을 효율적으로 호출

### 전처리 파이프라인

1. **Text Normalization** - Qwen/Qwen3-30B-A3B
2. **Query Rewriting** - Qwen/Qwen3-30B-A3B  
3. **Intent Classification** - Qwen/Qwen3-30B-A3B

## 🚀 설치 및 실행

### 1. 가상환경 활성화

```bash
cd SuperSOL
source solenv/bin/activate
```

### 2. 의존성 설치

```bash
pip install -r requirements.txt
```

### 3. 환경변수 설정

환경변수 파일을 생성하고 API 키를 설정하세요:

```bash
# 환경변수 파일 복사
cp env.example .env

# .env 파일을 편집하여 실제 API 키 입력
nano .env
```

필수 환경변수:
- `OPENAI_API_KEY`: OpenAI API 키
- `DEEPINFRA_API_KEY`: DeepInfra API 키

**보안 주의사항**: API 키는 절대 Git에 커밋하지 마세요!

### 4. 서비스 실행

#### 웹 UI 모드 (기본)
```bash
python run.py --mode web
```

#### API 서버 모드
```bash
python run.py --mode api
```

#### 웹 UI + API 서버 동시 실행
```bash
python run.py --mode both
```

#### 디버그 모드
```bash
python run.py --mode web --debug
```

### 5. 웹 UI 접속

서비스 실행 후 브라우저에서 다음 URL로 접속:
- **웹 UI**: http://localhost:8000
- **API 문서**: http://localhost:8001/docs (API 모드 실행 시)

## 📁 프로젝트 구조

```
SuperSOL/
├── src/
│   ├── Config.py                 # 환경변수 및 설정
│   ├── logger.py                 # 로깅 시스템
│   ├── prompts/                  # 프롬프트 파일들
│   │   ├── preprocessing_prompt.json
│   │   ├── agent_prompt.json
│   │   └── tool_prompt.json
│   ├── preprocessing/            # 전처리 모듈
│   │   ├── text_normalizer.py
│   │   ├── query_rewriter.py
│   │   ├── intent_classifier.py
│   │   └── preprocessing_pipeline.py
│   ├── agents/                   # 에이전트 모듈
│   │   ├── base_agent.py
│   │   ├── supervisor_agent.py
│   │   ├── domain_agent.py
│   │   ├── worker_agent.py
│   │   └── quality_check_agent.py
│   ├── tools/                    # 도구 모듈
│   │   ├── base_tool.py
│   │   ├── customer_info_tools.py
│   │   ├── financial_info_tools.py
│   │   ├── transfer_tools.py
│   │   ├── account_tools.py
│   │   ├── auto_transfer_tools.py
│   │   ├── investment_tools.py
│   │   ├── loan_tools.py
│   │   └── tool_manager.py
│   ├── mcp_server/               # MCP 서버
│   │   ├── api_server.py
│   │   └── chat_service.py
│   ├── web_ui/                   # 웹 UI
│   │   ├── web_server.py
│   │   └── static/
│   │       ├── style.css
│   │       └── script.js
│   ├── models/                   # 데이터 모델
│   │   ├── agent_models.py
│   │   ├── chat_models.py
│   │   └── tool_models.py
│   └── utils/                    # 유틸리티
│       ├── data_loader.py
│       ├── llm_client.py
│       └── prompt_loader.py
├── Data/                         # JSON 샘플 데이터
├── logs/                         # 로그 파일
├── docs/                         # 문서
└── solenv/                       # 가상환경
```
│   ├── mcp_server/               # MCP 서버
│   │   ├── chat_service.py
│   │   └── api_server.py
│   ├── models/                   # 데이터 모델
│   │   ├── chat_models.py
│   │   ├── agent_models.py
│   │   └── tool_models.py
│   └── utils/                    # 유틸리티
│       ├── llm_client.py
│       ├── prompt_loader.py
│       └── data_loader.py
├── data/                         # JSON 샘플 데이터
│   ├── customer_info.json
│   ├── financial_info.json
│   ├── transfer_history.json
│   ├── account_info.json
│   ├── auto_transfer.json
│   ├── investment_products.json
│   └── loan_info.json
├── logs/                         # 로그 파일
├── docs/                         # 문서
├── tests/                        # 테스트 코드
├── run.py                        # 메인 실행 파일
└── requirements.txt              # Python 의존성
```

## 🌐 웹 UI 기능

### 주요 기능
- **실시간 채팅 인터페이스**: 직관적이고 사용하기 쉬운 채팅 UI
- **웹소켓 지원**: 실시간 양방향 통신
- **반응형 디자인**: 모바일과 데스크톱 모두 지원
- **파란색 테마**: 은행 서비스에 적합한 전문적인 디자인
- **로딩 상태 표시**: 사용자 경험 향상
- **에러 처리**: 친화적인 오류 메시지

### 사용법
1. 웹 브라우저에서 `http://localhost:8000` 접속
2. 채팅 입력창에 질문 입력
3. Enter 키 또는 전송 버튼 클릭
4. AI 어시스턴트의 응답 확인

### 지원하는 질문 유형
- 계좌 조회 및 이체
- 자동이체 설정
- 투자상품 문의
- 대출 상담
- 고객정보 관리

## 🔧 API 사용법

### 채팅 메시지 전송

```bash
curl -X POST "http://localhost:8000/api/chat" \
     -H "Content-Type: application/json" \
     -d '{
       "message": "내 계좌 잔액을 확인해주세요",
       "session_id": "user123"
     }'
```

### 헬스 체크

```bash
curl -X GET "http://localhost:8000/api/health"
```

### 서비스 상태 확인

```bash
curl -X GET "http://localhost:8000/api/status"
```

## 📊 로깅 시스템

- **Agent I/O 로깅**: `logs/Agent_log_YYYYMMDD.log`
- **서비스 로깅**: `logs/Service_log_YYYYMMDD.log`

로그 형식: `%(asctime)s [%(levelname)-8s][%(name)-15s] %(message)s`

## 🛠️ 개발 가이드라인

### 코드 품질
- Python 타입 힌트 필수 사용
- PEP 8 스타일 가이드 준수
- 적절한 에러 처리 (try-catch 블록)
- 모든 클래스와 함수에 docstring 추가

### 테스트
```bash
# 테스트 실행
python -m pytest tests/

# 커버리지 확인
python -m pytest --cov=src tests/

# 웹 UI 테스트
python -m pytest tests/test_web_ui.py -v

# 전체 테스트 커버리지 확인
python -m pytest --cov=src --cov-report=html tests/
```

## 🔒 보안

- API 키는 환경변수로 관리
- 입력 검증 구현
- CORS 설정
- 에러 메시지에서 민감한 정보 제외

## 📈 성능

- 응답 시간 < 5초
- 동시 사용자 세션 지원
- LLM API 호출 최적화
- 적절한 캐싱 사용

## 🤝 기여

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 📞 지원

문제가 발생하거나 질문이 있으시면 이슈를 생성해주세요.
