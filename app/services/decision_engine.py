from typing import Any, Dict, List

from app.services.message_generator import compose_message
from app.services.scoring import EngagementScore, score_engagement


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
