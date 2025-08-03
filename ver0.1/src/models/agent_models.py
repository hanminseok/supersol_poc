from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class AgentType(str, Enum):
    """에이전트 유형 열거형"""
    SUPERVISOR = "supervisor"
    DOMAIN_BANKING = "domain_banking"
    DOMAIN_ASSET_MANAGEMENT = "domain_asset_management"
    WORKER_CUSTOMER_INFO = "worker_customer_info"
    WORKER_FINANCIAL_INFO = "worker_financial_info"
    WORKER_TRANSFER = "worker_transfer"
    WORKER_ACCOUNT = "worker_account"
    WORKER_AUTO_TRANSFER = "worker_auto_transfer"
    WORKER_INVESTMENT_PRODUCTS = "worker_investment_products"
    WORKER_LOAN = "worker_loan"
    QUALITY_CHECK = "quality_check"


class DomainType(str, Enum):
    """도메인 유형 열거형"""
    BANKING = "banking"
    ASSET_MANAGEMENT = "asset_management"


@dataclass
class IntentClassification:
    """의도 분류 결과"""
    intent: str
    confidence: float
    slots: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "intent": self.intent,
            "confidence": self.confidence,
            "slots": self.slots
        }


@dataclass
class AgentRequest:
    """에이전트 요청 모델"""
    agent_type: AgentType
    user_query: str
    conversation_history: List[str] = field(default_factory=list)
    intent_classification: Optional[IntentClassification] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "agent_type": self.agent_type.value,
            "user_query": self.user_query,
            "conversation_history": self.conversation_history,
            "intent_classification": self.intent_classification.to_dict() if self.intent_classification else None,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class AgentResponse:
    """에이전트 응답 모델"""
    agent_type: AgentType
    response: str
    domain: Optional[DomainType] = None
    worker: Optional[str] = None
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    reasoning: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "agent_type": self.agent_type.value,
            "response": self.response,
            "domain": self.domain.value if self.domain else None,
            "worker": self.worker,
            "tool_calls": self.tool_calls,
            "reasoning": self.reasoning,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        } 