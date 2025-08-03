# Configuration Files

이 디렉토리는 SuperSOL 에이전트 시스템의 설정 파일들을 포함합니다.

## 파일 구조

```
config/
├── shared_config.json          # 공통 설정
├── config_loader.py            # 설정 로더 유틸리티
├── customers.json              # 고객 데이터
└── agents/                     # 에이전트별 설정
    ├── rewriting_agent.json
    ├── preprocessing_agent.json
    ├── supervisor_agent.json
    ├── domain_agent.json
    └── tools.json              # 도구 실행 결과 및 응답 형식
```

## 설정 파일 설명

### shared_config.json
모든 에이전트에서 공통으로 사용되는 설정을 포함합니다:

- **banking_domains**: 은행 도메인 정의
- **common_intents**: 공통 의도(intent) 정의
- **common_topics**: 공통 주제(topic) 정의
- **context_settings**: 컨텍스트 관련 설정
- **reference_resolution**: 참조 해결 규칙
- **default_responses**: 기본 응답 메시지

### agents/ 디렉토리
각 에이전트별 설정 파일을 포함합니다:

#### rewriting_agent.json
질문 재작성 에이전트 설정:
- **context_settings**: 컨텍스트 설정
- **topics**: 주제 정의
- **reference_resolution**: 참조 해결 규칙

#### preprocessing_agent.json
전처리 에이전트 설정:
- **intents**: 의도 정의
- **intent_slots**: 의도별 슬롯 매핑
- **default_intent**: 기본 의도

#### supervisor_agent.json
감독 에이전트 설정:
- **intent_domain_mapping**: 의도-도메인 매핑
- **domains**: 도메인 정의
- **missing_slots_tools**: 누락된 슬롯 처리 도구

#### domain_agent.json
도메인 에이전트 설정:
- **intent_tool_mapping**: 의도-도구 매핑
- **tools**: 도구 정의
- **default_tool**: 기본 도구

#### tools.json
도구 실행 결과 및 응답 형식 설정:
- **tools**: 각 도구별 응답 형식 및 샘플 데이터
- **response_format**: 도구별 응답 스키마
- **sample_response**: 도구별 샘플 응답 데이터
- **default_error_response**: 기본 오류 응답

## 사용 방법

### ConfigLoader 사용

```python
from config.config_loader import config_loader

# 공통 설정 가져오기
domains = config_loader.get_banking_domains()
intents = config_loader.get_common_intents()

# 특정 에이전트 설정 가져오기
tool_mapping = config_loader.get_intent_tool_mapping("domain_agent")
domain_mapping = config_loader.get_intent_domain_mapping("supervisor_agent")

# 도구 설정 가져오기
tool_info = config_loader.get_tool_info("account_balance")
sample_response = config_loader.get_tool_sample_response("transfer_money")
response_format = config_loader.get_tool_response_format("loan_info")

### 설정 값 수정

1. 해당 설정 파일을 직접 편집
2. JSON 형식 유지
3. 에이전트 재시작 필요

## 하드코딩 제거 완료

다음 하드코딩된 값들이 설정 파일로 이동되었습니다:

### RewritingAgent
- 주제(topic) 정의
- 참조 해결 규칙
- 기본 응답 메시지
- 컨텍스트 설정

### PreprocessingAgent
- 의도(intent) 정의
- 의도별 슬롯 매핑
- 기본 의도

### SupervisorAgent
- 의도-도메인 매핑
- 도메인 정의
- 기본 도메인

### DomainAgent
- 의도-도구 매핑
- 도구 정의
- 기본 도구
- 도구 실행 시뮬레이션 결과

## 장점

1. **유지보수성**: 설정 변경 시 코드 수정 불필요
2. **확장성**: 새로운 의도/도구/도메인 추가 용이
3. **일관성**: 모든 에이전트에서 동일한 설정 사용
4. **테스트**: 설정별 테스트 가능
5. **다국어 지원**: 설정 파일로 다국어 지원 가능 