# next_agent가 필요없는 이유 - 상세 분석

## 현재 Agent 워크플로우 구조

### **실제 Agent 체인 실행 순서:**
```
User Query → ChatService → RewritingAgent → PreprocessingAgent → SupervisorAgent → DomainAgent → Response
```

### **ChatService에서 하드코딩된 Agent 순서:**
```python
# chat_service.py에서 명시적으로 정의된 순서
class ChatService:
    def __init__(self):
        self.rewriting_agent = RewritingAgent()
        self.preprocessing_agent = PreprocessingAgent()
        self.supervisor_agent = SupervisorAgent()
        self.domain_agent = DomainAgent()
    
    async def process_chat(self, session_id: str, user_query: str, customer_info: Optional[Dict[str, Any]] = None):
        # 1. Rewriting Agent
        rewriting_result = await self._execute_rewriting_agent(user_query, context)
        
        # 2. Preprocessing Agent
        preprocessing_result = await self._execute_preprocessing_agent(rewriting_result, context)
        
        # 3. Supervisor Agent
        supervisor_result = await self._execute_supervisor_agent(preprocessing_result, context)
        
        # 4. Domain Agent
        domain_result = await self._execute_domain_agent(supervisor_result, context)
```

## next_agent가 사용되지 않는 이유

### 1. **하드코딩된 워크플로우**
- **문제**: Agent 순서가 `ChatService`에서 하드코딩됨
- **결과**: JSON 설정의 `next_agent` 필드가 무시됨
- **증거**: 코드에서 `next_agent`를 참조하는 부분이 없음

### 2. **중앙 집중식 오케스트레이션**
```python
# chat_service.py에서 모든 Agent 호출을 직접 관리
async def _execute_rewriting_agent(self, user_query: str, context: Dict[str, Any]) -> Dict[str, Any]:
    return await self.rewriting_agent.execute({
        "query": user_query,
        "conversation_context": context.get("conversation_history", []),
        "current_state": context.get("current_state", {})
    })

async def _execute_preprocessing_agent(self, rewriting_result: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    return await self.preprocessing_agent.execute({
        "rewritten_text": rewriting_result.get("rewritten_text", ""),
        "topic": rewriting_result.get("topic", ""),
        "conversation_context": context.get("conversation_history", []),
        "current_state": context.get("current_state", {})
    })
```

### 3. **Agent 간 직접 통신 부재**
- **현재 구조**: Agent → ChatService → 다음 Agent
- **필요한 구조**: Agent → 다음 Agent (직접 통신)
- **문제**: Agent가 다음 Agent를 직접 호출하지 않음

### 4. **동적 라우팅 불가능**
```json
// 현재 JSON 설정
{
    "next_agent": ["preprocessing"]  // 항상 preprocessing으로만 라우팅
}
```

**실제로는:**
- Supervisor Agent가 도메인을 결정
- Domain Agent가 Worker를 결정
- 동적 라우팅이 필요하지만 `next_agent`로는 불가능

## next_agent가 작동하려면 필요한 구조

### **Option 1: Agent 간 직접 통신**
```python
class RewritingAgent(BaseAgent):
    async def _process(self, input_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        # 처리 로직
        result = self._process_logic(input_data)
        
        # next_agent 호출
        next_agent_name = self.config.next_agent[0]  # "preprocessing"
        next_agent = self._get_agent(next_agent_name)
        return await next_agent.execute(result)
```

### **Option 2: 동적 워크플로우 엔진**
```python
class WorkflowEngine:
    def __init__(self):
        self.agents = {}
        self.workflows = {}
    
    async def execute_workflow(self, workflow_name: str, input_data: Dict[str, Any]):
        workflow = self.workflows[workflow_name]
        current_agent = workflow.start_agent
        
        while current_agent:
            result = await current_agent.execute(input_data)
            current_agent = self._get_next_agent(current_agent, result)
```

## 현재 구조의 장점

### 1. **명확한 제어 흐름**
```python
# chat_service.py에서 전체 흐름을 한눈에 파악 가능
async def process_chat(self, session_id: str, user_query: str):
    # 1. Rewriting
    rewriting_result = await self._execute_rewriting_agent(user_query, context)
    
    # 2. Preprocessing  
    preprocessing_result = await self._execute_preprocessing_agent(rewriting_result, context)
    
    # 3. Supervisor
    supervisor_result = await self._execute_supervisor_agent(preprocessing_result, context)
    
    # 4. Domain
    domain_result = await self._execute_domain_agent(supervisor_result, context)
```

### 2. **에러 처리 및 복구**
```python
try:
    rewriting_result = await self._execute_rewriting_agent(user_query, context)
except Exception as e:
    # 기본값으로 복구
    rewriting_result = {
        "rewritten_text": user_query,
        "topic": "general",
        "context_used": False
    }
```

### 3. **컨텍스트 관리**
```python
# 각 Agent 실행 후 컨텍스트 업데이트
context = self._update_context_with_result(context, "rewriting", rewriting_result)
context = self._update_context_with_result(context, "preprocessing", preprocessing_result)
```

## 결론: next_agent 제거 권장

### **제거 이유:**
1. **사용되지 않음**: 코드에서 참조되지 않음
2. **구조적 불일치**: 현재 아키텍처와 맞지 않음
3. **유지보수 부담**: 불필요한 설정 관리
4. **혼란 야기**: 실제 동작과 설정이 다름

### **대안:**
1. **현재 구조 유지**: ChatService에서 하드코딩된 워크플로우
2. **향후 개선**: 동적 워크플로우 엔진 도입 시 next_agent 재검토

### **즉시 제거 가능:**
```json
// 제거 전
{
    "name": "rewriting_agent",
    "next_agent": ["preprocessing"],  // ← 제거
    "system_prompt": "...",
    // ...
}

// 제거 후
{
    "name": "rewriting_agent",
    "system_prompt": "...",
    // ...
}
```

**결과**: 설정 파일 간소화, 혼란 제거, 유지보수성 향상 