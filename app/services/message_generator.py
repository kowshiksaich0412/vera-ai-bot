from __future__ import annotations

from typing import Any, Dict


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
