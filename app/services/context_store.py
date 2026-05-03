from __future__ import annotations

from typing import Any, Dict, List, Optional


class ContextStore:
    def __init__(self) -> None:
        self.merchants: Dict[str, Dict[str, Any]] = {}
        self.customers: Dict[str, Dict[str, Any]] = {}
        self.triggers: Dict[str, Dict[str, Any]] = {}
        self.customers_by_merchant: Dict[str, List[str]] = {}

    def add_merchant(self, merchant: Dict[str, Any]) -> None:
        merchant_id = merchant.get("merchant_id")
        if not merchant_id:
            return
        self.merchants[merchant_id] = merchant

    def add_customer(self, customer: Dict[str, Any]) -> None:
        customer_id = customer.get("customer_id")
        merchant_id = customer.get("merchant_id")
        if not customer_id or not merchant_id:
            return
        self.customers[customer_id] = customer
        self.customers_by_merchant.setdefault(merchant_id, [])
        if customer_id not in self.customers_by_merchant[merchant_id]:
            self.customers_by_merchant[merchant_id].append(customer_id)

    def add_trigger(self, trigger: Dict[str, Any]) -> None:
        trigger_id = trigger.get("id")
        if not trigger_id:
            return
        self.triggers[trigger_id] = trigger

    def get_merchant(self, merchant_id: str) -> Optional[Dict[str, Any]]:
        return self.merchants.get(merchant_id)

    def get_customer(self, customer_id: str) -> Optional[Dict[str, Any]]:
        return self.customers.get(customer_id)

    def get_trigger(self, trigger_id: str) -> Optional[Dict[str, Any]]:
        return self.triggers.get(trigger_id)

    def get_customers_for_merchant(self, merchant_id: str) -> List[Dict[str, Any]]:
        customer_ids = self.customers_by_merchant.get(merchant_id, [])
        return [self.customers[cid] for cid in customer_ids if cid in self.customers]


context_store = ContextStore()
