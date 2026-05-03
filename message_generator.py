from __future__ import annotations

from typing import Any, Dict, List, Optional


def safe_name(customer: Dict[str, Any]) -> str:
    name = customer.get("identity", {}).get("name") or "there"
    if "(" in name:
        name = name.split("(")[0].strip()
    return name


def choose_offer_text(
    merchant: Dict[str, Any],
    category: Optional[Dict[str, Any]],
    customer: Dict[str, Any],
    trigger: Dict[str, Any],
) -> str:
    active_offers = [offer for offer in merchant.get("offers", []) if offer.get("status") == "active"]
    if active_offers:
        return active_offers[0].get("title", "special offer")

    if category and category.get("offer_catalog"):
        return category["offer_catalog"][0].get("title", "special offer")

    return "a great deal"


def build_cta(trigger: Dict[str, Any], decision: str) -> str:
    if decision == "skip":
        return "none"
    kind = trigger.get("kind", "").lower()
    if kind in {"recall_due", "appointment_tomorrow", "chronic_refill_due", "trial_followup", "customer_lapsed_soft", "customer_lapsed_hard"}:
        return "YES"
    return "YES"


def build_localized_phrase(category: Optional[Dict[str, Any]]) -> str:
    if not category:
        return ""
    code_mix = category.get("voice", {}).get("code_mix", "")
    if "hindi" in code_mix:
        return "Aapka kya kehna hai?"
    return "Let me know."


def generate_message(
    customer: Dict[str, Any],
    merchant: Dict[str, Any],
    category: Optional[Dict[str, Any]],
    trigger: Dict[str, Any],
    decision_meta: Dict[str, Any],
) -> Dict[str, Any]:
    name = safe_name(customer)
    merchant_name = merchant.get("identity", {}).get("name", "your merchant")
    offer_text = choose_offer_text(merchant, category, customer, trigger)
    best_time = decision_meta.get("best_time", "soon")
    kind = trigger.get("kind", "").lower()
    payload = trigger.get("payload", {})
    reasons: List[str] = []

    if decision_meta["decision"] == "skip":
        return {
            "message": "",
            "cta": "none",
            "why_message": "No message generated because decision engine chose to skip outreach.",
        }

    if kind == "recall_due":
        service_due = payload.get("service_due", "follow-up")
        slot = ""
        if payload.get("available_slots"):
            first_slot = payload["available_slots"][0].get("label")
            slot = f" Try {first_slot}." if first_slot else ""
        message = (
            f"Hi {name}, your {service_due.replace('_', ' ')} is coming up at {merchant_name}. "
            f"We have a ₹299 reminder ready and can book a {best_time} slot for you.{slot} "
            f"Reply YES to confirm."
        )
        reasons.append("Recall reminder anchored to known service and slot availability.")
    elif kind == "chronic_refill_due":
        molecules = payload.get("molecule_list", [])
        items = ", ".join(molecules[:2]) if molecules else "your medication"
        message = (
            f"Hi {name}, your refill for {items} is due soon at {merchant_name}. "
            f"We can arrange home delivery {best_time}. Reply YES and I will lock it in."
        )
        reasons.append("Chronic refill message uses customer-specific medicine reminder.")
    elif kind in {"customer_lapsed_soft", "customer_lapsed_hard", "winback_eligible", "perf_dip", "seasonal_perf_dip"}:
        service = "visit" if category is None else category.get("display_name", "service")
        message = (
            f"Hi {name}, {merchant_name} has a special {offer_text} this week for returning customers. "
            f"If you want a {best_time} slot, reply YES and I will hold it."
        )
        reasons.append("Winback copy emphasizes returning customer incentive and timing.")
    elif kind == "trial_followup":
        message = (
            f"Hi {name}, great to see you try the session at {merchant_name}. "
            f"If you'd like a follow-up at {best_time}, reply YES and I'll book it."
        )
        reasons.append("Trial follow-up phrasing invites the next appointment.")
    else:
        message = (
            f"Hi {name}, {merchant_name} has a new offer: {offer_text}. "
            f"If you'd like this {best_time}, reply YES and I'll reserve it for you. "
            f"{build_localized_phrase(category)}"
        )
        reasons.append("Generic customer outreach uses a strong offer and clear CTA.")

    return {
        "message": message,
        "cta": build_cta(trigger, decision_meta["decision"]),
        "why_message": " ".join(reasons),
    }
