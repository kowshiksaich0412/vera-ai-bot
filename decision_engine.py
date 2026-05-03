from __future__ import annotations

from datetime import date
from typing import Any, Dict, Optional


def map_preferred_slot(slot: Optional[str]) -> str:
    if not slot:
        return "soon"
    slot_map = {
        "weekday_evening": "weekday evening",
        "weekday_morning": "weekday morning",
        "weekday_afternoon": "weekday afternoon",
        "fri_sat_night": "Friday/Saturday night",
        "saturday_morning": "Saturday morning",
        "saturday_afternoon": "Saturday afternoon",
        "sunday_brunch": "Sunday brunch",
        "morning_6am": "early morning",
        "evening": "evening",
        "morning": "morning",
        "weekday_lunch": "weekday lunch",
    }
    return slot_map.get(slot, slot.replace("_", " ") if slot else "soon")


def choose_send_window(customer: Dict[str, Any], trigger: Dict[str, Any]) -> str:
    preferences = customer.get("preferences", {})
    preferred_slots = preferences.get("preferred_slots") or preferences.get("preferred_time")
    if preferred_slots:
        return map_preferred_slot(preferred_slots)

    kind = trigger.get("kind", "").lower()
    if "morning" in kind:
        return "tomorrow morning"
    if "evening" in kind or "night" in kind:
        return "this evening"
    if kind in {"recall_due", "appointment_tomorrow", "chronic_refill_due"}:
        return "in the next 24 hours"
    return "soon"


def should_send_message(
    customer: Dict[str, Any],
    merchant: Dict[str, Any],
    trigger: Dict[str, Any],
    score: float,
) -> Dict[str, Any]:
    state = (customer.get("state") or "").lower()
    urgency = trigger.get("urgency", 1)
    consent_scope = customer.get("consent", {}).get("scope", [])
    reminder_opt_in = customer.get("preferences", {}).get("reminder_opt_in", False)

    reasons = []
    send = False

    if score < 35:
        reasons.append("Score too low for customer outreach")
    elif not reminder_opt_in:
        reasons.append("Customer has not opted into reminders")
    elif "promotional_offers" not in consent_scope and trigger.get("scope") == "merchant":
        reasons.append("Customer consent does not cover promotional outreach")
    else:
        if trigger.get("scope") == "customer":
            if urgency >= 2 and state in {"active", "lapsed_soft", "new", "lapsed_hard"}:
                send = True
                reasons.append("Customer-scoped trigger with sufficient urgency and state")
            else:
                reasons.append("Customer trigger does not require immediate outreach")
        else:
            if urgency >= 4 and score >= 45:
                send = True
                reasons.append("High-urgency merchant trigger with strong customer fit")
            elif score >= 60:
                send = True
                reasons.append("Very strong customer fit for merchant-level promotion")
            elif state in {"lapsed_soft", "lapsed_hard"} and urgency >= 3:
                send = True
                reasons.append("Winback candidate for an urgent merchant trigger")
            else:
                reasons.append("Merchant-scoped trigger does not justify outreach to this customer")

    if send:
        window = choose_send_window(customer, trigger)
        return {
            "decision": "send",
            "best_time": window,
            "decision_reason": " | ".join(reasons),
        }

    return {
        "decision": "skip",
        "best_time": "n/a",
        "decision_reason": " | ".join(reasons),
    }
