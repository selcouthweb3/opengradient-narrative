"""
Simple JSON file store for predictions.
No database needed — just a flat file that persists predictions.
"""

import json
import os
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from models import Prediction

STORE_PATH = os.path.join(os.path.dirname(__file__), "predictions.json")


def _load() -> dict:
    if not os.path.exists(STORE_PATH):
        return {"predictions": {}}
    with open(STORE_PATH, "r") as f:
        return json.load(f)


def _save(data: dict):
    with open(STORE_PATH, "w") as f:
        json.dump(data, f, indent=2)


def create_prediction(
    title: str,
    description: Optional[str],
    category: str,
    deadline: str,
    wallet_address: str,
) -> Prediction:
    data = _load()
    pred_id = str(uuid.uuid4())[:8]
    pred = Prediction(
        id=pred_id,
        title=title,
        description=description,
        category=category,
        deadline=deadline,
        creator=wallet_address.lower(),
        created_at=datetime.now(timezone.utc).isoformat(),
        status="open",
    )
    data["predictions"][pred_id] = pred.model_dump()
    _save(data)
    return pred


def get_prediction(pred_id: str) -> Optional[Prediction]:
    data = _load()
    p = data["predictions"].get(pred_id)
    if not p:
        return None
    return Prediction(**p)


def get_all_predictions() -> List[Prediction]:
    data = _load()
    preds = [Prediction(**p) for p in data["predictions"].values()]
    return sorted(preds, key=lambda x: x.created_at, reverse=True)


def update_prediction(pred: Prediction):
    data = _load()
    data["predictions"][pred.id] = pred.model_dump()
    _save(data)


def add_vote(pred_id: str, wallet_address: str, vote: str) -> Optional[Prediction]:
    data = _load()
    p = data["predictions"].get(pred_id)
    if not p:
        return None

    wallet = wallet_address.lower()

    # Remove from both lists first (change vote)
    p["votes_agree"] = [w for w in p["votes_agree"] if w != wallet]
    p["votes_disagree"] = [w for w in p["votes_disagree"] if w != wallet]

    if vote == "agree":
        p["votes_agree"].append(wallet)
    else:
        p["votes_disagree"].append(wallet)

    data["predictions"][pred_id] = p
    _save(data)
    return Prediction(**p)
