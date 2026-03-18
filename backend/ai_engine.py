"""
AI scoring engine — every prediction gets TEE-verified analysis
settled on-chain with INDIVIDUAL_FULL so the reasoning is provable.
"""

import asyncio
import json
import logging
import re
import os
from dotenv import load_dotenv
import opengradient as og

load_dotenv()

logger = logging.getLogger(__name__)

EXPLORER_BASE = "https://explorer.opengradient.ai"

_llm = None
_approval_done = False


def get_llm():
    global _llm
    if _llm is None:
        private_key = os.getenv("OG_PRIVATE_KEY")
        if not private_key:
            raise ValueError("OG_PRIVATE_KEY not set in .env")
        _llm = og.LLM(private_key=private_key)
    return _llm


def ensure_approval():
    global _approval_done
    if not _approval_done:
        llm = get_llm()
        llm.ensure_opg_approval(opg_amount=10.0)
        _approval_done = True


def _parse_json(raw: str) -> dict:
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)


async def analyze_prediction(title: str, description: str, category: str, deadline: str, wallet: str) -> dict:
    """
    First analysis when a prediction is created.
    Returns probability score + narrative + bull/bear case.
    """
    ensure_approval()
    llm = get_llm()

    system = """You are a verifiable AI prediction market analyst running inside a Trusted Execution Environment on OpenGradient. Your analysis is settled on-chain — it is permanent and cryptographically provable.

Analyze the prediction and respond ONLY with valid JSON:
{
  "probability": 0-100,
  "narrative": "2-3 sentence balanced analysis of this prediction",
  "bull_case": "strongest argument this prediction comes true",
  "bear_case": "strongest argument this prediction does NOT come true"
}

Be sharp, specific, and unbiased. No markdown. No text outside the JSON."""

    user = f"""Prediction: {title}
Category: {category}
Deadline: {deadline}
Additional context: {description or 'None provided'}
Creator wallet: {wallet}

Analyze this prediction and provide your probability score and reasoning."""

    result = await llm.chat(
        model=og.TEE_LLM.CLAUDE_HAIKU_4_5,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ],
        max_tokens=400,
        temperature=0.3,
        x402_settlement_mode=og.x402SettlementMode.INDIVIDUAL_FULL,
    )

    raw = result.chat_output.get("content", "{}")
    parsed = _parse_json(raw)
    payment_hash = result.payment_hash or "pending"

    return {
        "probability": max(0, min(100, int(parsed.get("probability", 50)))),
        "narrative": parsed.get("narrative", "Analysis unavailable."),
        "bull_case": parsed.get("bull_case", ""),
        "bear_case": parsed.get("bear_case", ""),
        "payment_hash": payment_hash,
        "explorer_url": f"{EXPLORER_BASE}/tx/{payment_hash}",
    }


async def resolve_prediction(title: str, description: str, deadline: str, votes_agree: int, votes_disagree: int) -> dict:
    """
    Final verdict when creator resolves a prediction after deadline.
    """
    ensure_approval()
    llm = get_llm()

    total = votes_agree + votes_disagree
    agree_pct = round((votes_agree / total * 100) if total > 0 else 0)

    system = """You are a verifiable AI prediction market judge running inside a TEE on OpenGradient. Your verdict is permanent and on-chain.

Write a final verdict for this prediction market. Respond ONLY with valid JSON:
{
  "verdict": "2-3 sentence final narrative verdict on whether this prediction was likely correct, referencing community sentiment and your analysis",
  "community_lean": "agree|disagree|split",
  "confidence": 0-100
}

No markdown. No text outside JSON."""

    user = f"""Prediction: {title}
Context: {description or 'None'}
Deadline: {deadline}
Community votes — Agree: {votes_agree} ({agree_pct}%) | Disagree: {votes_disagree} ({100 - agree_pct}%)

Deliver your final verdict."""

    result = await llm.chat(
        model=og.TEE_LLM.CLAUDE_HAIKU_4_5,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ],
        max_tokens=300,
        temperature=0.2,
        x402_settlement_mode=og.x402SettlementMode.INDIVIDUAL_FULL,
    )

    raw = result.chat_output.get("content", "{}")
    parsed = _parse_json(raw)
    payment_hash = result.payment_hash or "pending"

    return {
        "verdict": parsed.get("verdict", "Verdict unavailable."),
        "community_lean": parsed.get("community_lean", "split"),
        "confidence": parsed.get("confidence", 50),
        "payment_hash": payment_hash,
        "explorer_url": f"{EXPLORER_BASE}/tx/{payment_hash}",
    }
