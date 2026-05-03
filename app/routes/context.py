from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Extra

from app.services.context_store import context_store

router = APIRouter()


class ContextPayload(BaseModel):
    merchant: Optional[Dict[str, Any]] = None
    merchants: Optional[List[Dict[str, Any]]] = None
    customer: Optional[Dict[str, Any]] = None
    customers: Optional[List[Dict[str, Any]]] = None
    trigger: Optional[Dict[str, Any]] = None
    triggers: Optional[List[Dict[str, Any]]] = None

    class Config:
        extra = Extra.allow


@router.post("/context")
def ingest_context(payload: ContextPayload) -> Dict[str, Any]:
    stored = {"merchants": 0, "customers": 0, "triggers": 0}

    if payload.merchant:
        context_store.add_merchant(payload.merchant)
        stored["merchants"] += 1
    if payload.merchants:
        for merchant in payload.merchants:
            context_store.add_merchant(merchant)
        stored["merchants"] += len(payload.merchants)

    if payload.customer:
        context_store.add_customer(payload.customer)
        stored["customers"] += 1
    if payload.customers:
        for customer in payload.customers:
            context_store.add_customer(customer)
        stored["customers"] += len(payload.customers)

    if payload.trigger:
        context_store.add_trigger(payload.trigger)
        stored["triggers"] += 1
    if payload.triggers:
        for trigger in payload.triggers:
            context_store.add_trigger(trigger)
        stored["triggers"] += len(payload.triggers)

    if stored["merchants"] + stored["customers"] + stored["triggers"] == 0:
        raise HTTPException(status_code=400, detail="No valid context objects provided")

    return {
        "status": "ok",
        "stored": stored,
        "message": "Context stored successfully",
    }
