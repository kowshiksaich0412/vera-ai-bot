from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Extra

from app.services.context_store import context_store
from app.services.message_generator import generate_reply

router = APIRouter()


class ReplyPayload(BaseModel):
    merchant_id: str
    customer_id: str
    message: str
    reply_type: Optional[str] = None

    class Config:
        extra = Extra.allow


@router.post("/reply")
def handle_reply(payload: ReplyPayload) -> Dict[str, Any]:
    merchant = context_store.get_merchant(payload.merchant_id)
    customer = context_store.get_customer(payload.customer_id)

    if merchant is None:
        raise HTTPException(status_code=404, detail=f"Merchant not found: {payload.merchant_id}")
    if customer is None:
        raise HTTPException(status_code=404, detail=f"Customer not found: {payload.customer_id}")

    response = generate_reply(merchant=merchant, customer=customer, received_message=payload.message)
    return {
        "status": "ok",
        "merchant_id": payload.merchant_id,
        "customer_id": payload.customer_id,
        "reply": response["message"],
        "next_action": response["next_action"],
        "explain": response["explain"],
    }
