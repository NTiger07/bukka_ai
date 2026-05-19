"""
Task B — Recommendation Agent.

Two modes:
- Standard:      persona + filters → ranked same-domain recommendations
- Cross-domain:  persona + history + target_domain → infer signals → rank in new domain
"""

from __future__ import annotations

import json
import logging
import os
import time

import anthropic

from app.data.yelp_loader import get_loader
from app.models import (
    HistoryItem,
    Persona,
    RecommendFilters,
    RecommendResponse,
    RecommendedBusiness,
)
from app.prompts import recommend_prompts

logger = logging.getLogger(__name__)

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return _client


def _is_cold_start(persona: Persona, history: list[HistoryItem]) -> bool:
    has_bio = bool(persona.bio and persona.bio.strip())
    has_prefs = bool(persona.food_preferences)
    has_history = bool(history)
    return not has_bio and not has_prefs and not has_history


def _call_claude(system: str, user: str, max_tokens: int = 4096) -> tuple[str, int]:
    """Call Claude and return (raw_text, elapsed_ms)."""
    model = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5-20251001")
    client = _get_client()
    t0 = time.perf_counter()
    message = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user}],
    )
    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    raw = message.content[0].text.strip()

    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    stop = message.stop_reason
    if stop != "end_turn":
        logger.warning("Claude stopped with reason=%s — response may be truncated", stop)

    return raw, elapsed_ms


def _parse_ranked(
    parsed: dict,
    candidates: list[dict],
    max_results: int,
) -> list[RecommendedBusiness]:
    biz_by_id = {b["business_id"]: b for b in candidates}
    results: list[RecommendedBusiness] = []
    for item in parsed.get("ranked", [])[:max_results]:
        bid = item.get("business_id", "")
        biz = biz_by_id.get(bid)
        if not biz:
            continue
        results.append(
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
    return results


def get_recommendations(
    persona: Persona,
    filters: RecommendFilters,
    history: list[HistoryItem] | None = None,
) -> RecommendResponse:
    history = history or []
    loader = get_loader()
    cold_start = _is_cold_start(persona, history)

    # ── Cross-domain path ─────────────────────────────────────────────────────
    if filters.target_domain:
        return _cross_domain_recommendations(
            persona=persona,
            filters=filters,
            history=history,
            loader=loader,
        )

    # ── Standard path ─────────────────────────────────────────────────────────
    cross_domain_diverse = not filters.categories

    candidates = loader.search_businesses(
        city=filters.city,
        state=filters.state,
        categories=filters.categories or None,
        min_stars=filters.min_stars,
        limit=20,
        diverse=cross_domain_diverse,
    )

    if not candidates:
        logger.warning("No candidates with category filter; widening search.")
        candidates = loader.search_businesses(
            city=filters.city,
            state=filters.state,
            min_stars=filters.min_stars,
            limit=20,
            diverse=True,
        )

    if not candidates:
        return RecommendResponse(
            recommendations=[],
            persona_summary=f"{persona.name} — no businesses matched the filters.",
            generation_time_ms=0,
        )

    user_prompt = recommend_prompts.build_user_prompt(
        persona=persona,
        candidates=candidates,
        is_cold_start=cold_start,
        is_cross_domain=cross_domain_diverse,
    )

    try:
        raw, elapsed_ms = _call_claude(recommend_prompts.SYSTEM_PROMPT, user_prompt)
        parsed = json.loads(raw)
    except (json.JSONDecodeError, Exception) as e:
        logger.error("Standard recommendation failed: %s", e)
        raise ValueError("Recommendation generation failed") from e

    return RecommendResponse(
        recommendations=_parse_ranked(parsed, candidates, filters.max_results),
        persona_summary=parsed.get("persona_summary", ""),
        generation_time_ms=elapsed_ms,
    )


def _cross_domain_recommendations(
    persona: Persona,
    filters: RecommendFilters,
    history: list[HistoryItem],
    loader,
) -> RecommendResponse:
    target = filters.target_domain

    # Search the dataset in the target domain specifically
    candidates = loader.search_businesses(
        city=filters.city,
        state=filters.state,
        categories=[target],
        min_stars=filters.min_stars,
        limit=20,
    )

    if not candidates:
        # Widen — drop min_stars constraint for niche domains
        candidates = loader.search_businesses(
            city=filters.city,
            state=filters.state,
            categories=[target],
            min_stars=1.0,
            limit=20,
        )

    if not candidates:
        return RecommendResponse(
            recommendations=[],
            persona_summary=f"{persona.name} — no '{target}' businesses found in the dataset for this location.",
            cross_domain_inference=None,
            generation_time_ms=0,
        )

    user_prompt = recommend_prompts.build_cross_domain_prompt(
        persona=persona,
        history=history,
        target_domain=target,
        candidates=candidates,
    )

    try:
        raw, elapsed_ms = _call_claude(
            recommend_prompts.CROSS_DOMAIN_SYSTEM_PROMPT,
            user_prompt,
            max_tokens=4096,
        )
        parsed = json.loads(raw)
    except (json.JSONDecodeError, Exception) as e:
        logger.error("Cross-domain recommendation failed: %s", e)
        raise ValueError("Cross-domain recommendation generation failed") from e

    return RecommendResponse(
        recommendations=_parse_ranked(parsed, candidates, filters.max_results),
        persona_summary=parsed.get("persona_summary", ""),
        cross_domain_inference=parsed.get("cross_domain_inference"),
        generation_time_ms=elapsed_ms,
    )
