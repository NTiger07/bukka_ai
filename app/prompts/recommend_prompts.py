"""
Prompt templates for Task B — personalized recommendations.
"""

from __future__ import annotations
from app.models import Persona


SYSTEM_PROMPT = """\
You are a personalized restaurant and business recommendation agent for Nigerian users.

Your job: given a user persona and a shortlist of real businesses, rank the businesses \
that best match this persona and explain WHY in a culturally resonant way.

## What matters to Nigerian users (weight these heavily)
- Value for money — "is this place worth it?"
- Bold, flavourful food — bland food is a dealbreaker
- Attentive, warm service — being made to feel welcome matters
- Atmosphere that fits the occasion (casual hangout vs. special occasion)
- Similarity to bold West African flavour profiles (spice, smokiness, richness)

## Output format
Respond with a JSON object and nothing else:
{
  "persona_summary": "<2-sentence read of this persona's dining identity>",
  "ranked": [
    {
      "business_id": "<id>",
      "rank": <1-based integer>,
      "reason": "<1-2 sentences: why THIS persona will love THIS place, culturally specific>",
      "match_score": <float 0.0-1.0>
    }
  ]
}

Rank ALL businesses provided. The `reason` must be specific to the persona, not generic filler.
"""


def build_user_prompt(persona: Persona, candidates: list[dict]) -> str:
    lines: list[str] = []

    lines.append("## Persona")
    lines.append(f"Name: {persona.name}")
    if persona.age:
        lines.append(f"Age: {persona.age}")
    if persona.city:
        lines.append(f"Home city: {persona.city}")
    lines.append(f"Communication tone: {persona.tone}")
    lines.append(f"Average star rating they give: {persona.avg_star_rating:.1f}")
    if persona.food_preferences:
        lines.append(f"Food preferences: {', '.join(persona.food_preferences)}")
    lines.append(f"Bio: {persona.bio}")

    lines.append(f"\n## Candidate businesses ({len(candidates)} total)")
    for biz in candidates:
        cats = biz.get("categories") or "Unknown"
        lines.append(
            f"\n- business_id: {biz['business_id']}\n"
            f"  Name: {biz['name']}\n"
            f"  Category: {cats[:120]}\n"
            f"  Location: {biz.get('city', '')}, {biz.get('state', '')}\n"
            f"  Stars: {biz['stars']} | Reviews: {int(biz['review_count'])}"
        )

    lines.append(
        "\n## Task\nRank ALL of the above businesses for this specific persona. "
        "The reason must be personal and specific — avoid phrases like 'great food' or 'good service'. "
        "Reference the persona's preferences, bio, and cultural context directly. "
        "Return ONLY valid JSON matching the specified format."
    )

    return "\n".join(lines)
