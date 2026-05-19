"""
Task B — Recommendation Agent.

Flow:
1. Filter the Yelp business dataset by city / state / categories / min_stars.
2. Rank by quality score (stars × log review_count) and take top 20 candidates.
3. Send candidates + persona to Claude for personalised ranking + explanations.
4. Return the top N results as a RecommendResponse.
"""

from __future__ import annotations

import json
import logging
import os
import time

import anthropic

from app.data.yelp_loader import get_loader
from app.models import Persona, RecommendFilters, RecommendResponse, RecommendedBusiness
from app.prompts import recommend_prompts

logger = logging.getLogger(__name__)

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return _client


def get_recommendations(
    persona: Persona,
    filters: RecommendFilters,
) -> RecommendResponse:
    loader = get_loader()

    candidates = loader.search_businesses(
        city=filters.city,
        state=filters.state,
        categories=filters.categories if filters.categories else None,
        min_stars=filters.min_stars,
        limit=20,
    )

    if not candidates:
        # Widen search — drop category filter if it returned nothing
        logger.warning("No candidates found with category filter; widening search.")
        candidates = loader.search_businesses(
            city=filters.city,
            state=filters.state,
            min_stars=filters.min_stars,
            limit=20,
        )

    if not candidates:
        return RecommendResponse(
            recommendations=[],
            persona_summary=f"{persona.name} has refined tastes but no businesses matched the filters.",
            generation_time_ms=0,
        )

    user_prompt = recommend_prompts.build_user_prompt(
        persona=persona,
        candidates=candidates,
    )

    model = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")
    client = _get_client()

    t0 = time.perf_counter()
    message = client.messages.create(
        model=model,
        max_tokens=4096,
        system=[
            {
                "type": "text",
                "text": recommend_prompts.SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_prompt}],
    )
    elapsed_ms = int((time.perf_counter() - t0) * 1000)

    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        logger.error("Failed to parse recommendation JSON (stop_reason=%s):\n%s", message.stop_reason, raw)
        raise ValueError("LLM returned invalid JSON") from None

    persona_summary: str = parsed.get("persona_summary", "")
    ranked: list[dict] = parsed.get("ranked", [])

    # Build a lookup so we can merge LLM ranking with full business data
    biz_by_id = {b["business_id"]: b for b in candidates}
    recommendations: list[RecommendedBusiness] = []

    for item in ranked[: filters.max_results]:
        bid = item.get("business_id", "")
        biz = biz_by_id.get(bid)
        if not biz:
            continue
        recommendations.append(
            RecommendedBusiness(
                rank=item["rank"],
                business_id=bid,
                name=biz["name"],
                category=(biz.get("categories") or "")[:120],
                city=biz.get("city", ""),
                stars=float(biz["stars"]),
                review_count=int(biz["review_count"]),
                reason=item.get("reason", ""),
                match_score=float(item.get("match_score", 0.5)),
            )
        )

    return RecommendResponse(
        recommendations=recommendations,
        persona_summary=persona_summary,
        generation_time_ms=elapsed_ms,
    )
