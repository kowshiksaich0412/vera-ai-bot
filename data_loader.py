from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fp:
        return json.load(fp)


def load_categories(dataset_root: Path) -> List[Dict[str, Any]]:
    categories_dir = dataset_root / "categories"
    if not categories_dir.exists():
        raise FileNotFoundError(f"Categories folder not found: {categories_dir}")

    categories = []
    for path in sorted(categories_dir.glob("*.json")):
        categories.append(load_json(path))
    return categories


def load_merchants(dataset_root: Path) -> List[Dict[str, Any]]:
    merchants_dir = dataset_root / "merchants"
    if merchants_dir.exists():
        merchants = [load_json(path) for path in sorted(merchants_dir.glob("*.json"))]
    else:
        seed_file = dataset_root / "merchants_seed.json"
        if not seed_file.exists():
            raise FileNotFoundError(f"Merchant data not found in {dataset_root}")
        merchants = load_json(seed_file).get("merchants", [])

    return merchants


def load_customers(dataset_root: Path) -> List[Dict[str, Any]]:
    customers_dir = dataset_root / "customers"
    if customers_dir.exists():
        customers = [load_json(path) for path in sorted(customers_dir.glob("*.json"))]
    else:
        seed_file = dataset_root / "customers_seed.json"
        if not seed_file.exists():
            raise FileNotFoundError(f"Customer data not found in {dataset_root}")
        customers = load_json(seed_file).get("customers", [])

    return customers


def load_triggers(dataset_root: Path) -> List[Dict[str, Any]]:
    triggers_dir = dataset_root / "triggers"
    if triggers_dir.exists():
        triggers = [load_json(path) for path in sorted(triggers_dir.glob("*.json"))]
    else:
        seed_file = dataset_root / "triggers_seed.json"
        if not seed_file.exists():
            raise FileNotFoundError(f"Trigger data not found in {dataset_root}")
        triggers = load_json(seed_file).get("triggers", [])

    return triggers


def index_by_id(objects: List[Dict[str, Any]], key: str = "id") -> Dict[str, Dict[str, Any]]:
    return {obj[key]: obj for obj in objects if key in obj}


def find_category_for_merchant(merchant: Dict[str, Any], categories: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    slug = merchant.get("category_slug")
    if not slug:
        return None
    for category in categories:
        if category.get("slug") == slug:
            return category
    return None
