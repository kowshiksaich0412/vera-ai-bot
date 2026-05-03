from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Extra

from app.services.context_store import context_store
from app.services.decision_engine import decide_engagements
from app.services.scoring import EngagementScore

router = APIRouter()


class TickPayload(BaseModel):
    tick_id: str
    merchant_id: str
    trigger_id: str
    customer_id: Optional[str] = None
    event_type: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
    customers: Optional[List[Dict[str, Any]]] = None

    class Config:
        extra = Extra.allow


@router.post("/tick")
def process_tick(payload: TickPayload) -> Dict[str, Any]:
    merchant = context_store.get_merchant(payload.merchant_id)
    trigger = context_store.get_trigger(payload.trigger_id)

    if payload.customers:
        for customer in payload.customers:
            context_store.add_customer(customer)

    if merchant is None:
        raise HTTPException(status_code=404, detail=f"Merchant not found: {payload.merchant_id}")
    if trigger is None:
        raise HTTPException(status_code=404, detail=f"Trigger not found: {payload.trigger_id}")

    candidates: List[Dict[str, Any]] = []
    if payload.customer_id:
        customer = context_store.get_customer(payload.customer_id)
        if customer:
            candidates = [customer]
        else:
            raise HTTPException(status_code=404, detail=f"Customer not found: {payload.customer_id}")
    else:
        candidates = context_store.get_customers_for_merchant(payload.merchant_id)

    if not candidates:
        raise HTTPException(status_code=404, detail="No customer context available for this merchant")

    decisions = decide_engagements(merchant=merchant, trigger=trigger, customers=candidates)
    total_score = sum([decision.get("score", 0) for decision in decisions])

    return {
        "status": "ok",
        "tick_id": payload.tick_id,
        "merchant_id": payload.merchant_id,
        "trigger_id": payload.trigger_id,
        "decisions": decisions,
        "summary": {
            "count": len(decisions),
            "average_score": round(total_score / len(decisions), 2) if decisions else 0,
        },
    }
