# Configuration Extraction Changelog

## 2024-01-XX - Hard-coded Values Extraction

### 개요
에이전트 코드에서 하드코딩된 값들을 설정 파일로 추출하여 유지보수성과 확장성을 향상시켰습니다.

### 변경 사항

#### 새로 생성된 파일
- `shared_config.json`: 공통 설정 파일
- `config_loader.py`: 설정 로더 유틸리티
- `README.md`: 설정 파일 문서
- `CHANGELOG.md`: 변경 이력
- `tools.json`: 도구 실행 결과 및 응답 형식 설정

#### 수정된 파일

##### ver0.2/config/agents/rewriting_agent.json
- **추가**: `context_settings` - 컨텍스트 관련 설정
- **추가**: `topics` - 주제 정의
- **추가**: `reference_resolution` - 참조 해결 규칙

##### ver0.2/config/agents/preprocessing_agent.json
- **추가**: `intents` - 의도 정의 (확장)
- **추가**: `intent_slots` - 의도별 슬롯 매핑 (확장)
- **추가**: `default_intent` - 기본 의도
- **추가**: `context_settings` - 컨텍스트 설정

##### ver0.2/config/agents/supervisor_agent.json
- **추가**: `intent_domain_mapping` - 의도-도메인 매핑
- **추가**: `domains` - 도메인 정의
- **추가**: `default_domain` - 기본 도메인
- **추가**: `context_settings` - 컨텍스트 설정
- **추가**: `missing_slots_tools` - 누락된 슬롯 처리 도구

##### ver0.2/config/agents/domain_agent.json
- **추가**: `intent_tool_mapping` - 의도-도구 매핑
- **추가**: `tools` - 도구 정의
- **추가**: `default_tool` - 기본 도구
- **추가**: `context_settings` - 컨텍스트 설정

#### 수정된 에이전트 코드

##### ver0.2/agents/rewriting_agent.py
- **제거**: 하드코딩된 주제 목록
- **제거**: 하드코딩된 참조 해결 규칙
- **제거**: 하드코딩된 기본 응답 메시지
- **추가**: `config_loader` import 및 사용
- **변경**: `_create_default_response()` - 설정에서 기본값 가져오기
- **변경**: `_build_context_aware_prompt()` - 설정에서 주제 목록 가져오기
- **변경**: `_summarize_conversation_context()` - 설정에서 최대 대화 수 가져오기
- **변경**: `_generate_reference_guide()` - 설정에서 참조 규칙 가져오기

##### ver0.2/agents/preprocessing_agent.py
- **제거**: 하드코딩된 의도-슬롯 매핑
- **제거**: 하드코딩된 기본 의도
- **추가**: `config_loader` import 및 사용
- **변경**: `_process()` - 설정에서 기본 의도 가져오기
- **변경**: `_get_related_slots_for_intent()` - 설정에서 슬롯 매핑 가져오기

##### ver0.2/agents/supervisor_agent.py
- **제거**: 하드코딩된 의도-도메인 매핑
- **제거**: 하드코딩된 도메인 정의
- **추가**: `config_loader` import 및 사용
- **변경**: `_default_context_aware_routing()` - 설정에서 매핑 가져오기
- **변경**: `_build_context_aware_routing_prompt()` - 설정에서 도메인 목록 가져오기
- **변경**: `_summarize_conversation_context()` - 설정에서 최대 대화 수 가져오기

##### ver0.2/agents/domain_agent.py
- **제거**: 하드코딩된 의도-도구 매핑
- **제거**: 하드코딩된 도구 정의
- **제거**: 하드코딩된 도구 실행 시뮬레이션 결과 (약 400줄의 하드코딩된 데이터)
- **추가**: `config_loader` import 및 사용
- **변경**: `_default_tool_selection()` - 설정에서 매핑 가져오기
- **변경**: `_default_tool_selection_with_context()` - 설정에서 매핑 가져오기
- **변경**: `_build_tool_selection_prompt()` - 설정에서 도구 목록 가져오기
- **변경**: `_summarize_conversation_context()` - 설정에서 최대 대화 수 가져오기
- **변경**: `_simulate_tool_execution()` - 설정에서 샘플 응답 가져오기

### 추출된 하드코딩 값들

#### 의도(Intent) 관련
- `check_balance`, `transfer_money`, `loan_inquiry`, `investment_info`
- `account_info`, `transaction_history`, `deposit_history`
- `auto_transfer_history`, `minus_account_info`, `isa_account_info`
- `mortgage_rate_change`, `fund_info`, `hot_etf_info`
- `transfer_limit_change`, `frequent_deposit_accounts`, `loan_account_status`
- `general_inquiry`

#### 도메인(Domain) 관련
- `banking`, `account`, `loan`, `investment`, `general`

#### 도구(Tool) 관련
- `account_balance`, `transfer_money`, `loan_info`, `investment_info`
- `account_info`, `transaction_history`, `deposit_history`
- `auto_transfer_history`, `minus_account_info`, `isa_account_info`
- `mortgage_rate_change`, `fund_info`, `hot_etf_info`
- `transfer_limit_change`, `frequent_deposit_accounts`, `loan_account_status`
- `general_inquiry`

#### 도구 실행 결과 데이터
- 각 도구별 상세한 응답 형식 및 샘플 데이터
- 거래 내역, 입금 내역, 자동이체 내역 등의 실제 데이터 구조
- 펀드 정보, ETF 정보, 대출 정보 등의 복잡한 중첩 데이터 구조

#### 주제(Topic) 관련
- `banking`, `account`, `loan`, `investment`, `general`

#### 참조 해결 규칙
- `'그 계좌' → 가장 최근에 언급된 계좌`
- `'잔액은?' → '계좌 잔액을 확인하고 싶습니다'`
- `'송금은?' → '송금을 진행하고 싶습니다'`
- `'대출은?' → '대출 정보를 확인하고 싶습니다'`

### 장점

1. **유지보수성 향상**: 새로운 의도/도구/도메인 추가 시 코드 수정 불필요
2. **일관성 보장**: 모든 에이전트에서 동일한 설정 사용
3. **확장성**: 설정 파일만 수정하여 시스템 확장 가능
4. **테스트 용이성**: 설정별 테스트 가능
5. **다국어 지원**: 설정 파일로 다국어 지원 가능
6. **버전 관리**: 설정 변경 이력 추적 가능

### 사용 방법

```python
from config.config_loader import config_loader

# 공통 설정
domains = config_loader.get_banking_domains()
intents = config_loader.get_common_intents()

# 에이전트별 설정
tool_mapping = config_loader.get_intent_tool_mapping("domain_agent")
domain_mapping = config_loader.get_intent_domain_mapping("supervisor_agent")

# 도구 설정
tool_info = config_loader.get_tool_info("account_balance")
sample_response = config_loader.get_tool_sample_response("transfer_money")
response_format = config_loader.get_tool_response_format("loan_info")

### 다음 단계

1. 설정 파일 검증 로직 추가
2. 설정 변경 시 자동 리로드 기능
3. 설정 파일 스키마 정의
4. 설정 변경 알림 시스템 