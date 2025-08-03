#!/usr/bin/env python3
"""
Mock LLM Client for Testing
"""

import json
import asyncio
from typing import List, Dict, Any

class MockLLMClient:
    """테스트용 모의 LLM 클라이언트"""
    
    def __init__(self):
        self.chat = MockChat(self)
        self.responses = {
            "rewriting_agent": {
                "rewritten_text": "사용자 질문을 명확하게 재작성한 결과입니다.",
                "topic": "general",
                "context_used": False
            },
            "preprocessing_agent": {
                "normalized_text": "정규화된 텍스트입니다.",
                "intent": "general_inquiry",
                "slot": [],
                "context_used": False
            },
            "supervisor_agent": {
                "target_domain": "general",
                "normalized_text": "정규화된 텍스트입니다.",
                "intent": "general_inquiry",
                "slot": [],
                "context": {},
                "routing_reasoning": "일반 문의로 분류되었습니다."
            },
            "domain_agent": {
                "tool_name": "general_inquiry",
                "tool_input": {},
                "tool_output": {
                    "response": "일반 문의에 대한 답변입니다.",
                    "category": "general"
                },
                "context": {},
                "enhanced_slots": []
            }
        }
    
    async def chat_completions_create(self, messages: List[Dict[str, Any]], **kwargs):
        """모의 LLM 응답 생성"""
        # 메시지에서 에이전트 타입 추출
        agent_type = self._extract_agent_type(messages)
        
        # 모의 응답 생성
        mock_response = self._generate_mock_response(agent_type, messages)
        
        # OpenAI 응답 형식으로 변환
        return MockResponse(mock_response)
    
    def _extract_agent_type(self, messages: List[Dict[str, Any]]) -> str:
        """메시지에서 에이전트 타입 추출"""
        for message in messages:
            if message.get("role") == "system":
                content = message.get("content", "")
                # 더 구체적인 키워드로 에이전트 타입 판별
                if "재작성" in content or "rewriting" in content.lower():
                    return "rewriting_agent"
                elif "전처리" in content or "preprocessing" in content.lower():
                    return "preprocessing_agent"
                elif "감독" in content or "supervisor" in content.lower():
                    return "supervisor_agent"
                elif "도메인" in content or "domain" in content.lower():
                    return "domain_agent"
            
            # 사용자 메시지에서도 힌트 찾기
            elif message.get("role") == "user":
                content = message.get("content", "")
                # 프롬프트에서 에이전트 타입 힌트 찾기
                if "재작성" in content or "rewritten_text" in content:
                    return "rewriting_agent"
                elif "정규화" in content or "normalized_text" in content:
                    return "preprocessing_agent"
                elif "도메인" in content or "target_domain" in content:
                    return "supervisor_agent"
                elif "도구" in content or "tool_name" in content:
                    return "domain_agent"
        
        # 기본값으로 rewriting_agent 반환 (대부분의 경우)
        return "rewriting_agent"
    
    def _generate_mock_response(self, agent_type: str, messages: List[Dict[str, Any]]) -> str:
        """에이전트 타입에 따른 모의 응답 생성"""
        base_response = self.responses.get(agent_type, {})
        
        # 사용자 메시지에서 질문 추출
        user_message = ""
        for message in messages:
            if message.get("role") == "user":
                user_message = message.get("content", "")
                break
        
        # 질문에 따른 동적 응답 생성
        if any(keyword in user_message for keyword in ["잔액", "계좌", "통장"]):
            if agent_type == "rewriting_agent":
                return json.dumps({
                    "rewritten_text": "계좌 잔액을 조회하고 싶습니다.",
                    "topic": "account",
                    "context_used": False
                })
            elif agent_type == "preprocessing_agent":
                return json.dumps({
                    "normalized_text": "계좌 잔액을 조회하고 싶습니다.",
                    "intent": "check_balance",
                    "slot": ["account_number"],
                    "context_used": False
                })
            elif agent_type == "supervisor_agent":
                return json.dumps({
                    "target_domain": "account",
                    "normalized_text": "계좌 잔액을 조회하고 싶습니다.",
                    "intent": "check_balance",
                    "slot": ["account_number"],
                    "context": {},
                    "routing_reasoning": "계좌 관련 문의로 account 도메인으로 라우팅"
                })
            elif agent_type == "domain_agent":
                return json.dumps({
                    "tool_name": "account_balance",
                    "tool_input": {"account_number": "123-456-789"},
                    "tool_output": {
                        "balance": "1,000,000원",
                        "currency": "KRW",
                        "last_updated": "2024-01-15 14:30:00"
                    },
                    "context": {},
                    "enhanced_slots": ["account_number"]
                })
        
        elif any(keyword in user_message for keyword in ["송금", "이체", "보내", "돈"]):
            if agent_type == "rewriting_agent":
                return json.dumps({
                    "rewritten_text": "송금을 진행하고 싶습니다.",
                    "topic": "banking",
                    "context_used": False
                })
            elif agent_type == "preprocessing_agent":
                return json.dumps({
                    "normalized_text": "송금을 진행하고 싶습니다.",
                    "intent": "transfer_money",
                    "slot": ["amount", "recipient"],
                    "context_used": False
                })
            elif agent_type == "supervisor_agent":
                return json.dumps({
                    "target_domain": "banking",
                    "normalized_text": "송금을 진행하고 싶습니다.",
                    "intent": "transfer_money",
                    "slot": ["amount", "recipient"],
                    "context": {},
                    "routing_reasoning": "송금 관련 문의로 banking 도메인으로 라우팅"
                })
            elif agent_type == "domain_agent":
                return json.dumps({
                    "tool_name": "transfer_money",
                    "tool_input": {"amount": "100,000원", "recipient": "수신자"},
                    "tool_output": {
                        "status": "success",
                        "transaction_id": "TXN123456789",
                        "amount": "100,000원",
                        "recipient": "수신자"
                    },
                    "context": {},
                    "enhanced_slots": ["amount", "recipient"]
                })
        
        elif any(keyword in user_message for keyword in ["대출", "담보", "이자", "금리"]):
            if agent_type == "rewriting_agent":
                return json.dumps({
                    "rewritten_text": "대출 정보를 확인하고 싶습니다.",
                    "topic": "loan",
                    "context_used": False
                })
            elif agent_type == "preprocessing_agent":
                return json.dumps({
                    "normalized_text": "대출 정보를 확인하고 싶습니다.",
                    "intent": "loan_inquiry",
                    "slot": ["loan_type"],
                    "context_used": False
                })
            elif agent_type == "supervisor_agent":
                return json.dumps({
                    "target_domain": "loan",
                    "normalized_text": "대출 정보를 확인하고 싶습니다.",
                    "intent": "loan_inquiry",
                    "slot": ["loan_type"],
                    "context": {},
                    "routing_reasoning": "대출 관련 문의로 loan 도메인으로 라우팅"
                })
            elif agent_type == "domain_agent":
                return json.dumps({
                    "tool_name": "loan_info",
                    "tool_input": {"loan_type": "신용대출"},
                    "tool_output": {
                        "available_loan_amount": "50,000,000원",
                        "interest_rate": "3.5%",
                        "loan_types": ["신용대출", "담보대출", "전세자금대출"]
                    },
                    "context": {},
                    "enhanced_slots": ["loan_type"]
                })
        
        elif any(keyword in user_message for keyword in ["환전", "유로", "달러", "엔화"]):
            if agent_type == "rewriting_agent":
                return json.dumps({
                    "rewritten_text": "환전 정보를 확인하고 싶습니다.",
                    "topic": "foreign_exchange",
                    "context_used": False
                })
            elif agent_type == "preprocessing_agent":
                return json.dumps({
                    "normalized_text": "환전 정보를 확인하고 싶습니다.",
                    "intent": "exchange_rate_inquiry",
                    "slot": ["currency", "amount"],
                    "context_used": False
                })
            elif agent_type == "supervisor_agent":
                return json.dumps({
                    "target_domain": "foreign_exchange",
                    "normalized_text": "환전 정보를 확인하고 싶습니다.",
                    "intent": "exchange_rate_inquiry",
                    "slot": ["currency", "amount"],
                    "context": {},
                    "routing_reasoning": "환전 관련 문의로 foreign_exchange 도메인으로 라우팅"
                })
            elif agent_type == "domain_agent":
                return json.dumps({
                    "tool_name": "exchange_rate",
                    "tool_input": {"currency": "EUR", "amount": "500,000원"},
                    "tool_output": {
                        "exchange_rate": "1,350원",
                        "converted_amount": "370.37 EUR",
                        "currency": "EUR"
                    },
                    "context": {},
                    "enhanced_slots": ["currency", "amount"]
                })
        
        elif any(keyword in user_message for keyword in ["자동이체", "자동 이체", "등록", "해지"]):
            if agent_type == "rewriting_agent":
                return json.dumps({
                    "rewritten_text": "자동이체 서비스를 이용하고 싶습니다.",
                    "topic": "banking",
                    "context_used": False
                })
            elif agent_type == "preprocessing_agent":
                return json.dumps({
                    "normalized_text": "자동이체 서비스를 이용하고 싶습니다.",
                    "intent": "auto_transfer_service",
                    "slot": ["amount", "schedule", "recipient"],
                    "context_used": False
                })
            elif agent_type == "supervisor_agent":
                return json.dumps({
                    "target_domain": "banking",
                    "normalized_text": "자동이체 서비스를 이용하고 싶습니다.",
                    "intent": "auto_transfer_service",
                    "slot": ["amount", "schedule", "recipient"],
                    "context": {},
                    "routing_reasoning": "자동이체 관련 문의로 banking 도메인으로 라우팅"
                })
            elif agent_type == "domain_agent":
                return json.dumps({
                    "tool_name": "auto_transfer",
                    "tool_input": {"amount": "100,000원", "schedule": "매월 21일", "recipient": "수신자"},
                    "tool_output": {
                        "status": "success",
                        "auto_transfer_id": "AT123456789",
                        "amount": "100,000원",
                        "schedule": "매월 21일",
                        "recipient": "수신자"
                    },
                    "context": {},
                    "enhanced_slots": ["amount", "schedule", "recipient"]
                })
        
        elif any(keyword in user_message for keyword in ["펀드", "투자", "수익률", "포트폴리오"]):
            if agent_type == "rewriting_agent":
                return json.dumps({
                    "rewritten_text": "투자 상품 정보를 확인하고 싶습니다.",
                    "topic": "investment",
                    "context_used": False
                })
            elif agent_type == "preprocessing_agent":
                return json.dumps({
                    "normalized_text": "투자 상품 정보를 확인하고 싶습니다.",
                    "intent": "investment_info",
                    "slot": ["investment_product"],
                    "context_used": False
                })
            elif agent_type == "supervisor_agent":
                return json.dumps({
                    "target_domain": "investment",
                    "normalized_text": "투자 상품 정보를 확인하고 싶습니다.",
                    "intent": "investment_info",
                    "slot": ["investment_product"],
                    "context": {},
                    "routing_reasoning": "투자 관련 문의로 investment 도메인으로 라우팅"
                })
            elif agent_type == "domain_agent":
                return json.dumps({
                    "tool_name": "investment_info",
                    "tool_input": {"investment_product": "펀드"},
                    "tool_output": {
                        "products": ["주식형펀드", "채권형펀드", "혼합형펀드"],
                        "current_rates": {"주식형펀드": "5.2%", "채권형펀드": "3.1%", "혼합형펀드": "4.3%"}
                    },
                    "context": {},
                    "enhanced_slots": ["investment_product"]
                })
        
        elif any(keyword in user_message for keyword in ["조건", "어떻게", "가능한가"]):
            if agent_type == "rewriting_agent":
                return json.dumps({
                    "rewritten_text": "서비스 조건을 확인하고 싶습니다.",
                    "topic": "general",
                    "context_used": False
                })
            elif agent_type == "preprocessing_agent":
                return json.dumps({
                    "normalized_text": "서비스 조건을 확인하고 싶습니다.",
                    "intent": "service_condition_inquiry",
                    "slot": ["service_type"],
                    "context_used": False
                })
            elif agent_type == "supervisor_agent":
                return json.dumps({
                    "target_domain": "general",
                    "normalized_text": "서비스 조건을 확인하고 싶습니다.",
                    "intent": "service_condition_inquiry",
                    "slot": ["service_type"],
                    "context": {},
                    "routing_reasoning": "서비스 조건 문의로 general 도메인으로 라우팅"
                })
            elif agent_type == "domain_agent":
                return json.dumps({
                    "tool_name": "service_condition",
                    "tool_input": {"service_type": "일반"},
                    "tool_output": {
                        "conditions": "서비스 이용 조건입니다.",
                        "requirements": ["신분증", "계좌개설"],
                        "fees": "수수료 정보"
                    },
                    "context": {},
                    "enhanced_slots": ["service_type"]
                })
        
        # 기본 응답 - rewriting_agent의 경우 올바른 JSON 형식으로 반환
        if agent_type == "rewriting_agent":
            # 사용자 질문을 그대로 rewritten_text로 사용
            return json.dumps({
                "rewritten_text": user_message if user_message else "사용자 질문을 명확하게 재작성한 결과입니다.",
                "topic": "general",
                "context_used": False
            })
        else:
            return json.dumps(base_response)

class MockResponse:
    """모의 OpenAI 응답 객체"""
    
    def __init__(self, content: str):
        self.choices = [MockChoice(content)]
        self.usage = MockUsage()

class MockChoice:
    """모의 OpenAI Choice 객체"""
    
    def __init__(self, content: str):
        self.message = MockMessage(content)

class MockMessage:
    """모의 OpenAI Message 객체"""
    
    def __init__(self, content: str):
        self.content = content

class MockUsage:
    """모의 OpenAI Usage 객체"""
    
    def __init__(self):
        self.prompt_tokens = 100
        self.completion_tokens = 50
        self.total_tokens = 150

class MockChat:
    """모의 OpenAI Chat 객체"""
    
    def __init__(self, mock_client: MockLLMClient):
        self.completions = MockCompletions(mock_client)

class MockCompletions:
    """모의 OpenAI Completions 객체"""
    
    def __init__(self, mock_client: MockLLMClient):
        self.mock_client = mock_client
    
    def create(self, messages, **kwargs):
        """모의 completions.create 메서드"""
        # MockLLMClient의 _generate_mock_response 메서드 사용
        agent_type = self.mock_client._extract_agent_type(messages)
        mock_response = self.mock_client._generate_mock_response(agent_type, messages)
        return MockResponse(mock_response)

# 전역 모의 LLM 클라이언트 인스턴스
mock_llm_client = MockLLMClient() 