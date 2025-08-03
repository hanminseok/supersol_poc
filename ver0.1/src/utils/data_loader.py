import json
import os
from typing import Dict, Any, List
from ..Config import config
from ..logger import get_logger


class DataLoader:
    """데이터 로더 클래스"""
    
    def __init__(self):
        """데이터 로더를 초기화합니다."""
        self.data_dir = config.DATA_DIR
        self.logger = get_logger("DataLoader")
        self._cached_data = {}
    
    def load_json_data(self, filename: str) -> Dict[str, Any]:
        """JSON 데이터 파일을 로드합니다."""
        try:
            # 캐시 확인
            if filename in self._cached_data:
                return self._cached_data[filename]
            
            file_path = os.path.join(self.data_dir, filename)
            
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"데이터 파일을 찾을 수 없습니다: {file_path}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 캐시에 저장
            self._cached_data[filename] = data
            
            self.logger.debug(f"데이터 파일 로드 완료: {filename}")
            return data
            
        except Exception as e:
            self.logger.log_error_with_context(e, f"DataLoader.load_json_data({filename})")
            return {}
    
    def get_customer_info(self, customer_id: str) -> Dict[str, Any]:
        """고객 정보를 가져옵니다."""
        try:
            data = self.load_json_data("customer_info.json")
            
            # 고객 ID로 검색
            for customer in data.get("customers", []):
                if customer.get("customer_id") == customer_id:
                    return customer
            
            return {}
            
        except Exception as e:
            self.logger.log_error_with_context(e, f"DataLoader.get_customer_info({customer_id})")
            return {}
    
    def get_financial_info(self, customer_id: str) -> Dict[str, Any]:
        """금융 정보를 가져옵니다."""
        try:
            data = self.load_json_data("financial_info.json")
            
            # 고객 ID로 검색
            for financial in data.get("financial_info", []):
                if financial.get("customer_id") == customer_id:
                    return financial
            
            return {}
            
        except Exception as e:
            self.logger.log_error_with_context(e, f"DataLoader.get_financial_info({customer_id})")
            return {}
    
    def get_transfer_history(self, account_number: str, start_date: str = None, end_date: str = None) -> List[Dict[str, Any]]:
        """이체 내역을 가져옵니다."""
        try:
            data = self.load_json_data("transfer_history.json")
            
            transfers = []
            for transfer in data.get("transfers", []):
                if transfer.get("account_number") == account_number:
                    # 날짜 필터링 (간단한 구현)
                    if start_date and end_date:
                        transfer_date = transfer.get("date", "")
                        if start_date <= transfer_date <= end_date:
                            transfers.append(transfer)
                    else:
                        transfers.append(transfer)
            
            return transfers
            
        except Exception as e:
            self.logger.log_error_with_context(e, f"DataLoader.get_transfer_history({account_number})")
            return []
    
    def get_account_info(self, account_number: str) -> Dict[str, Any]:
        """계좌 정보를 가져옵니다."""
        try:
            data = self.load_json_data("account_info.json")
            
            # 계좌번호로 검색
            for account in data.get("accounts", []):
                if account.get("account_number") == account_number:
                    return account
            
            return {}
            
        except Exception as e:
            self.logger.log_error_with_context(e, f"DataLoader.get_account_info({account_number})")
            return {}
    
    def get_auto_transfer_info(self, account_number: str) -> List[Dict[str, Any]]:
        """자동이체 정보를 가져옵니다."""
        try:
            data = self.load_json_data("auto_transfer.json")
            
            auto_transfers = []
            for auto_transfer in data.get("auto_transfers", []):
                if auto_transfer.get("from_account") == account_number:
                    auto_transfers.append(auto_transfer)
            
            return auto_transfers
            
        except Exception as e:
            self.logger.log_error_with_context(e, f"DataLoader.get_auto_transfer_info({account_number})")
            return []
    
    def get_investment_products(self, product_type: str = None, risk_level: str = None) -> List[Dict[str, Any]]:
        """투자상품 목록을 가져옵니다."""
        try:
            data = self.load_json_data("investment_products.json")
            
            products = []
            for product in data.get("products", []):
                # 필터링
                if product_type and product.get("type") != product_type:
                    continue
                if risk_level and product.get("risk_level") != risk_level:
                    continue
                products.append(product)
            
            return products
            
        except Exception as e:
            self.logger.log_error_with_context(e, f"DataLoader.get_investment_products")
            return []
    
    def get_loan_info(self, customer_id: str) -> List[Dict[str, Any]]:
        """대출 정보를 가져옵니다."""
        try:
            data = self.load_json_data("loan_info.json")
            
            loans = []
            for loan in data.get("loans", []):
                if loan.get("customer_id") == customer_id:
                    loans.append(loan)
            
            return loans
            
        except Exception as e:
            self.logger.log_error_with_context(e, f"DataLoader.get_loan_info({customer_id})")
            return []
    
    def clear_cache(self) -> None:
        """데이터 캐시를 클리어합니다."""
        self._cached_data.clear()
        self.logger.debug("데이터 캐시 클리어 완료") 