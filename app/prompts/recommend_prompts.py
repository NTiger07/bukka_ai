"""
Prompt templates for Task B — personalized recommendations.

Two prompt paths:
- build_user_prompt()        — standard same-domain recommendations
- build_cross_domain_prompt() — explicit 2-step reasoning: infer signals from
                                history, translate to target domain, rank
"""

from __future__ import annotations
from app.models import HistoryItem, Persona


SYSTEM_PROMPT = """\
You are a personalized business recommendation agent for Nigerian users.

Your job: given a user persona and a shortlist of real businesses, rank the businesses \
that best match this persona and explain WHY in a culturally resonant way.

## What matters to Nigerian users (weight these heavily)
- Value for money — "is this place worth it?"
- Bold, flavourful experiences — bland or mediocre is a dealbreaker
- Attentive, warm service — being made to feel welcome matters
- Atmosphere that fits the occasion (casual hangout vs. special occasion)
- Similarity to bold West African sensibilities (intensity, warmth, richness)

## Cold-start users
If the persona has no bio and no stated preferences, do NOT fabricate tastes. \
Instead, rank by: (1) general quality and popularity, (2) value for money, \
(3) variety across categories. Explain recommendations in terms of why \
any Nigerian visitor would enjoy them, not assumed personal preferences.

## Cross-domain recommendations
When candidates span multiple business types (restaurants, bars, spas, shopping, \
entertainment), recommend the best across ALL domains — not just food. \
A great recommendation for a stressed professional might be a spa, not another restaurant.

## Output format
Respond with a JSON object and nothing else:
{
  "persona_summary": "<2-sentence read of this persona's identity>",
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

CROSS_DOMAIN_SYSTEM_PROMPT = """\
You are a cross-domain recommendation agent for Nigerian users.

You receive a user's visit history from one or more domains (e.g., restaurants, bars) \
and a target domain they want recommendations for (e.g., spas, shopping, entertainment). \
Your job is to reason explicitly about what the user's history reveals about their deeper \
preferences, then translate those signals into the target domain.

## Reasoning process you MUST follow
Step 1 — Extract signals: What does this user consistently value? What do they avoid? \
Look at star patterns, categories they rate highly, and any notes they left.

Step 2 — Translate to target domain: How do those signals map to the target domain? \
Be explicit. Example: "Values bold intensity in food → likely wants deep tissue massage, \
not a gentle Swedish; hates bland → avoid generic chain spas."

Step 3 — Rank candidates using the translated signals.

## Nigerian cultural lens
Apply Nigerian values throughout: warmth of welcome, value for money, \
quality that justifies the spend, experience that matches the occasion.

## Output format
Respond with a JSON object and nothing else:
{
  "persona_summary": "<2-sentence read of this persona's identity>",
  "cross_domain_inference": "<Step 1 + Step 2 combined: what signals you extracted and how they translate. 3-5 sentences.>",
  "ranked": [
    {
      "business_id": "<id>",
      "rank": <1-based integer>,
      "reason": "<1-2 sentences tying the cross-domain signal directly to this specific business>",
      "match_score": <float 0.0-1.0>
    }
  ]
}

Rank ALL candidates. The `reason` must reference the cross-domain inference, not just the business.
"""


def build_user_prompt(
    persona: Persona,
    candidates: list[dict],
    is_cold_start: bool = False,
    is_cross_domain: bool = False,
) -> str:
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
    if persona.bio:
        lines.append(f"Bio: {persona.bio}")
    else:
        lines.append("Bio: [None provided — cold-start user]")

    if is_cold_start:
        lines.append(
            "\nNote: This is a cold-start user with no history. "
            "Rank by quality, popularity, and broad Nigerian appeal. Do not assume specific preferences."
        )
    if is_cross_domain:
        lines.append(
            "\nNote: Candidates span multiple business categories. "
            "Recommend the best across ALL domains — diversify your top picks."
        )

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

    task = (
        "\n## Task\nRank ALL of the above businesses for this specific persona. "
        "The reason must be personal and specific — avoid phrases like 'great food' or 'good service'. "
    )
    if is_cold_start:
        task += "Since this is a cold-start user, explain in terms of universal Nigerian appeal and quality. "
    else:
        task += "Reference the persona's preferences, bio, and cultural context directly. "
    task += "Return ONLY valid JSON matching the specified format."
    lines.append(task)

    return "\n".join(lines)


def build_cross_domain_prompt(
    persona: Persona,
    history: list[HistoryItem],
    target_domain: str,
    candidates: list[dict],
) -> str:
    lines: list[str] = []

    # Persona
    lines.append("## Persona")
    lines.append(f"Name: {persona.name}")
    if persona.age:
        lines.append(f"Age: {persona.age}")
    if persona.city:
        lines.append(f"Home city: {persona.city}")
    lines.append(f"Tone: {persona.tone}")
    lines.append(f"Average star rating they give: {persona.avg_star_rating:.1f}")
    if persona.food_preferences:
        lines.append(f"Food preferences: {', '.join(persona.food_preferences)}")
    if persona.bio:
        lines.append(f"Bio: {persona.bio}")

    # History block — the source domain signals
    lines.append(f"\n## User's visit history (source domain signals)")
    lines.append("These are real places this user has visited and rated:")
    for item in history:
        line = f"- {item.business_name} [{item.category}] → ★{item.stars}"
        if item.notes:
            line += f': "{item.notes}"'
        lines.append(line)

    if not history:
        lines.append("(No history provided — infer from persona bio and food preferences only)")

    # Target domain
    lines.append(f"\n## Target domain: {target_domain}")
    lines.append(
        f"The user wants recommendations specifically in: {target_domain}\n"
        f"Apply Steps 1–2 from your reasoning process before ranking."
    )

    # Candidates in the target domain
    lines.append(f"\n## Candidate businesses in '{target_domain}' ({len(candidates)} total)")
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
        f"\n## Task\n"
        f"1. Extract the user's preference signals from their history.\n"
        f"2. Explicitly state how those signals translate to '{target_domain}'.\n"
        f"3. Rank ALL candidates using those translated signals.\n"
        f"Each reason must reference the cross-domain inference — not just the business. "
        f"Return ONLY valid JSON matching the specified format."
    )

    return "\n".join(lines)
