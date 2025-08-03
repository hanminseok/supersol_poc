from typing import List, Dict, Any
from ..logger import preprocessing_logger
from ..models.agent_models import IntentClassification
from .text_normalizer import TextNormalizer
from .query_rewriter import QueryRewriter
from .intent_classifier import IntentClassifier


class PreprocessingPipeline:
    """전처리 파이프라인 클래스"""
    
    def __init__(self):
        """전처리 파이프라인을 초기화합니다."""
        self.text_normalizer = TextNormalizer()
        self.query_rewriter = QueryRewriter()
        self.intent_classifier = IntentClassifier()
        self.logger = preprocessing_logger
    
    def process(self, query: str, conversation_history: List[str] = None) -> Dict[str, Any]:
        """전처리 파이프라인을 실행합니다."""
        try:
            self.logger.info(f"전처리 파이프라인 시작: {query[:50]}...")
            
            if conversation_history is None:
                conversation_history = []
            
            # 1. 텍스트 정규화
            normalized_query = self.text_normalizer.normalize(query)
            
            # 2. 질의 재작성
            rewritten_query = self.query_rewriter.rewrite(normalized_query, conversation_history)
            
            # 3. 의도 분류
            intent_classification = self.intent_classifier.classify(rewritten_query)
            
            # 결과 구성
            result = {
                "original_query": query,
                "normalized_query": normalized_query,
                "rewritten_query": rewritten_query,
                "intent_classification": intent_classification,
                "conversation_history": conversation_history
            }
            
            self.logger.info(f"전처리 파이프라인 완료: 의도={intent_classification.intent}")
            return result
            
        except Exception as e:
            self.logger.log_error_with_context(e, "PreprocessingPipeline.process")
            # 에러 시 기본 결과 반환
            return {
                "original_query": query,
                "normalized_query": query,
                "rewritten_query": query,
                "intent_classification": IntentClassification(
                    intent="기타",
                    confidence=0.0,
                    slots={}
                ),
                "conversation_history": conversation_history or []
            }
    
    def get_context(self, query: str, intent_classification: IntentClassification) -> str:
        """컨텍스트를 추출합니다."""
        try:
            context_parts = []
            
            # 의도 기반 컨텍스트
            if intent_classification.intent != "기타":
                context_parts.append(f"사용자 의도: {intent_classification.intent}")
            
            # 슬롯 기반 컨텍스트
            if intent_classification.slots:
                slot_contexts = []
                for key, value in intent_classification.slots.items():
                    slot_contexts.append(f"{key}: {value}")
                context_parts.append(f"추출된 정보: {', '.join(slot_contexts)}")
            
            # 신뢰도 기반 컨텍스트
            if intent_classification.confidence > 0.7:
                context_parts.append("높은 신뢰도의 의도 분류")
            elif intent_classification.confidence < 0.3:
                context_parts.append("낮은 신뢰도의 의도 분류")
            
            return "; ".join(context_parts) if context_parts else "일반적인 질의"
            
        except Exception as e:
            self.logger.log_error_with_context(e, "PreprocessingPipeline.get_context")
            return "일반적인 질의" 