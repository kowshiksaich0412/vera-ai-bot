from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Extra


class MerchantContext(BaseModel):
    merchant_id: str
    category_slug: Optional[str] = None
    identity: Optional[Dict[str, Any]] = None
    subscription: Optional[Dict[str, Any]] = None
    performance: Optional[Dict[str, Any]] = None
    offers: Optional[List[Dict[str, Any]]] = None

    class Config:
        extra = Extra.allow


class CustomerContext(BaseModel):
    customer_id: str
    merchant_id: str
    identity: Optional[Dict[str, Any]] = None
    relationship: Optional[Dict[str, Any]] = None
    state: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None
    consent: Optional[Dict[str, Any]] = None

    class Config:
        extra = Extra.allow


class TriggerContext(BaseModel):
    id: str
    scope: str
    kind: str
    source: Optional[str] = None
    merchant_id: str
    customer_id: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
    urgency: Optional[int] = None
    suppression_key: Optional[str] = None
    expires_at: Optional[str] = None

    class Config:
        extra = Extra.allow
