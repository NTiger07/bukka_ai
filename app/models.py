from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field


# ── Shared ────────────────────────────────────────────────────────────────────

class Persona(BaseModel):
    name: str
    age: int | None = None
    city: str | None = None
    region: Literal["yoruba", "igbo", "hausa", "edo", "general"] | None = None
    tone: Literal["expressive", "blunt", "formal", "casual", "sarcastic"] = "casual"
    food_preferences: list[str] = Field(default_factory=list)
    avg_star_rating: float = Field(default=3.5, ge=1.0, le=5.0)
    bio: str = ""  # empty = cold-start user


# ── Task A – Review Generation ────────────────────────────────────────────────

class BusinessAttributes(BaseModel):
    price_range: Literal["$", "$$", "$$$", "$$$$"] | None = None
    outdoor_seating: bool | None = None
    wifi: bool | None = None
    reservations: bool | None = None


class Business(BaseModel):
    name: str
    category: str
    city: str | None = None
    state: str | None = None
    stars: float | None = Field(default=None, ge=1.0, le=5.0)
    attributes: BusinessAttributes | None = None


class ReviewRequest(BaseModel):
    persona: Persona
    business: Business
    context: str | None = None


class ReviewResponse(BaseModel):
    review: str
    stars: int = Field(ge=1, le=5)
    word_count: int
    sentiment: Literal["positive", "negative", "mixed"]
    generation_time_ms: int


# ── Task B – Recommendations ──────────────────────────────────────────────────

class HistoryItem(BaseModel):
    """A single past visit the user made — source-domain signal for cross-domain inference."""
    business_name: str
    category: str                          # e.g. "Restaurants, Chinese"
    stars: int = Field(ge=1, le=5)         # what the user actually rated it
    notes: str | None = None               # optional: "loved the bold spice", "service was cold"


class RecommendFilters(BaseModel):
    city: str | None = None
    state: str | None = None
    categories: list[str] = Field(default_factory=list)
    min_stars: float = Field(default=3.0, ge=1.0, le=5.0)
    max_results: int = Field(default=5, ge=1, le=50)
    # Cross-domain: set this to recommend in a different domain than the user's history
    target_domain: str | None = None       # e.g. "Spas", "Nightlife", "Shopping", "Arts & Entertainment"


class RecommendRequest(BaseModel):
    persona: Persona
    filters: RecommendFilters = Field(default_factory=RecommendFilters)
    history: list[HistoryItem] = Field(default_factory=list)
    use_agent_pipeline: bool = Field(
        default=False,
        description="True = three-agent pipeline (slower, richer reasoning). False = single-agent (faster).",
    )


class RecommendedBusiness(BaseModel):
    rank: int
    business_id: str
    name: str
    category: str
    city: str
    stars: float
    review_count: int
    reason: str
    match_score: float = Field(ge=0.0, le=1.0)


class RecommendResponse(BaseModel):
    recommendations: list[RecommendedBusiness]
    persona_summary: str
    preference_profile: str | None = None      # Agent 1 output — what the user values
    cross_domain_inference: str | None = None  # Agent 2 output — how signals translate
    generation_time_ms: int
