import json
import os
from typing import Dict, Any, List, Optional
from pathlib import Path

class CustomerService:
    def __init__(self, config_file: str = "config/customers.json"):
        self.config_file = config_file
        self.customers = self._load_customers()
    
    def _load_customers(self) -> Dict[str, Any]:
        """고객 정보 JSON 파일 로드"""
        try:
            config_path = Path(__file__).parent.parent / self.config_file
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data
        except Exception as e:
            print(f"Error loading customers: {str(e)}")
            return {"customers": []}
    
    def get_all_customers(self) -> List[Dict[str, Any]]:
        """모든 고객 정보 조회"""
        return self.customers.get("customers", [])
    
    def get_customer_by_id(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """고객 ID로 고객 정보 조회"""
        customers = self.get_all_customers()
        for customer in customers:
            if customer.get("customer_id") == customer_id:
                return customer
        return None
    
    def get_customer_by_account(self, account_number: str) -> Optional[Dict[str, Any]]:
        """계좌번호로 고객 정보 조회"""
        customers = self.get_all_customers()
        for customer in customers:
            if customer.get("account_number") == account_number:
                return customer
        return None
    
    def get_customer_summary(self) -> List[Dict[str, Any]]:
        """고객 요약 정보 조회 (웹 UI용)"""
        customers = self.get_all_customers()
        summary = []
        for customer in customers:
            summary.append({
                "customer_id": customer.get("customer_id"),
                "name": customer.get("name"),
                "account_number": customer.get("account_number"),
                "account_type": customer.get("account_type"),
                "customer_type": customer.get("customer_type"),
                "balance": customer.get("balance", 0)
            })
        return summary
    
    def update_customer_login(self, customer_id: str):
        """고객 로그인 시간 업데이트"""
        from datetime import datetime
        customers = self.get_all_customers()
        for customer in customers:
            if customer.get("customer_id") == customer_id:
                customer["last_login"] = datetime.now().isoformat() + "Z"
                break
        self.customers["customers"] = customers
        self._save_customers()
    
    def _save_customers(self):
        """고객 정보 저장"""
        try:
            config_path = Path(__file__).parent.parent / self.config_file
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.customers, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving customers: {str(e)}") 