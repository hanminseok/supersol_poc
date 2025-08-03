from typing import Dict, Any, Optional

class ResponseGenerator:
    """응답 생성 전용 클래스 - chat_service.py의 긴 함수를 분리"""
    
    @staticmethod
    def generate_response(tool_name: str, tool_output: Dict[str, Any], customer_info: Optional[Dict[str, Any]] = None, context: Optional[Dict[str, Any]] = None) -> str:
        """도구 결과에 따른 응답 생성"""
        customer_name = customer_info.get("name", "고객") if customer_info else "고객"
        current_state = context.get("current_state", {}) if context else {}
        selected_account = current_state.get("selected_account")
        
        # 응답 생성기 매핑
        response_generators = {
            "direct_response": ResponseGenerator._generate_direct_response,
            "account_balance": ResponseGenerator._generate_account_balance_response,
            "transfer_money": ResponseGenerator._generate_transfer_response,
            "loan_info": ResponseGenerator._generate_loan_response,
            "investment_info": ResponseGenerator._generate_investment_response,
            "exchange_rate": ResponseGenerator._generate_exchange_response,
            "auto_transfer": ResponseGenerator._generate_auto_transfer_response,
            "service_condition": ResponseGenerator._generate_service_condition_response,
        }
        
        # 해당 도구의 응답 생성기 호출
        generator = response_generators.get(tool_name)
        if generator:
            return generator(tool_output, customer_name, selected_account)
        else:
            return ResponseGenerator._generate_default_response(tool_output, customer_name)
    
    @staticmethod
    def _generate_direct_response(tool_output: Dict[str, Any], customer_name: str, selected_account: Optional[str] = None) -> str:
        """직접 응답 생성"""
        if isinstance(tool_output, dict):
            response = tool_output.get("response", "")
        else:
            response = str(tool_output)
        
        return response if response else "죄송합니다. 답변을 생성하는 중 오류가 발생했습니다."
    
    @staticmethod
    def _generate_account_balance_response(tool_output: Dict[str, Any], customer_name: str, selected_account: Optional[str] = None) -> str:
        """계좌 잔액 응답 생성"""
        balance = tool_output.get("balance", "알 수 없음")
        account_number = tool_output.get("account_number", selected_account or "현재 계좌")
        
        if customer_name != "고객":
            return f"{customer_name}님, {account_number}의 현재 잔액은 {balance}입니다."
        else:
            return f"{account_number}의 현재 잔액은 {balance}입니다."
    
    @staticmethod
    def _generate_transfer_response(tool_output: Dict[str, Any], customer_name: str, selected_account: Optional[str] = None) -> str:
        """송금 응답 생성"""
        status = tool_output.get("status", "실패")
        if status == "success":
            amount = tool_output.get("amount", "0")
            recipient = tool_output.get("recipient", "")
            if customer_name != "고객":
                return f"{customer_name}님, {recipient}에게 {amount} 송금이 완료되었습니다."
            else:
                return f"{recipient}에게 {amount} 송금이 완료되었습니다."
        else:
            return "송금 처리 중 오류가 발생했습니다."
    
    @staticmethod
    def _generate_loan_response(tool_output: Dict[str, Any], customer_name: str, selected_account: Optional[str] = None) -> str:
        """대출 정보 응답 생성"""
        available_amount = tool_output.get("available_loan_amount", "알 수 없음")
        interest_rate = tool_output.get("interest_rate", "알 수 없음")
        
        if customer_name != "고객":
            return f"{customer_name}님, 대출 가능 금액은 {available_amount}이며, 현재 이자율은 {interest_rate}입니다."
        else:
            return f"대출 가능 금액은 {available_amount}이며, 현재 이자율은 {interest_rate}입니다."
    
    @staticmethod
    def _generate_investment_response(tool_output: Dict[str, Any], customer_name: str, selected_account: Optional[str] = None) -> str:
        """투자 정보 응답 생성"""
        products = tool_output.get("products", [])
        rates = tool_output.get("current_rates", {})
        
        if customer_name != "고객":
            return f"{customer_name}님, 투자 가능한 상품: {', '.join(products)}. 현재 금리: {rates}"
        else:
            return f"투자 가능한 상품: {', '.join(products)}. 현재 금리: {rates}"
    
    @staticmethod
    def _generate_exchange_response(tool_output: Dict[str, Any], customer_name: str, selected_account: Optional[str] = None) -> str:
        """환율 정보 응답 생성"""
        exchange_rate = tool_output.get("exchange_rate", "알 수 없음")
        converted_amount = tool_output.get("converted_amount", "알 수 없음")
        currency = tool_output.get("currency", "")
        
        if customer_name != "고객":
            return f"{customer_name}님, {currency} 환율은 {exchange_rate}이며, 환전 금액은 {converted_amount}입니다."
        else:
            return f"{currency} 환율은 {exchange_rate}이며, 환전 금액은 {converted_amount}입니다."
    
    @staticmethod
    def _generate_auto_transfer_response(tool_output: Dict[str, Any], customer_name: str, selected_account: Optional[str] = None) -> str:
        """자동이체 응답 생성"""
        status = tool_output.get("status", "실패")
        if status == "success":
            amount = tool_output.get("amount", "0")
            schedule = tool_output.get("schedule", "")
            recipient = tool_output.get("recipient", "")
            
            if customer_name != "고객":
                return f"{customer_name}님, {recipient}에게 {amount} {schedule} 자동이체가 등록되었습니다."
            else:
                return f"{recipient}에게 {amount} {schedule} 자동이체가 등록되었습니다."
        else:
            return "자동이체 등록 중 오류가 발생했습니다."
    
    @staticmethod
    def _generate_service_condition_response(tool_output: Dict[str, Any], customer_name: str, selected_account: Optional[str] = None) -> str:
        """서비스 조건 응답 생성"""
        conditions = tool_output.get("conditions", "서비스 이용 조건을 확인해주세요.")
        requirements = tool_output.get("requirements", [])
        fees = tool_output.get("fees", "")
        
        if customer_name != "고객":
            response = f"{customer_name}님, {conditions}"
        else:
            response = f"{conditions}"
        
        if requirements:
            response += f" 필요 서류: {', '.join(requirements)}"
        if fees:
            response += f" 수수료: {fees}"
        
        return response
    
    @staticmethod
    def _generate_default_response(tool_output: Dict[str, Any], customer_name: str) -> str:
        """기본 응답 생성"""
        if isinstance(tool_output, dict):
            response = tool_output.get("response", str(tool_output))
        else:
            response = str(tool_output)
        
        if customer_name != "고객":
            return f"{customer_name}님, {response}"
        else:
            return response 