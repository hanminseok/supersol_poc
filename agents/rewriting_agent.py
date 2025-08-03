import json
from typing import Dict, Any, Optional
from .base_agent import BaseAgent
from models.agent_config import get_agent_config
from config.config_loader import config_loader

class RewritingAgent(BaseAgent):
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
        
        # 입력 데이터 로깅
        self.logger.info(f"=== {self.config.name} Input ===")
        self.logger.info(f"Query: {query}")
        self.logger.info(f"Conversation Context: {len(conversation_context)} entries")
        self.logger.info(f"Current State: {current_state}")
        
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
        
        # 출력 데이터 로깅
        self.logger.info(f"=== {self.config.name} Output ===")
        self.logger.info(f"Result: {result}")
        
        return result
    
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
            
            if not rewritten_text:
                self.logger.warning(f"Empty rewritten_text in response from {self.config.name}")
                return self._create_default_response(input_data, topic)
            
            return {
                "rewritten_text": rewritten_text,
                "topic": topic,
                "context_used": context_used
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
        """기본 응답 생성"""
        original_query = input_data.get("query", "")
        if isinstance(original_query, list):
            original_query = " ".join(original_query)
        
        # Get default values from configuration
        context_settings = config_loader.get_context_settings()
        default_responses = config_loader.get_default_responses()
        default_topic = topic or context_settings.get("default_topic", "general")
        default_response = default_responses.get("empty_query", "질문을 이해하지 못했습니다.")
        
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
        
        # Get configuration values
        common_topics = config_loader.get_common_topics()
        topics_list = ", ".join(common_topics.keys())
        
        prompt = f"""
다음 사용자 질문을 대화 맥락을 고려하여 명확하고 구체적으로 재작성해주세요.

사용자 질문: {query}

대화 컨텍스트:
{context_summary}

현재 상태:
{current_state_info}

참조 해결 가이드:
{reference_guide}

반드시 다음 JSON 형식으로만 응답해주세요. 다른 텍스트는 포함하지 마세요:
{{
    "rewritten_text": "재작성된 명확한 질문",
    "topic": "질문의 주제 (예: {topics_list})",
    "context_used": true/false
}}

재작성 시 고려사항:
1. 대화 맥락을 고려하여 명확하게 만듭니다
2. "그 계좌", "이 계좌" 등의 표현을 구체적인 계좌 정보로 변환합니다
3. "잔액은?", "송금은?" 등의 단축 표현을 완전한 문장으로 확장합니다
4. 이전 대화에서 언급된 정보를 활용하여 맥락을 유지합니다
5. 은행 서비스와 관련된 용어를 정확히 사용합니다
6. 구체적이고 실행 가능한 질문으로 만듭니다
7. 반드시 JSON 형식을 정확히 지켜주세요

응답 예시:
{{
    "rewritten_text": "123-456-789 계좌의 잔액을 확인하고 싶습니다",
    "topic": "account",
    "context_used": true
}}
"""
        return prompt
    
    def _summarize_conversation_context(self, conversation_context: list) -> str:
        """대화 컨텍스트 요약"""
        if not conversation_context:
            return "이전 대화 없음"
        
        summary_parts = []
        
        # Get max conversation entries from configuration
        context_settings = config_loader.get_context_settings()
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
        
        # 참조 해결 규칙
        guide_parts.append("- 참조 해결 규칙:")
        reference_rules = config_loader.get_reference_resolution_rules()
        for rule in reference_rules:
            guide_parts.append(f"  * {rule}")
        
        if not guide_parts:
            return "참조 해결 가이드 없음"
        
        return "\n".join(guide_parts) 