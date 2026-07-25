"""
Task B — Three-Agent Recommendation Pipeline.

Agent 1 (Preference Analyst)  persona + history       →  preference profile
Agent 2 (Domain Translator)   profile + target_domain →  translated signals   [cross-domain only]
Agent 3 (Ranker)              profile + candidates    →  ranked recommendations

Cold-start users skip Agent 1. Standard (same-domain) users skip Agent 2.
"""

from __future__ import annotations

import json
import logging
import os
import time

from openai import OpenAI

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

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=os.getenv("NVIDIA_API_KEY"),
        )
    return _client


def _is_cold_start(persona: Persona, history: list[HistoryItem]) -> bool:
    return not persona.bio.strip() and not persona.food_preferences and not history


def _call_claude(system: str, user: str, max_tokens: int = 1024) -> str:
    """Call the LLM with system + user prompt. Returns stripped text."""
    model = os.getenv("NVIDIA_MODEL", "qwen/qwen3-235b-a22b")
    client = _get_client()
    message = client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    raw = message.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    if message.choices[0].finish_reason != "stop":
        logger.warning("Agent stopped with reason=%s — may be truncated", message.choices[0].finish_reason)
    return raw


# ── Agent 1 ───────────────────────────────────────────────────────────────────

def _run_preference_analyst(
    persona: Persona,
    history: list[HistoryItem],
) -> dict:
    """Extract a structured preference profile from persona + history."""
    logger.info("Agent 1 (Preference Analyst): analysing persona '%s'", persona.name)
    user_prompt = recommend_prompts.build_preference_analyst_prompt(persona, history)
    raw = _call_claude(
        recommend_prompts.PREFERENCE_ANALYST_SYSTEM_PROMPT,
        user_prompt,
        max_tokens=1024,
    )
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error("Preference Analyst JSON parse failed: %s\nRaw: %s", e, raw)
        raise ValueError("Preference Analyst failed to return valid JSON") from e


# ── Agent 2 ───────────────────────────────────────────────────────────────────

def _run_domain_translator(
    preference_profile: dict,
    target_domain: str,
    candidates: list[dict],
) -> dict:
    """Translate preference signals from source domain into the target domain."""
    logger.info("Agent 2 (Domain Translator): translating to '%s'", target_domain)
    user_prompt = recommend_prompts.build_domain_translator_prompt(
        preference_profile, target_domain, candidates
    )
    raw = _call_claude(
        recommend_prompts.DOMAIN_TRANSLATOR_SYSTEM_PROMPT,
        user_prompt,
        max_tokens=1024,
    )
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error("Domain Translator JSON parse failed: %s\nRaw: %s", e, raw)
        raise ValueError("Domain Translator failed to return valid JSON") from e


# ── Agent 3 ───────────────────────────────────────────────────────────────────

def _run_ranker(
    candidates: list[dict],
    preference_profile: dict | None,
    domain_translation: dict | None,
    is_cold_start: bool,
    max_results: int,
) -> tuple[list[RecommendedBusiness], str]:
    """Rank candidates. Returns (ranked_list, persona_summary)."""
    logger.info("Agent 3 (Ranker): ranking %d candidates", len(candidates))
    user_prompt = recommend_prompts.build_ranker_prompt(
        candidates=candidates,
        preference_profile=preference_profile,
        domain_translation=domain_translation,
        is_cold_start=is_cold_start,
    )
    raw = _call_claude(
        recommend_prompts.RANKER_SYSTEM_PROMPT,
        user_prompt,
        max_tokens=6000,
    )
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error("Ranker JSON parse failed: %s\nRaw: %s", e, raw)
        raise ValueError("Ranker failed to return valid JSON") from e

    biz_by_id = {b["business_id"]: b for b in candidates}
    results: list[RecommendedBusiness] = []
    for item in parsed.get("ranked", [])[:max_results]:
        bid = item.get("business_id", "")
        biz = biz_by_id.get(bid)
        if not biz:
            continue
        results.append(RecommendedBusiness(
            rank=item["rank"],
            business_id=bid,
            name=biz["name"],
            category=(biz.get("categories") or "")[:120],
            city=biz.get("city", ""),
            stars=float(biz["stars"]),
            review_count=int(biz["review_count"]),
            reason=item.get("reason", ""),
            match_score=float(item.get("match_score", 0.5)),
        ))
    return results, parsed.get("persona_summary", "")


# ── Fast path (single-agent) ─────────────────────────────────────────────────

def _fast_path(
    persona: Persona,
    filters: RecommendFilters,
    history: list[HistoryItem],
    candidates: list[dict],
    cold_start: bool,
    target: str | None,
    t0: float,
) -> RecommendResponse:
    user_prompt = recommend_prompts.build_user_prompt(
        persona=persona,
        candidates=candidates,
        history=history,
        is_cold_start=cold_start,
        target_domain=target,
    )
    raw = _call_claude(recommend_prompts.FAST_SYSTEM_PROMPT, user_prompt, max_tokens=4096)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error("Fast path JSON parse failed: %s\nRaw: %s", e, raw)
        raise ValueError("Recommendation generation failed") from e

    biz_by_id = {b["business_id"]: b for b in candidates}
    results: list[RecommendedBusiness] = []
    for item in parsed.get("ranked", [])[:filters.max_results]:
        bid = item.get("business_id", "")
        biz = biz_by_id.get(bid)
        if not biz:
            continue
        results.append(RecommendedBusiness(
            rank=item["rank"],
            business_id=bid,
            name=biz["name"],
            category=(biz.get("categories") or "")[:120],
            city=biz.get("city", ""),
            stars=float(biz["stars"]),
            review_count=int(biz["review_count"]),
            reason=item.get("reason", ""),
            match_score=float(item.get("match_score", 0.5)),
        ))

    return RecommendResponse(
        recommendations=results,
        persona_summary=parsed.get("persona_summary", ""),
        cross_domain_inference=parsed.get("cross_domain_inference"),
        generation_time_ms=int((time.perf_counter() - t0) * 1000),
    )


# ── Orchestrator ──────────────────────────────────────────────────────────────

def get_recommendations(
    persona: Persona,
    filters: RecommendFilters,
    history: list[HistoryItem] | None = None,
    use_agent_pipeline: bool = False,
) -> RecommendResponse:
    history = history or []
    filters.max_results = 5  # Always enforce 5 results max regardless of frontend input
    loader = get_loader()
    cold_start = _is_cold_start(persona, history)
    t0 = time.perf_counter()

    # ── Retrieve candidates ───────────────────────────────────────────────────
    target = filters.target_domain

    if target:
        candidates = loader.search_businesses(
            city=filters.city,
            state=filters.state,
            categories=[target],
            min_stars=filters.min_stars,
            limit=filters.max_results * 3,
        )
        if not candidates:
            candidates = loader.search_businesses(
                city=filters.city,
                state=filters.state,
                categories=[target],
                min_stars=1.0,
                limit=filters.max_results * 3,
            )
    else:
        default_categories = filters.categories or ["Restaurants", "Food"]
        candidates = loader.search_businesses(
            city=filters.city,
            state=filters.state,
            categories=default_categories,
            min_stars=filters.min_stars,
            limit=filters.max_results * 3,
            diverse=not filters.categories,
        )
        if not candidates:
            candidates = loader.search_businesses(
                city=filters.city,
                state=filters.state,
                categories=default_categories,
                min_stars=filters.min_stars,
                limit=filters.max_results * 3,
                diverse=True,
            )

    if not candidates:
        label = f"'{target}'" if target else "these filters"
        return RecommendResponse(
            recommendations=[],
            persona_summary=f"{persona.name} — no businesses matched {label}.",
            generation_time_ms=0,
        )

    # ── Route to fast path or pipeline ───────────────────────────────────────
    if not use_agent_pipeline:
        return _fast_path(persona, filters, history, candidates, cold_start, target, t0)

    # ── Agent 1: Preference Analyst ───────────────────────────────────────────
    preference_profile: dict | None = None
    if not cold_start:
        preference_profile = _run_preference_analyst(persona, history)

    # ── Agent 2: Domain Translator (cross-domain only) ────────────────────────
    domain_translation: dict | None = None
    if target and preference_profile:
        domain_translation = _run_domain_translator(preference_profile, target, candidates)
    elif target and cold_start:
        # cold-start cross-domain: skip translator, ranker will use quality signals
        logger.info("Cold-start cross-domain — skipping Domain Translator")

    # ── Agent 3: Ranker ───────────────────────────────────────────────────────
    recommendations, persona_summary = _run_ranker(
        candidates=candidates,
        preference_profile=preference_profile,
        domain_translation=domain_translation,
        is_cold_start=cold_start,
        max_results=filters.max_results,
    )

    elapsed_ms = int((time.perf_counter() - t0) * 1000)

    # Surface Agent 1 output as preference_profile string
    profile_str: str | None = None
    if preference_profile:
        profile_str = preference_profile.get("summary") or None

    # Surface Agent 2 output as cross_domain_inference string
    inference_str: str | None = None
    if domain_translation:
        parts = []
        if domain_translation.get("source_signals"):
            parts.append(domain_translation["source_signals"])
        if domain_translation.get("translation"):
            parts.append(domain_translation["translation"])
        inference_str = " ".join(parts) if parts else None

    return RecommendResponse(
        recommendations=recommendations,
        persona_summary=persona_summary,
        preference_profile=profile_str,
        cross_domain_inference=inference_str,
        generation_time_ms=elapsed_ms,
    )
