"""
Task A — Review Generation Agent.

Flow:
1. Look up the business in the Yelp dataset to get its business_id.
2. Pull up to 3 real review examples (business-level, then category-level fallback).
3. Build prompt and call Claude.
4. Parse the JSON response and return a ReviewResponse.
"""

from __future__ import annotations

import json
import logging
import os
import time

import anthropic

from app.data.nigerian_examples import get_examples_by_region, get_examples_by_stars
from app.data.yelp_loader import get_loader
from app.models import Business, Persona, ReviewResponse
from app.prompts import review_prompts

logger = logging.getLogger(__name__)

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return _client


def generate_review(
    persona: Persona,
    business: Business,
    context: str | None = None,
) -> ReviewResponse:
    loader = get_loader()

    # Nigerian gold examples — 2 matched by region+tone, always injected first
    gold = get_examples_by_region(persona.region, persona.tone, n=2)
    for ex in gold:
        ex["is_gold"] = True

    # Yelp dataset examples — business-level first, then category fallback
    business_id = loader.find_business_id(business.name, business.city)
    dataset_examples = loader.get_review_examples(
        business_id=business_id,
        categories=business.category,
        n=2,
    )

    # Gold first so the model anchors on Nigerian voice before seeing US examples
    examples = gold + dataset_examples

    user_prompt = review_prompts.build_user_prompt(
        persona=persona,
        business=business,
        context=context,
        examples=examples,
    )

    model = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")
    client = _get_client()

    t0 = time.perf_counter()
    message = client.messages.create(
        model=model,
        max_tokens=1024,
        system=[
            {
                "type": "text",
                "text": review_prompts.SYSTEM_PROMPT,
                # Cache the static system prompt — it never changes between requests
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_prompt}],
    )
    elapsed_ms = int((time.perf_counter() - t0) * 1000)

    raw = message.content[0].text.strip()

    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        logger.error("Failed to parse LLM response as JSON: %s", raw[:300])
        raise ValueError("LLM returned invalid JSON") from None

    review_text: str = parsed["review"]
    stars: int = max(1, min(5, int(parsed["stars"])))
    sentiment: str = parsed.get("sentiment", _infer_sentiment(stars))

    return ReviewResponse(
        review=review_text,
        stars=stars,
        word_count=len(review_text.split()),
        sentiment=sentiment,
        generation_time_ms=elapsed_ms,
    )


def _infer_sentiment(stars: int) -> str:
    if stars >= 4:
        return "positive"
    if stars <= 2:
        return "negative"
    return "mixed"
