"""
OpenGradient Narrative — Verifiable AI Prediction Market
FastAPI backend with TEE-verified LLM scoring and on-chain receipts.
"""

import asyncio
import logging
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from models import CreatePredictionRequest, VoteRequest, ResolveRequest
from store import create_prediction, get_prediction, get_all_predictions, update_prediction, add_vote
from ai_engine import analyze_prediction, resolve_prediction

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s — %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="OpenGradient Narrative",
    description="Verifiable AI Prediction Market — every analysis is TEE-verified and on-chain.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "product": "OpenGradient Narrative"}


@app.get("/predictions")
def list_predictions():
    preds = get_all_predictions()
    return {"predictions": [p.model_dump() for p in preds]}


@app.get("/predictions/{pred_id}")
def get_one(pred_id: str):
    pred = get_prediction(pred_id)
    if not pred:
        raise HTTPException(status_code=404, detail="Prediction not found")
    return pred.model_dump()


@app.post("/predictions")
async def create(req: CreatePredictionRequest):
    """
    Create a new prediction. The AI immediately analyzes it with
    TEE-verified inference and returns an on-chain receipt.
    """
    if not req.wallet_address.startswith("0x"):
        raise HTTPException(status_code=400, detail="Invalid wallet address")

    # Save to store first
    pred = create_prediction(
        title=req.title,
        description=req.description,
        category=req.category.value,
        deadline=req.deadline,
        wallet_address=req.wallet_address,
    )

    # Run TEE-verified AI analysis
    try:
        analysis = await analyze_prediction(
            title=req.title,
            description=req.description or "",
            category=req.category.value,
            deadline=req.deadline,
            wallet=req.wallet_address,
        )
        from models import AIAnalysis
        pred.analysis = AIAnalysis(**analysis)
        update_prediction(pred)
        logger.info(f"Prediction {pred.id} created — payment_hash: {analysis['payment_hash']}")
    except Exception as e:
        logger.error(f"AI analysis failed for {pred.id}: {e}")
        # Still return the prediction even if AI fails
        pred.analysis = None
        update_prediction(pred)

    return pred.model_dump()


@app.post("/predictions/vote")
def vote(req: VoteRequest):
    """Cast or change a vote on an open prediction."""
    pred = get_prediction(req.prediction_id)
    if not pred:
        raise HTTPException(status_code=404, detail="Prediction not found")
    if pred.status != "open":
        raise HTTPException(status_code=400, detail="Prediction is not open for voting")

    updated = add_vote(req.prediction_id, req.wallet_address, req.vote.value)
    return updated.model_dump()


@app.post("/predictions/resolve")
async def resolve(req: ResolveRequest):
    """
    Creator resolves a prediction after its deadline.
    AI delivers a final on-chain verdict.
    """
    pred = get_prediction(req.prediction_id)
    if not pred:
        raise HTTPException(status_code=404, detail="Prediction not found")
    if pred.creator != req.wallet_address.lower():
        raise HTTPException(status_code=403, detail="Only the creator can resolve this prediction")
    if pred.status == "resolved":
        raise HTTPException(status_code=400, detail="Already resolved")

    # Check deadline
    try:
        deadline_dt = datetime.fromisoformat(pred.deadline.replace("Z", "+00:00"))
        if datetime.now(timezone.utc) < deadline_dt:
            raise HTTPException(status_code=400, detail="Deadline has not passed yet")
    except ValueError:
        pass  # If deadline parsing fails, allow resolve

    # TEE-verified final verdict
    try:
        verdict_data = await resolve_prediction(
            title=pred.title,
            description=pred.description or "",
            deadline=pred.deadline,
            votes_agree=len(pred.votes_agree),
            votes_disagree=len(pred.votes_disagree),
        )
        pred.verdict = verdict_data["verdict"]
        pred.verdict_payment_hash = verdict_data["payment_hash"]
        pred.verdict_explorer_url = verdict_data["explorer_url"]
        pred.status = "resolved"
        update_prediction(pred)
        logger.info(f"Prediction {pred.id} resolved — verdict hash: {verdict_data['payment_hash']}")
    except Exception as e:
        logger.error(f"Resolve failed for {pred.id}: {e}")
        raise HTTPException(status_code=500, detail=f"Verdict engine error: {str(e)}")

    return pred.model_dump()
