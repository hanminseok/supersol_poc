import json
from typing import Dict, Any, Optional
from .base_agent import BaseAgent
from models.agent_config import get_agent_config

class RewritingAgent(BaseAgent):
    """
    사용자 질문을 대화 맥락을 고려하여 명확하고 구체적으로 재작성하는 에이전트
    
    주요 기능:
    - 대화 컨텍스트를 고려한 질문 재작성
    - 참조 해결 (예: "그 계좌" → 구체적인 계좌 정보)
    - 주제 분류 (banking, account, loan, investment, general)
    """
    
    def __init__(self):
        config = get_agent_config("rewriting_agent")
        if not config:
            raise ValueError("Rewriting agent config not found")
        super().__init__(config)
    
    async def _process(self, input_data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """질문 재작성 처리 - 멀티턴 질의 지원"""
        query = input_data.get("query", "")
        
        # 컨텍스트에서 추가 정보 추출
        conversation_context = input_data.get("conversation_context", [])
        current_state = input_data.get("current_state", {})
        
        # 입력 데이터 로깅 - 사용자 질의와 과거 질의 정보 표시
        self.logger.info(f"=== {self.config.name} Input ===")
        self.logger.info(f"User Query: {query}")
        
        # 과거 질의 정보 로깅
        if conversation_context:
            self.logger.info(f"Past Queries Count: {len(conversation_context)}")
            past_queries = [entry.get("user_query", "") for entry in conversation_context]
            self.logger.info(f"Past Queries: {past_queries}")
        else:
            self.logger.info("Past Queries Count: 0")
            self.logger.info("Past Queries: []")
        
        # 대화 맥락을 포함한 프롬프트 생성
        context_prompt = self._build_context_aware_prompt(query, conversation_context, current_state)
        
        # LLM 호출
        messages = [
            self._create_system_message(),
            self._create_user_message(context_prompt)
        ]
        
        response = await self._call_llm(messages)
        
        # JSON 응답 파싱 - 개선된 버전
        result = self._parse_json_response(response, input_data)
        
        # conditional_routing 처리
        result = await self._handle_conditional_routing(result, query, context)
        
        # 출력 데이터 로깅 - LLM 결과만 표시
        self.logger.info(f"=== {self.config.name} Output ===")
        self.logger.info(f"LLM Result: {result}")
        
        return result
    
    async def _handle_conditional_routing(self, result: Dict[str, Any], query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """조건부 라우팅 처리 - topic이 general일 경우 직접 답변"""
        topic = result.get("topic", "general")
        is_general = result.get("is_general", False)
        
        # topic이 general이거나 is_general이 True인 경우
        if topic == "general" or is_general:
            self.logger.info(f"Topic is general, generating direct response")
            
            # conditional_routing 설정에서 response_prompt 가져오기
            conditional_routing = self.config.get("conditional_routing", {})
            conditions = conditional_routing.get("conditions", [])
            
            response_prompt = None
            for condition in conditions:
                if condition.get("condition") == "topic == 'general'":
                    response_prompt = condition.get("response_prompt")
                    break
            
            if response_prompt:
                # LLM을 사용하여 직접 답변 생성
                direct_response = await self._generate_direct_response(query, response_prompt, context)
                result["direct_response"] = direct_response
                result["should_skip_next_agent"] = True
                self.logger.info(f"Generated direct response: {direct_response}")
            else:
                # 기본 답변
                result["direct_response"] = "죄송합니다. 은행 업무와 관련되지 않은 질문입니다. 은행 서비스(계좌, 대출, 투자 등)에 대해 문의해 주시기 바랍니다."
                result["should_skip_next_agent"] = True
                self.logger.info("Using default response for general topic")
        
        return result
    
    async def _generate_direct_response(self, query: str, response_prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """일반 질문에 대한 직접 답변 생성"""
        try:
            # 간단한 프롬프트로 LLM 호출
            messages = [
                {"role": "system", "content": response_prompt},
                {"role": "user", "content": f"사용자 질문: {query}"}
            ]
            
            # 비동기적으로 LLM 호출
            import asyncio
            try:
                # 현재 실행 중인 이벤트 루프가 있는지 확인
                loop = asyncio.get_running_loop()
                # 새 태스크 생성하여 실행
                task = asyncio.create_task(self._call_llm(messages))
                response = await task
            except RuntimeError:
                # 이벤트 루프가 실행 중이지 않은 경우
                response = await self._call_llm(messages)
            
            return response.strip()
            
        except Exception as e:
            self.logger.error(f"Error generating direct response: {str(e)}")
            return "죄송합니다. 질문에 대한 답변을 생성하는 중 오류가 발생했습니다."
    
    def _prepare_next_agent_input(self, current_result: Dict[str, Any], original_input: Dict[str, Any]) -> Dict[str, Any]:
        """다음 Agent(Preprocessing)의 입력 데이터 준비"""
        return {
            "rewritten_text": current_result.get("rewritten_text", ""),
            "topic": current_result.get("topic", ""),
            "conversation_context": original_input.get("conversation_context", []),
            "current_state": original_input.get("current_state", {})
        }
    
    def _parse_json_response(self, response: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """JSON 응답 파싱 - 개선된 버전"""
        if not response or response.strip() == "":
            self.logger.warning(f"Empty response from {self.config.name}")
            return self._create_default_response(input_data)
        
        # JSON 블록 추출 시도
        json_response = self._extract_json_from_response(response)
        
        try:
            result = json.loads(json_response)
            
            # 필수 필드 확인 및 기본값 설정
            rewritten_text = result.get("rewritten_text", "")
            topic = result.get("topic", "general")
            context_used = result.get("context_used", False)
            is_general = result.get("is_general", False)
            direct_response = result.get("direct_response", "")
            
            if not rewritten_text:
                self.logger.warning(f"Empty rewritten_text in response from {self.config.name}")
                return self._create_default_response(input_data, topic)
            
            return {
                "rewritten_text": rewritten_text,
                "topic": topic,
                "context_used": context_used,
                "is_general": is_general,
                "direct_response": direct_response
            }
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON response from {self.config.name}: {str(e)}")
            self.logger.error(f"Raw response: {response}")
            return self._create_default_response(input_data)
    
    def _extract_json_from_response(self, response: str) -> str:
        """응답에서 JSON 블록 추출"""
        response = response.strip()
        
        # JSON 블록이 ```json ... ``` 형태로 감싸져 있는 경우
        if "```json" in response and "```" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            if end != -1:
                return response[start:end].strip()
        
        # JSON 블록이 ``` ... ``` 형태로 감싸져 있는 경우
        if "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            if end != -1:
                return response[start:end].strip()
        
        # 중괄호로 시작하고 끝나는 JSON 찾기
        if response.startswith("{") and response.endswith("}"):
            return response
        
        # 중괄호로 시작하는 부분 찾기
        start = response.find("{")
        if start != -1:
            # 중괄호 카운팅으로 JSON 끝 찾기
            brace_count = 0
            for i, char in enumerate(response[start:], start):
                if char == "{":
                    brace_count += 1
                elif char == "}":
                    brace_count -= 1
                    if brace_count == 0:
                        return response[start:i+1]
        
        return response
    
    def _create_default_response(self, input_data: Dict[str, Any], topic: str = None) -> Dict[str, Any]:
        """기본 응답 생성 - 설정에서 기본값 가져오기"""
        original_query = input_data.get("query", "")
        if isinstance(original_query, list):
            original_query = " ".join(original_query)
        
        # 설정에서 기본값 가져오기
        context_settings = self.config.get("context_settings", {})
        default_topic = topic or context_settings.get("default_topic", "general")
        default_response = context_settings.get("default_response", "질문을 이해하지 못했습니다.")
        
        return {
            "rewritten_text": original_query if original_query else default_response,
            "topic": default_topic,
            "context_used": False
        }
    
    def _build_context_aware_prompt(self, query: str, conversation_context: list, current_state: dict) -> str:
        """컨텍스트를 고려한 프롬프트 생성"""
        # 대화 컨텍스트 요약
        context_summary = self._summarize_conversation_context(conversation_context)
        
        # 현재 상태 정보
        current_state_info = self._format_current_state(current_state)
        
        # 참조 해결 가이드 생성
        reference_guide = self._generate_reference_guide(conversation_context, current_state)
        
        # 설정에서 주제 목록 가져오기
        topics = self.config.get("topics", {})
        topics_list = ", ".join(topics.keys())
        
        # 설정에서 프롬프트 템플릿 가져오기
        prompt_config = self.config.get("prompt", {})
        context_aware_prompt_template = prompt_config.get("context_aware_prompt", [])
        
        # 문자열과 배열 형식 모두 처리
        if isinstance(context_aware_prompt_template, str):
            # 문자열인 경우 직접 포맷팅
            prompt = context_aware_prompt_template.format(
                query=query,
                context_summary=context_summary,
                current_state_info=current_state_info,
                reference_guide=reference_guide,
                topics_list=topics_list
            )
        elif isinstance(context_aware_prompt_template, list):
            # 배열인 경우 줄바꿈으로 연결 후 포맷팅
            prompt_lines = context_aware_prompt_template
            prompt_text = "\n".join(prompt_lines)
            prompt = prompt_text.format(
                query=query,
                context_summary=context_summary,
                current_state_info=current_state_info,
                reference_guide=reference_guide,
                topics_list=topics_list
            )
        else:
            # 기본값으로 빈 문자열
            prompt = ""
        
        return prompt
    
    def _summarize_conversation_context(self, conversation_context: list) -> str:
        """대화 컨텍스트 요약"""
        if not conversation_context:
            return "이전 대화 없음"
        
        summary_parts = []
        
        # 설정에서 최대 대화 항목 수 가져오기
        context_settings = self.config.get("context_settings", {})
        max_entries = context_settings.get("max_conversation_entries", 3)
        
        for i, entry in enumerate(conversation_context[-max_entries:]):
            user_query = entry.get("user_query", "")
            extracted_info = entry.get("extracted_info", {})
            
            summary = f"대화 {i+1}: {user_query}"
            
            # 추출된 정보 추가
            intent = extracted_info.get("intent")
            tool_name = extracted_info.get("tool_name")
            accounts = extracted_info.get("accounts_mentioned", [])
            
            if intent:
                summary += f" (의도: {intent})"
            if tool_name:
                summary += f" (도구: {tool_name})"
            if accounts:
                summary += f" (계좌: {', '.join(accounts)})"
            
            summary_parts.append(summary)
        
        return "\n".join(summary_parts)
    
    def _format_current_state(self, current_state: dict) -> str:
        """현재 상태 정보 포맷팅"""
        if not current_state:
            return "상태 정보 없음"
        
        state_parts = []
        
        selected_account = current_state.get("selected_account")
        if selected_account:
            state_parts.append(f"- 선택된 계좌: {selected_account}")
        
        last_intent = current_state.get("last_intent")
        if last_intent:
            state_parts.append(f"- 이전 의도: {last_intent}")
        
        last_slots = current_state.get("last_slots", [])
        if last_slots:
            state_parts.append(f"- 이전 슬롯: {', '.join(last_slots)}")
        
        pending_action = current_state.get("pending_action")
        if pending_action:
            state_parts.append(f"- 진행 중인 작업: {pending_action}")
        
        if not state_parts:
            return "상태 정보 없음"
        
        return "\n".join(state_parts)
    
    def _generate_reference_guide(self, conversation_context: list, current_state: dict) -> str:
        """참조 해결 가이드 생성"""
        guide_parts = []
        
        # 이전 대화에서 언급된 계좌 정보
        mentioned_accounts = []
        for entry in conversation_context:
            extracted_info = entry.get("extracted_info", {})
            accounts = extracted_info.get("accounts_mentioned", [])
            mentioned_accounts.extend(accounts)
        
        if mentioned_accounts:
            unique_accounts = list(set(mentioned_accounts))
            guide_parts.append(f"- 언급된 계좌: {', '.join(unique_accounts)}")
        
        # 현재 선택된 계좌
        selected_account = current_state.get("selected_account")
        if selected_account:
            guide_parts.append(f"- 현재 선택된 계좌: {selected_account}")
        
        # 이전 의도
        last_intent = current_state.get("last_intent")
        if last_intent:
            guide_parts.append(f"- 이전 의도: {last_intent}")
        
        # 설정에서 참조 해결 규칙 가져오기
        reference_resolution = self.config.get("reference_resolution", {})
        reference_rules = reference_resolution.get("rules", [])
        
        if reference_rules:
            guide_parts.append("- 참조 해결 규칙:")
            for rule in reference_rules:
                guide_parts.append(f"  * {rule}")
        
        if not guide_parts:
            return "참조 해결 가이드 없음"
        
        return "\n".join(guide_parts) 