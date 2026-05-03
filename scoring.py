from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Dict, List, Optional


@dataclass
class CustomerScore:
    customer_id: str
    merchant_id: str
    total: float
    category_affinity: float
    state_weight: float
    interaction_score: float
    recency_score: float
    lifetime_score: float
    consent_factor: float
    details: Dict[str, float]
    reasons: List[str]


def parse_iso_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    formats = ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z"]
    for fmt in formats:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return None


def clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def calculate_recency_score(last_visit: Optional[str], reference_date: date) -> float:
    visited = parse_iso_date(last_visit)
    if not visited:
        return 0.2
    days = (reference_date - visited).days
    if days <= 14:
        return 1.0
    if days <= 45:
        return 0.85
    if days <= 90:
        return 0.65
    if days <= 180:
        return 0.40
    return 0.15


def calculate_state_weight(state: Optional[str]) -> float:
    weights = {
        "active": 1.0,
        "lapsed_soft": 0.95,
        "new": 0.70,
        "lapsed_hard": 0.55,
        "churned": 0.25,
    }
    return weights.get((state or "").lower(), 0.50)


def calculate_interaction_score(visits_total: Optional[int]) -> float:
    if not visits_total or visits_total <= 0:
        return 0.1
    return clamp(visits_total / 12.0)


def calculate_lifetime_score(lifetime_value: Optional[float]) -> float:
    if not lifetime_value or lifetime_value <= 0:
        return 0.1
    return clamp(lifetime_value / 12000.0)


def calculate_consent_factor(customer: Dict[str, Any]) -> float:
    preferences = customer.get("preferences", {})
    consent = customer.get("consent", {})
    if not preferences.get("reminder_opt_in", False) or not consent.get("scope"):
        return 0.25
    return 1.0


def compute_customer_score(
    customer: Dict[str, Any],
    merchant: Dict[str, Any],
    category: Optional[Dict[str, Any]] = None,
    reference_date: Optional[date] = None,
) -> CustomerScore:
    reference_date = reference_date or date.today()
    state = customer.get("state")
    visits_total = customer.get("relationship", {}).get("visits_total", 0)
    lifetime_value = customer.get("relationship", {}).get("lifetime_value", 0)

    category_affinity = 1.0 if customer.get("merchant_id") == merchant.get("merchant_id") else 0.0
    state_weight = calculate_state_weight(state)
    interaction_score = calculate_interaction_score(visits_total)
    recency_score = calculate_recency_score(customer.get("relationship", {}).get("last_visit"), reference_date)
    lifetime_score = calculate_lifetime_score(lifetime_value)
    consent_factor = calculate_consent_factor(customer)

    raw_score = (
        22.0 * category_affinity
        + 20.0 * state_weight
        + 18.0 * interaction_score
        + 18.0 * recency_score
        + 12.0 * lifetime_score
    )
    total = clamp(raw_score / 1.0, 0.0, 100.0) * consent_factor
    reasons: List[str] = []
    if state:
        reasons.append(f"State '{state}' carries weight {state_weight:.2f}")
    if visits_total:
        reasons.append(f"{visits_total} visits -> interaction {interaction_score:.2f}")
    if customer.get("relationship", {}).get("last_visit"):
        reasons.append(f"Last visit {customer['relationship']['last_visit']} -> recency {recency_score:.2f}")
    if consent_factor < 1.0:
        reasons.append("Low outreach consent or opt-in missing")

    return CustomerScore(
        customer_id=customer.get("customer_id", ""),
        merchant_id=merchant.get("merchant_id", ""),
        total=round(total, 1),
        category_affinity=round(category_affinity, 2),
        state_weight=round(state_weight, 2),
        interaction_score=round(interaction_score, 2),
        recency_score=round(recency_score, 2),
        lifetime_score=round(lifetime_score, 2),
        consent_factor=round(consent_factor, 2),
        details={
            "category_affinity": round(category_affinity, 2),
            "state_weight": round(state_weight, 2),
            "interaction_score": round(interaction_score, 2),
            "recency_score": round(recency_score, 2),
            "lifetime_score": round(lifetime_score, 2),
            "consent_factor": round(consent_factor, 2),
        },
        reasons=reasons,
    )


def rank_customers_for_merchant(
    merchant: Dict[str, Any],
    customers: List[Dict[str, Any]],
    category: Optional[Dict[str, Any]] = None,
    top_n: int = 5,
    reference_date: Optional[date] = None,
) -> List[CustomerScore]:
    reference_date = reference_date or date.today()
    candidates = [c for c in customers if c.get("merchant_id") == merchant.get("merchant_id")]
    scored = [compute_customer_score(c, merchant, category, reference_date) for c in candidates]
    return sorted(scored, key=lambda cs: cs.total, reverse=True)[:top_n]
