from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List


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
