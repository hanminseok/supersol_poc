import json
import re
from typing import Dict, Any, Tuple
from ..Config import config
from ..logger import preprocessing_logger
from ..models.agent_models import IntentClassification
from ..utils.llm_client import DeepInfraClient


class IntentClassifier:
    """의도 분류 클래스"""
    
    def __init__(self):
        """의도 분류기를 초기화합니다."""
        self.llm_client = DeepInfraClient(config.INTENT_CLASSIFICATION_MODEL)
        self.logger = preprocessing_logger
        
        # 가능한 의도 목록
        self.possible_intents = [
            "고객정보_조회", "고객정보_수정",
            "금융정보_조회",
            "이체_조회", "이체_실행",
            "계좌_조회",
            "자동이체_조회", "자동이체_실행",
            "투자상품_조회", "투자상품_실행",
            "대출_조회", "대출_실행"
        ]
    
    def classify(self, query: str) -> IntentClassification:
        """질의의 의도를 분류합니다."""
        try:
            self.logger.info(f"의도 분류 시작: {query[:50]}...")
            
            # LLM을 사용한 의도 분류
            intent, confidence, slots = self._llm_classify(query)
            
            # 결과 검증
            if intent not in self.possible_intents:
                intent = "기타"
                confidence = 0.5
            
            result = IntentClassification(
                intent=intent,
                confidence=confidence,
                slots=slots
            )
            
            self.logger.info(f"의도 분류 완료: {intent} (신뢰도: {confidence:.2f})")
            return result
            
        except Exception as e:
            self.logger.log_error_with_context(e, "IntentClassifier.classify")
            # 에러 시 기본값 반환
            return IntentClassification(
                intent="기타",
                confidence=0.0,
                slots={}
            )
    
    def _llm_classify(self, query: str) -> Tuple[str, float, Dict[str, Any]]:
        """LLM을 사용한 의도 분류를 수행합니다."""
        try:
            # 프롬프트 로드
            with open(f"{config.PROMPTS_DIR}/preprocessing_prompt.json", 'r', encoding='utf-8') as f:
                prompts = json.load(f)
            
            prompt_data = prompts["intent_classification"]
            
            # 프롬프트 구성
            system_prompt = prompt_data["system"]
            user_prompt = prompt_data["user"].format(query=query)
            
            # LLM 호출
            response = self.llm_client.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt
            )
            
            # 응답 파싱
            intent, slots = self._parse_classification_response(response)
            
            # 신뢰도 계산 (간단한 휴리스틱)
            confidence = self._calculate_confidence(query, intent)
            
            return intent, confidence, slots
            
        except Exception as e:
            self.logger.log_error_with_context(e, "IntentClassifier._llm_classify")
            return "기타", 0.0, {}
    
    def _parse_classification_response(self, response: str) -> Tuple[str, Dict[str, Any]]:
        """분류 응답을 파싱합니다."""
        intent = "기타"
        slots = {}
        
        try:
            # 의도 추출
            intent_match = re.search(r'의도:\s*(\w+)', response)
            if intent_match:
                intent = intent_match.group(1)
            
            # 슬롯 추출
            slots_match = re.search(r'슬롯:\s*(.+)', response, re.DOTALL)
            if slots_match:
                slots_text = slots_match.group(1).strip()
                slots = self._parse_slots(slots_text)
                
        except Exception as e:
            self.logger.log_error_with_context(e, "IntentClassifier._parse_classification_response")
        
        return intent, slots
    
    def _parse_slots(self, slots_text: str) -> Dict[str, Any]:
        """슬롯 텍스트를 파싱합니다."""
        slots = {}
        
        try:
            # 간단한 키-값 쌍 파싱
            lines = slots_text.split('\n')
            for line in lines:
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()
                    if key and value:
                        slots[key] = value
                        
        except Exception as e:
            self.logger.log_error_with_context(e, "IntentClassifier._parse_slots")
        
        return slots
    
    def _calculate_confidence(self, query: str, intent: str) -> float:
        """신뢰도를 계산합니다."""
        # 간단한 키워드 기반 신뢰도 계산
        confidence = 0.5  # 기본값
        
        # 의도별 키워드 매칭
        intent_keywords = {
            "고객정보_조회": ["고객", "정보", "조회", "확인"],
            "금융정보_조회": ["금융", "정보", "조회", "확인"],
            "이체_조회": ["이체", "내역", "조회", "확인"],
            "이체_실행": ["이체", "송금", "보내기", "실행"],
            "계좌_조회": ["계좌", "잔액", "조회", "확인"],
            "자동이체_조회": ["자동이체", "조회", "확인"],
            "자동이체_실행": ["자동이체", "설정", "등록"],
            "투자상품_조회": ["투자", "상품", "조회", "확인"],
            "투자상품_실행": ["투자", "가입", "신청"],
            "대출_조회": ["대출", "조회", "확인"],
            "대출_실행": ["대출", "신청", "상담"]
        }
        
        if intent in intent_keywords:
            keywords = intent_keywords[intent]
            matches = sum(1 for keyword in keywords if keyword in query)
            if matches > 0:
                confidence = min(0.9, 0.5 + (matches * 0.1))
        
        return confidence 