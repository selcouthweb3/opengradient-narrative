from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


class PredictionCategory(str, Enum):
    CRYPTO = "crypto"
    SPORTS = "sports"
    POLITICS = "politics"
    TECH = "tech"
    ENTERTAINMENT = "entertainment"
    SCIENCE = "science"
    OTHER = "other"


class VoteType(str, Enum):
    AGREE = "agree"
    DISAGREE = "disagree"


class CreatePredictionRequest(BaseModel):
    title: str = Field(..., min_length=10, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    category: PredictionCategory = PredictionCategory.OTHER
    deadline: str = Field(..., description="ISO 8601 datetime string for market close")
    wallet_address: str = Field(..., description="Creator's wallet address")


class VoteRequest(BaseModel):
    prediction_id: str
    wallet_address: str
    vote: VoteType


class ResolveRequest(BaseModel):
    prediction_id: str
    wallet_address: str  # Must be creator


class AIAnalysis(BaseModel):
    probability: int = Field(..., ge=0, le=100)
    narrative: str
    bull_case: str
    bear_case: str
    payment_hash: str
    explorer_url: str


class Prediction(BaseModel):
    id: str
    title: str
    description: Optional[str]
    category: str
    deadline: str
    creator: str
    created_at: str
    analysis: Optional[AIAnalysis] = None
    votes_agree: List[str] = []   # list of wallet addresses
    votes_disagree: List[str] = []
    status: str = "open"          # open | closed | resolved
    verdict: Optional[str] = None
    verdict_payment_hash: Optional[str] = None
    verdict_explorer_url: Optional[str] = None
