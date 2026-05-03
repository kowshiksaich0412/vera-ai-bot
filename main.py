from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from data_loader import (
    index_by_id,
    load_categories,
    load_customers,
    load_merchants,
    load_triggers,
    find_category_for_merchant,
)
from decision_engine import should_send_message
from message_generator import generate_message
from scoring import compute_customer_score, rank_customers_for_merchant


def make_decision_payload(
    customer: Dict[str, Any],
    merchant: Dict[str, Any],
    category: Optional[Dict[str, Any]],
    trigger: Dict[str, Any],
    score_obj,
) -> Dict[str, Any]:
    decision_meta = should_send_message(customer, merchant, trigger, score_obj.total)
    generated = generate_message(customer, merchant, category, trigger, decision_meta)
    return {
        "customer_id": customer.get("customer_id"),
        "merchant_id": merchant.get("merchant_id"),
        "decision": decision_meta["decision"],
        "message": generated["message"],
        "score": score_obj.total,
        "cta": generated["cta"],
        "best_time": decision_meta["best_time"],
        "why_selected": decision_meta["decision_reason"],
        "why_message": generated["why_message"],
    }


def build_engagements(
    merchant: Dict[str, Any],
    trigger: Dict[str, Any],
    all_customers: List[Dict[str, Any]],
    category: Optional[Dict[str, Any]],
    top_n: int = 3,
) -> List[Dict[str, Any]]:
    if trigger.get("scope") == "customer" and trigger.get("customer_id"):
        customer_id = trigger["customer_id"]
        customer = next((c for c in all_customers if c.get("customer_id") == customer_id), None)
        if not customer:
            return []
        score_obj = compute_customer_score(customer, merchant, category)
        return [make_decision_payload(customer, merchant, category, trigger, score_obj)]

    ranked = rank_customers_for_merchant(merchant, all_customers, category, top_n=top_n)
    results: List[Dict[str, Any]] = []
    for score_obj in ranked:
        customer = next((c for c in all_customers if c.get("customer_id") == score_obj.customer_id), None)
        if customer is None:
            continue
        results.append(make_decision_payload(customer, merchant, category, trigger, score_obj))
    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Magicpin Vera engagement engine")
    parser.add_argument("--dataset", type=Path, default=Path(__file__).resolve().parent / "dataset", help="Path to the dataset folder")
    parser.add_argument("--merchant-id", type=str, required=True, help="Merchant ID to evaluate")
    parser.add_argument("--trigger-id", type=str, required=True, help="Trigger ID to process")
    parser.add_argument("--top-n", type=int, default=3, help="Top N customers to score")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    categories = load_categories(args.dataset)
    merchants = load_merchants(args.dataset)
    customers = load_customers(args.dataset)
    triggers = load_triggers(args.dataset)

    merchant_index = index_by_id(merchants, "merchant_id")
    trigger_index = index_by_id(triggers, "id")

    merchant = merchant_index.get(args.merchant_id)
    trigger = trigger_index.get(args.trigger_id)
    if merchant is None:
        raise ValueError(f"Merchant not found: {args.merchant_id}")
    if trigger is None:
        raise ValueError(f"Trigger not found: {args.trigger_id}")

    category = find_category_for_merchant(merchant, categories)
    engagements = build_engagements(merchant, trigger, customers, category, top_n=args.top_n)

    output = {
        "merchant_id": merchant.get("merchant_id"),
        "trigger_id": trigger.get("id"),
        "results": engagements,
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
