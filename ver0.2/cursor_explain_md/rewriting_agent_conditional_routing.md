# RewritingAgent Conditional Routing 기능

## 개요

`RewritingAgent`는 사용자의 질문을 분석하여 `topic`을 분류하고, `topic`이 `general`일 경우 다음 Agent를 호출하지 않고 LLM이 직접 답변을 생성하는 조건부 라우팅 기능을 제공합니다.

## 주요 기능

### 1. 조건부 라우팅 (Conditional Routing)

- **일반 질문 감지**: 은행 업무와 관련되지 않은 일반적인 질문을 `general` topic으로 분류
- **직접 답변 생성**: `general` topic일 경우 LLM이 직접 친절하고 도움이 되는 답변 생성
- **워크플로우 최적화**: 불필요한 Agent 호출을 건너뛰어 응답 속도 향상

### 2. 설정 구조

```json
{
    "conditional_routing": {
        "conditions": [
            {
                "condition": "topic == 'general'",
                "action": "self_respond",
                "response_prompt": "사용자의 질문에 대해 친절하고 도움이 되는 답변을 제공해주세요. 은행 업무와 관련되지 않은 일반적인 질문이므로, 일반적인 지식과 경험을 바탕으로 답변해주세요."
            }
        ]
    }
}
```

### 3. 동작 방식

#### 일반 질문 처리 흐름
1. 사용자 질문 입력
2. LLM이 질문을 분석하여 `topic` 분류
3. `topic`이 `general`인 경우:
   - `is_general`을 `True`로 설정
   - `should_skip_next_agent`를 `True`로 설정
   - LLM이 직접 답변 생성 (`direct_response`)
   - 다음 Agent 호출 건너뛰기

#### 은행 관련 질문 처리 흐름
1. 사용자 질문 입력
2. LLM이 질문을 분석하여 `topic` 분류
3. `topic`이 `account`, `banking`, `loan`, `investment`인 경우:
   - `is_general`을 `False`로 설정
   - 다음 Agent(`preprocessing`)로 정상 진행

## 구현 세부사항

### 1. 수정된 파일들

#### `ver0.2/config/agents/rewriting_agent.json`
- `conditional_routing` 설정 추가
- `response_prompt`로 LLM이 직접 답변 생성하도록 안내

#### `ver0.2/agents/rewriting_agent.py`
- `_handle_conditional_routing()` 메서드 추가
- `_generate_direct_response()` 메서드 추가
- `_parse_json_response()` 메서드에 `is_general`, `direct_response` 필드 추가
- `_process()` 메서드에 conditional_routing 처리 로직 추가

#### `ver0.2/agents/base_agent.py`
- `execute()` 메서드에 `should_skip_next_agent` 플래그 처리 로직 추가

#### `ver0.2/models/agent_config.py`
- `AgentConfig` 모델에 `conditional_routing` 필드 추가

### 2. 핵심 메서드

#### `_handle_conditional_routing()`
```python
async def _handle_conditional_routing(self, result: Dict[str, Any], query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """조건부 라우팅 처리 - topic이 general일 경우 직접 답변"""
    topic = result.get("topic", "general")
    is_general = result.get("is_general", False)
    
    if topic == "general" or is_general:
        # LLM을 사용하여 직접 답변 생성
        direct_response = await self._generate_direct_response(query, response_prompt, context)
        result["direct_response"] = direct_response
        result["should_skip_next_agent"] = True
    
    return result
```

#### `_generate_direct_response()`
```python
async def _generate_direct_response(self, query: str, response_prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
    """일반 질문에 대한 직접 답변 생성"""
    messages = [
        {"role": "system", "content": response_prompt},
        {"role": "user", "content": f"사용자 질문: {query}"}
    ]
    
    response = await self._call_llm(messages)
    return response.strip()
```

## 테스트 결과

### 1. 일반 질문 테스트 (날씨 관련)
- **입력**: "오늘 날씨가 어떤가요?"
- **결과**:
  - `topic`: `general`
  - `is_general`: `True`
  - `should_skip_next_agent`: `True`
  - `direct_response`: "죄송합니다만, 저는 실시간 정보를 제공하는 능력이 없습니다. 날씨에 대한 최신 정보를 얻으시려면, 인터넷이나 앱을 통해 현지의 날씨를 확인해 보시는 것이 가장 정확할 것입니다."

### 2. 은행 관련 질문 테스트 (계좌 잔액)
- **입력**: "내 계좌 잔액을 확인해주세요"
- **결과**:
  - `topic`: `account`
  - `is_general`: `False`
  - 다음 Agent들(`preprocessing`, `supervisor`, `domain`)로 정상 진행

## 장점

1. **응답 속도 향상**: 일반 질문에 대해 불필요한 Agent 호출을 건너뛰어 빠른 응답
2. **리소스 효율성**: 시스템 리소스 절약
3. **사용자 경험 개선**: 일반 질문에 대한 즉시 답변 제공
4. **확장성**: 다른 조건부 라우팅 규칙 추가 가능

## 향후 개선 방향

1. **다양한 조건 추가**: 다른 topic에 대한 조건부 라우팅 규칙 추가
2. **답변 품질 향상**: 더 정확하고 유용한 답변을 위한 프롬프트 개선
3. **로깅 및 모니터링**: 조건부 라우팅 사용 통계 및 성능 모니터링
4. **사용자 피드백**: 답변 품질에 대한 사용자 피드백 수집 및 반영 