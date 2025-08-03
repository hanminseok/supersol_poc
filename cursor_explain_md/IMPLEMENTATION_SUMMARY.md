# next_agent 워크플로우 구현 완료 요약

## 🎯 구현 목표
분석 문서 `analysis_next_agent_unnecessary.md`에 따라 `next_agent`가 실제로 작동하도록 프로젝트 구조를 변경했습니다.

## ✅ 구현된 변경사항

### 1. **AgentManager 클래스 생성** (`services/agent_manager.py`)
- Agent 간 직접 통신을 관리하는 중앙 집중식 매니저
- 워크플로우 실행 및 Agent 체인 관리
- Agent 이름 매핑 및 라우팅 로직

**주요 기능:**
```python
class AgentManager:
    - _initialize_agents(): 모든 Agent 초기화
    - get_agent_by_config_name(): 설정 이름으로 Agent 찾기
    - get_next_agent(): 다음 Agent 결정
    - execute_workflow(): 워크플로우 실행
    - execute_single_agent(): 단일 Agent 실행
```

### 2. **BaseAgent 수정** (`agents/base_agent.py`)
- `next_agent` 호출 기능 추가
- Agent 간 직접 통신 지원
- 재귀적 워크플로우 실행

**주요 변경사항:**
```python
async def execute(self, input_data, context, agent_manager=None):
    # Agent 처리 로직
    result = await self._process(validated_input, context)
    
    # next_agent 호출 (Agent Manager가 제공된 경우)
    if agent_manager and hasattr(self.config, 'next_agent') and self.config.next_agent:
        next_result = await self._call_next_agent(agent_manager, validated_output, input_data, context)
        return self._merge_results(validated_output, next_result)
    
    return validated_output
```

### 3. **각 Agent에 _prepare_next_agent_input 메서드 추가**

#### RewritingAgent (`agents/rewriting_agent.py`)
```python
def _prepare_next_agent_input(self, current_result, original_input):
    return {
        "rewritten_text": current_result.get("rewritten_text", ""),
        "topic": current_result.get("topic", ""),
        "conversation_context": original_input.get("conversation_context", []),
        "current_state": original_input.get("current_state", {})
    }
```

#### PreprocessingAgent (`agents/preprocessing_agent.py`)
```python
def _prepare_next_agent_input(self, current_result, original_input):
    return {
        "normalized_text": current_result.get("normalized_text", ""),
        "intent": current_result.get("intent", ""),
        "slot": current_result.get("slot", []),
        "conversation_context": original_input.get("conversation_context", []),
        "current_state": original_input.get("current_state", {})
    }
```

#### SupervisorAgent (`agents/supervisor_agent.py`)
```python
def _prepare_next_agent_input(self, current_result, original_input):
    return {
        "target_domain": current_result.get("target_domain", ""),
        "normalized_text": current_result.get("normalized_text", ""),
        "intent": current_result.get("intent", ""),
        "slot": current_result.get("slot", []),
        "context": current_result.get("context", {})
    }
```

#### DomainAgent (`agents/domain_agent.py`)
```python
def _prepare_next_agent_input(self, current_result, original_input):
    # 워크플로우 종료 (다음 Agent 없음)
    return {}
```

### 4. **ChatService 수정** (`services/chat_service.py`)
- AgentManager 사용하도록 변경
- 하드코딩된 Agent 순서 제거
- 워크플로우 기반 실행

**주요 변경사항:**
```python
class ChatService:
    def __init__(self):
        self.agent_manager = AgentManager()  # AgentManager 사용
    
    async def process_chat(self, session_id, user_query, customer_info=None):
        # Agent Manager를 통해 워크플로우 실행
        initial_input = {
            "query": user_query,
            "conversation_context": conversation_history,
            "current_state": context.get("current_state", {})
        }
        
        final_result = await self.agent_manager.execute_workflow("rewriting", initial_input, context)
```

### 5. **설정 파일 수정**
- 모든 Agent 설정에서 `system_prompt` 필드 추가
- `prompt_template` → `prompt`로 변경
- `domain_agent.json`에서 `next_agent: []`로 설정 (워크플로우 종료)

## 🔄 워크플로우 실행 흐름

### **이전 구조 (하드코딩):**
```
ChatService → RewritingAgent → ChatService → PreprocessingAgent → ChatService → SupervisorAgent → ChatService → DomainAgent
```

### **새로운 구조 (next_agent 기반):**
```
ChatService → AgentManager → RewritingAgent → PreprocessingAgent → SupervisorAgent → DomainAgent
```

### **실제 실행 순서:**
1. **RewritingAgent** 실행
2. **next_agent: ["preprocessing"]** → PreprocessingAgent 호출
3. **next_agent: ["supervisor"]** → SupervisorAgent 호출  
4. **next_agent: ["domain"]** → DomainAgent 호출
5. **next_agent: []** → 워크플로우 종료

## 🧪 테스트 결과

### **테스트 스크립트:** `test_next_agent_workflow.py`

**테스트 항목:**
- ✅ AgentManager 초기화 및 단일 Agent 실행
- ✅ 워크플로우 실행 (Agent 체인)
- ✅ ChatService 통합 테스트
- ✅ next_agent 설정 검증

**결과:** 모든 테스트 성공 (4/4)

## 🎉 구현 완료 효과

### **1. next_agent 활성화**
- JSON 설정의 `next_agent` 필드가 실제로 사용됨
- Agent 간 직접 통신 구현
- 동적 워크플로우 실행

### **2. 구조적 개선**
- 중앙 집중식 Agent 관리
- 명확한 Agent 간 인터페이스
- 확장 가능한 워크플로우 구조

### **3. 유지보수성 향상**
- Agent 순서 변경 시 설정 파일만 수정
- 새로운 Agent 추가 시 AgentManager에 등록만 하면 됨
- 워크플로우 로직과 Agent 로직 분리

## 📋 사용 방법

### **새로운 Agent 추가:**
1. Agent 클래스 생성
2. `_prepare_next_agent_input` 메서드 구현
3. AgentManager에 등록
4. 설정 파일에서 `next_agent` 설정

### **워크플로우 수정:**
1. 설정 파일의 `next_agent` 배열 수정
2. Agent 순서 변경 시 연결된 Agent들의 `_prepare_next_agent_input` 메서드 확인

### **실행:**
```python
# 기존과 동일한 방식으로 사용
chat_service = ChatService()
async for chunk in chat_service.process_chat(session_id, user_query):
    print(chunk)
```

## 🔮 향후 개선 방향

1. **동적 라우팅**: Agent 결과에 따른 조건부 라우팅
2. **병렬 실행**: 독립적인 Agent들의 병렬 처리
3. **에러 복구**: Agent 실패 시 대체 경로 제공
4. **모니터링**: 워크플로우 실행 상태 추적

---

**구현 완료일:** 2025-08-03  
**테스트 상태:** ✅ 모든 테스트 통과  
**배포 준비:** ✅ 완료 