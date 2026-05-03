from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Extra


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


# Models/Schemas
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


class ContextPayload(BaseModel):
    merchant: Optional[Dict[str, Any]] = None
    merchants: Optional[List[Dict[str, Any]]] = None
    customer: Optional[Dict[str, Any]] = None
    customers: Optional[List[Dict[str, Any]]] = None
    trigger: Optional[Dict[str, Any]] = None
    triggers: Optional[List[Dict[str, Any]]] = None

    class Config:
        extra = Extra.allow


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


class ReplyPayload(BaseModel):
    merchant_id: str
    customer_id: str
    message: str
    reply_type: Optional[str] = None

    class Config:
        extra = Extra.allow


# Services
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


class EngagementScore:
    def __init__(self, score: float, category_match: float, recency: float, frequency: float, explain: str) -> None:
        self.score = score
        self.category_match = category_match
        self.recency = recency
        self.frequency = frequency
        self.explain = explain


CATEGORY_KEYWORDS = {
    "dentists": ["cleaning", "whitening", "root_canal", "aligner", "cement", "periodontal", "pediatric"],
    "salons": ["haircut", "hair_spa", "manicure", "pedicure", "bridal", "stylist", "facial"],
    "restaurants": ["pizza", "thali", "delivery", "dosa", "biryani", "cafe", "meal", "order"],
    "gyms": ["membership", "pt", "training", "yoga", "session", "class", "workout"],
    "pharmacies": ["refill", "rx", "medicine", "delivery", "otc", "chronic", "prescription"],
}


def _parse_date(value: str) -> float:
    if not value:
        return 0.0
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z"):
        try:
            return datetime.strptime(value, fmt).timestamp()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(value).timestamp()
    except ValueError:
        return 0.0


def category_match(merchant: Dict[str, Any], customer: Dict[str, Any]) -> float:
    slug = merchant.get("category_slug", "").lower()
    services = [str(s).lower() for s in customer.get("relationship", {}).get("services_received", []) if s]
    keywords = CATEGORY_KEYWORDS.get(slug, [])
    if any(any(word in service for word in keywords) for service in services):
        return 1.0
    if customer.get("merchant_id") == merchant.get("merchant_id"):
        return 1.0
    return 0.65


def recency_score(customer: Dict[str, Any]) -> float:
    last_visit = customer.get("relationship", {}).get("last_visit")
    timestamp = _parse_date(last_visit)
    if timestamp == 0.0:
        return 0.15
    age_days = (datetime.utcnow().timestamp() - timestamp) / 86400.0
    if age_days <= 14:
        return 1.0
    if age_days <= 30:
        return 0.85
    if age_days <= 60:
        return 0.65
    if age_days <= 120:
        return 0.35
    return 0.15


def frequency_score(customer: Dict[str, Any]) -> float:
    visits = customer.get("relationship", {}).get("visits_total")
    if not isinstance(visits, (int, float)) or visits <= 0:
        return 0.1
    return min(1.0, visits / 12.0)


def score_engagement(merchant: Dict[str, Any], customer: Dict[str, Any]) -> EngagementScore:
    cat_match = category_match(merchant, customer)
    recency = recency_score(customer)
    frequency = frequency_score(customer)
    score = round((0.4 * cat_match + 0.3 * recency + 0.3 * frequency), 3)
    explain = (
        f"category_match={cat_match:.2f}, recency={recency:.2f}, frequency={frequency:.2f}"
    )
    return EngagementScore(score=score, category_match=cat_match, recency=recency, frequency=frequency, explain=explain)


def _should_send(score: EngagementScore, trigger: Dict[str, Any], customer: Dict[str, Any]) -> bool:
    urgency = int(trigger.get("urgency", 1)) if trigger.get("urgency") is not None else 1
    state = (customer.get("state") or "").lower()

    if score.score >= 0.75:
        return True
    if urgency >= 4 and score.score >= 0.55:
        return True
    if trigger.get("scope") == "customer" and score.score >= 0.5:
        return True
    if state in {"active", "lapsed_soft"} and score.score >= 0.6:
        return True
    return False


def decide_engagements(merchant: Dict[str, Any], trigger: Dict[str, Any], customers: List[Dict[str, Any]], top_n: int = 3) -> List[Dict[str, Any]]:
    scored = []
    for customer in customers:
        score_obj = score_engagement(merchant, customer)
        if len(scored) < top_n or score_obj.score > scored[-1]["score"]:
            scored.append({"customer": customer, "score_obj": score_obj})
            scored = sorted(scored, key=lambda item: item["score_obj"].score, reverse=True)[:top_n]

    decisions = []
    for item in scored:
        customer = item["customer"]
        score_obj = item["score_obj"]
        decision = "send" if _should_send(score_obj, trigger, customer) else "skip"
        message_payload = compose_message(
            customer=customer,
            merchant=merchant,
            trigger=trigger,
            score=score_obj.score,
            decision=decision,
        )
        decisions.append(
            {
                "customer_id": customer.get("customer_id"),
                "merchant_id": merchant.get("merchant_id"),
                "decision": decision,
                "score": score_obj.score,
                "explain": score_obj.explain,
                "message": message_payload["message"],
                "cta": message_payload["cta"],
                "best_time": message_payload["best_time"],
                "why": message_payload["why"],
            }
        )
    return decisions


def _normalize_name(customer: Dict[str, Any]) -> str:
    name = customer.get("identity", {}).get("name") or "there"
    if "(" in name:
        name = name.split("(")[0].strip()
    return name


def _cta_for_kind(kind: str) -> str:
    if kind in {
        "recall_due",
        "appointment_tomorrow",
        "chronic_refill_due",
        "trial_followup",
        "customer_lapsed_soft",
        "customer_lapsed_hard",
    }:
        return "YES"
    return "YES"


def _best_time_hint(customer: Dict[str, Any], trigger: Dict[str, Any]) -> str:
    preferred = customer.get("preferences", {}).get("preferred_slots") or customer.get("preferences", {}).get("preferred_time")
    if preferred:
        return preferred.replace("_", " ")
    kind = trigger.get("kind", "")
    if "morning" in kind:
        return "tomorrow morning"
    if "evening" in kind or "night" in kind:
        return "this evening"
    if kind in {"recall_due", "appointment_tomorrow", "chronic_refill_due"}:
        return "in the next 24 hours"
    return "soon"


def compose_message(customer: Dict[str, Any], merchant: Dict[str, Any], trigger: Dict[str, Any], score: float, decision: str) -> Dict[str, Any]:
    name = _normalize_name(customer)
    merchant_name = merchant.get("identity", {}).get("name", "your merchant")
    kind = trigger.get("kind", "").lower()
    best_time = _best_time_hint(customer, trigger)
    cta = _cta_for_kind(kind) if decision == "send" else "none"

    if decision == "skip":
        return {"message": "", "cta": "none", "best_time": "n/a", "why": "Decision engine chose not to engage this customer."}

    if kind == "recall_due":
        service_due = trigger.get("payload", {}).get("service_due", "follow-up")
        service_text = service_due.replace("_", " ")
        slot_text = ""
        available = trigger.get("payload", {}).get("available_slots", [])
        if available:
            slot_text = f" Try {available[0].get('label')} if that works."
        message = (
            f"Hey {name}, your {service_text} is due at {merchant_name}. "
            f"We can book it {best_time}.{slot_text} Reply YES to confirm."
        )
        why = "Recall reminder focused on specific service and booking urgency."
    elif kind == "chronic_refill_due":
        medicines = trigger.get("payload", {}).get("molecule_list", [])
        items = ", ".join(medicines[:2]) if medicines else "your refill"
        message = (
            f"Hi {name}, {merchant_name} is ready to refill {items} for you. "
            f"We can deliver {best_time}. Reply YES to proceed."
        )
        why = "Refill outreach uses personalized medication details and delivery timing."
    elif kind == "trial_followup":
        message = (
            f"Hi {name}, happy you tried the session at {merchant_name}. "
            f"If you'd like a follow-up {best_time}, reply YES and I'll book it."
        )
        why = "Trial follow-up encourages next visit with a clear personalized next step."
    else:
        message = (
            f"Hey {name}, {merchant_name} has a special offer today. "
            f"If you want a slot {best_time}, reply YES and I'll save it for you."
        )
        why = "Generic engagement message uses a quick CTA and time window."

    return {"message": message, "cta": cta, "best_time": best_time, "why": why}


def generate_reply(merchant: Dict[str, Any], customer: Dict[str, Any], received_message: str) -> Dict[str, str]:
    text = received_message.lower()
    name = _normalize_name(customer)
    merchant_name = merchant.get("identity", {}).get("name", "your merchant")

    if any(keyword in text for keyword in ["yes", "sure", "book", "confirm", "ok", "okay"]):
        return {
            "message": f"Great {name}! I will confirm the booking with {merchant_name} and send you details shortly.",
            "next_action": "confirm_booking",
            "explain": "The reply indicates customer intent, so we confirm and move to booking.",
        }

    if any(keyword in text for keyword in ["no", "not now", "later", "stop"]):
        return {
            "message": f"No problem, {name}. If you want to revisit this later, just let me know.",
            "next_action": "respect_decline",
            "explain": "The reply looks like a decline, so we pause outreach respectfully.",
        }

    if any(keyword in text for keyword in ["help", "question", "need", "details", "info"]):
        return {
            "message": f"Sure {name}, I can help. What do you want to know about {merchant_name}'s offer or availability?",
            "next_action": "assist_request",
            "explain": "The reply requests help, so we ask a focused follow-up question.",
        }

    return {
        "message": f"Thanks {name}, I can help you find the best slot with {merchant_name}. Would you like me to check availability for you?",
        "next_action": "ask_clarification",
        "explain": "The reply is ambiguous, so we ask a clarifying question to continue the conversation.",
    }


# Global context store
context_store = ContextStore()


# FastAPI App
app = FastAPI(
    title="Vera AI Bot",
    version="1.0",
    description="AI engagement assistant for merchants",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# Routes
@app.get("/")
def root() -> Dict[str, str]:
    return {"message": "Vera AI Bot API", "status": "running"}


@app.get("/v1/healthz")
def healthz() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/v1/metadata")
def metadata() -> Dict[str, Any]:
    return {
        "name": "Vera AI Bot",
        "version": "1.0",
        "description": "AI engagement assistant for merchants",
    }


@app.post("/v1/context")
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


@app.post("/v1/tick")
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


@app.post("/v1/reply")
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
