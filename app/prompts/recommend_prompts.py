"""
Prompt templates for Task B recommendations.

Two modes (toggled by use_agent_pipeline in the request):

FAST PATH (single-agent):
  build_user_prompt()         — standard same-domain
  build_cross_domain_prompt() — cross-domain with inline 3-step reasoning

PIPELINE PATH (three-agent):
  Agent 1 — Preference Analyst:  persona + history  →  preference profile
  Agent 2 — Domain Translator:   profile + target   →  translated signals (cross-domain only)
  Agent 3 — Ranker:              profile + candidates →  ranked list
"""

from __future__ import annotations
from app.models import HistoryItem, Persona


# ── Agent 1: Preference Analyst ───────────────────────────────────────────────

PREFERENCE_ANALYST_SYSTEM_PROMPT = """\
You are a user preference analyst for a Nigerian recommendation platform.

Your job: read a user's persona and their past visit history, then produce a concise, \
structured profile of what this specific person truly values — not what their demographic \
"should" value.

Focus on:
- Patterns across their rated businesses (what high-starred places have in common)
- Patterns in their low-rated places (what they consistently dislike)
- Price sensitivity (inferred from avg_star_rating and bio)
- Experience priorities (atmosphere, service, authenticity, boldness, value-for-money)
- Any Nigerian cultural signals in their bio or preferences

Output ONLY valid JSON — no prose, no markdown:
{
  "preferred_attributes": ["<2-5 specific things they love>"],
  "avoided_attributes": ["<2-5 specific things they hate or avoid>"],
  "price_sensitivity": "budget" | "mid-range" | "premium",
  "experience_priorities": ["<ordered list of what matters most to them>"],
  "cultural_notes": "<1-2 sentences on Nigerian cultural context for this person>",
  "summary": "<2 sentences: who is this person and what experience are they looking for>"
}
"""


def build_preference_analyst_prompt(
    persona: Persona,
    history: list[HistoryItem],
) -> str:
    lines: list[str] = ["## Persona"]
    lines.append(f"Name: {persona.name}")
    if persona.age:
        lines.append(f"Age: {persona.age}")
    if persona.city:
        lines.append(f"Home city: {persona.city}")
    if persona.region:
        lines.append(f"Region/background: {persona.region}")
    lines.append(f"Tone: {persona.tone}")
    lines.append(f"Avg star rating they give: {persona.avg_star_rating:.1f}/5.0")
    if persona.food_preferences:
        lines.append(f"Food preferences: {', '.join(persona.food_preferences)}")
    if persona.bio:
        lines.append(f"Bio: {persona.bio}")

    lines.append("\n## Visit History")
    if history:
        lines.append("Past visits this user has rated:")
        for item in history:
            line = f"- {item.business_name} [{item.category}] → ★{item.stars}/5"
            if item.notes:
                line += f': "{item.notes}"'
            lines.append(line)
    else:
        lines.append("(No visit history — infer entirely from persona bio and stated preferences)")

    lines.append(
        "\n## Task\nAnalyse the persona and history above. "
        "Identify the genuine preference signals. "
        "Return ONLY valid JSON matching the specified format."
    )
    return "\n".join(lines)


# ── Agent 2: Domain Translator ────────────────────────────────────────────────

DOMAIN_TRANSLATOR_SYSTEM_PROMPT = """\
You are a cross-domain preference translator for a Nigerian recommendation platform.

You receive a structured preference profile extracted from a user's history in one domain \
(e.g., restaurants), and a target domain the user wants recommendations in (e.g., Nightlife, \
Beauty & Spas, Shopping). Your job is to reason explicitly about how the user's core values \
map to the new domain.

Be concrete. Bad translation: "They like quality → recommend quality places."
Good translation: "They value quiet, attentive service and dislike chaotic environments → \
in Nightlife, this means upscale cocktail bars or jazz lounges, NOT clubs or sports bars."

Also apply Nigerian cultural values:
- Warmth and being made to feel welcome
- Value for money — premium spend must be justified
- Experiences that match the occasion and social context

Output ONLY valid JSON:
{
  "source_signals": "<what the user values, drawn from the preference profile — 2-3 sentences>",
  "translation": "<how those signals map to the target domain — 3-4 sentences, be specific>",
  "ideal_venue_profile": "<describe the perfect place in the target domain for this user — 1-2 sentences>",
  "red_flags": ["<2-4 specific things to avoid in the target domain for this user>"]
}
"""


def build_domain_translator_prompt(
    preference_profile: dict,
    target_domain: str,
    candidates: list[dict],
) -> str:
    lines: list[str] = ["## User Preference Profile (from Preference Analyst)"]
    lines.append(f"Preferred: {', '.join(preference_profile.get('preferred_attributes', []))}")
    lines.append(f"Avoided: {', '.join(preference_profile.get('avoided_attributes', []))}")
    lines.append(f"Price sensitivity: {preference_profile.get('price_sensitivity', 'unknown')}")
    lines.append(f"Priorities: {', '.join(preference_profile.get('experience_priorities', []))}")
    if preference_profile.get("cultural_notes"):
        lines.append(f"Cultural context: {preference_profile['cultural_notes']}")
    if preference_profile.get("summary"):
        lines.append(f"Summary: {preference_profile['summary']}")

    lines.append(f"\n## Target Domain: {target_domain}")

    lines.append(f"\n## Available candidates in '{target_domain}'")
    for biz in candidates[:5]:
        cats = (biz.get("categories") or "")[:100]
        lines.append(f"- {biz['name']} | {cats} | ★{biz['stars']} | {biz.get('city', '')}")

    lines.append(
        f"\n## Task\nTranslate this user's preference profile into signals relevant for "
        f"'{target_domain}'. Be specific — reference the actual candidate types above to "
        f"ground your translation. Return ONLY valid JSON."
    )
    return "\n".join(lines)


# ── Agent 3: Ranker ───────────────────────────────────────────────────────────

RANKER_SYSTEM_PROMPT = """\
You are a business ranking agent for a Nigerian recommendation platform.

You receive either:
(a) a structured user preference profile (standard recommendations), or
(b) a cross-domain translation profile (cross-domain recommendations)

Your job: rank the candidate businesses by fit to the profile. Be specific and personal — \
every reason must tie the business directly to the profile, not generic praise.

Nigerian cultural lens — weight these throughout:
- Value for money: premium spend must feel justified
- Bold, rich experiences: mediocre or bland is a dealbreaker
- Warmth of welcome: attentive, personal service
- Occasion fit: does this place match how this user actually socialises?

Output ONLY valid JSON:
{
  "persona_summary": "<2 sentences: who this person is and what they need right now>",
  "ranked": [
    {
      "business_id": "<id>",
      "rank": <1-based integer>,
      "reason": "<1 sentence max: tie the profile directly to THIS business — no generic filler>",
      "match_score": <float 0.0-1.0>
    }
  ]
}

Rank ALL businesses but return ONLY the TOP 5 by fit. Keep every reason to ONE sentence — be precise, not verbose.
"""


def build_ranker_prompt(
    candidates: list[dict],
    preference_profile: dict | None = None,
    domain_translation: dict | None = None,
    is_cold_start: bool = False,
) -> str:
    lines: list[str] = []

    if is_cold_start:
        lines.append("## User Profile")
        lines.append(
            "Cold-start user — no history or stated preferences available. "
            "Rank by: (1) overall star quality and review volume, "
            "(2) broad Nigerian cultural appeal, (3) category diversity. "
            "Explain in terms of why any Nigerian visitor would enjoy each place."
        )
    elif domain_translation:
        lines.append("## Cross-Domain Translation Profile")
        lines.append(f"Source signals: {domain_translation.get('source_signals', '')}")
        lines.append(f"Translation: {domain_translation.get('translation', '')}")
        lines.append(f"Ideal venue: {domain_translation.get('ideal_venue_profile', '')}")
        red_flags = domain_translation.get("red_flags", [])
        if red_flags:
            lines.append(f"Red flags to avoid: {', '.join(red_flags)}")
    elif preference_profile:
        lines.append("## User Preference Profile")
        lines.append(f"Preferred: {', '.join(preference_profile.get('preferred_attributes', []))}")
        lines.append(f"Avoided: {', '.join(preference_profile.get('avoided_attributes', []))}")
        lines.append(f"Price sensitivity: {preference_profile.get('price_sensitivity', 'unknown')}")
        lines.append(f"Priorities: {', '.join(preference_profile.get('experience_priorities', []))}")
        if preference_profile.get("cultural_notes"):
            lines.append(f"Cultural context: {preference_profile['cultural_notes']}")
        if preference_profile.get("summary"):
            lines.append(f"Who they are: {preference_profile['summary']}")

    lines.append(f"\n## Candidate businesses ({len(candidates)} total)")
    for biz in candidates:
        cats = (biz.get("categories") or "Unknown")[:120]
        lines.append(
            f"\n- business_id: {biz['business_id']}\n"
            f"  Name: {biz['name']}\n"
            f"  Category: {cats}\n"
            f"  Location: {biz.get('city', '')}, {biz.get('state', '')}\n"
            f"  Stars: {biz['stars']} | Reviews: {int(biz['review_count'])}"
        )

    lines.append(
        "\n## Task\nRank ALL businesses above. "
        "Each reason must be ONE sentence only — directly reference the profile. "
        "No generic phrases. No extra prose outside the JSON. "
        "Return ONLY valid JSON."
    )
    return "\n".join(lines)


# ── Fast path: single-agent prompts ──────────────────────────────────────────

FAST_SYSTEM_PROMPT = """\
You are a personalized business recommendation agent for Nigerian users.

Rank the candidate businesses that best match the persona. Be specific and personal — \
every reason must tie directly to this persona's stated preferences and cultural context.

Nigerian values to weight heavily:
- Value for money, bold experiences, warm service, occasion fit

Cold-start: if persona has no bio and no preferences, rank by quality, popularity, \
and broad Nigerian appeal. Do not fabricate preferences.

Cross-domain: when candidates span multiple types, recommend the best across ALL domains.

For cross-domain with history, follow these steps explicitly in cross_domain_inference:
Step 1 — Extract what the user values from their history.
Step 2 — Translate those signals to the target domain.
Step 3 — Rank using the translated signals.

Output ONLY valid JSON — no prose, no markdown:
{
  "persona_summary": "<2 sentences: who this person is and what they need>",
  "cross_domain_inference": "<1-2 sentences: how their restaurant preferences translate to the target domain — or null if not cross-domain>",
  "ranked": [
    {"business_id": "<id>", "rank": <int>, "reason": "<1 sentence max tying this business to the persona>", "match_score": <0.0-1.0>}
  ]
}

Return ONLY the TOP 5 ranked results. One sentence per reason. No extra text outside the JSON.
"""


def build_user_prompt(
    persona: Persona,
    candidates: list[dict],
    history: list | None = None,
    is_cold_start: bool = False,
    target_domain: str | None = None,
) -> str:
    lines: list[str] = ["## Persona"]
    lines.append(f"Name: {persona.name}")
    if persona.age:
        lines.append(f"Age: {persona.age}")
    if persona.city:
        lines.append(f"Home city: {persona.city}")
    if persona.region:
        lines.append(f"Region: {persona.region}")
    lines.append(f"Tone: {persona.tone}")
    lines.append(f"Avg star rating: {persona.avg_star_rating:.1f}")
    if persona.food_preferences:
        lines.append(f"Food preferences: {', '.join(persona.food_preferences)}")
    if persona.bio:
        lines.append(f"Bio: {persona.bio}")
    else:
        lines.append("Bio: [None — cold-start user]")

    if history:
        lines.append("\n## Visit History")
        for item in history:
            line = f"- {item.business_name} [{item.category}] → ★{item.stars}"
            if item.notes:
                line += f': "{item.notes}"'
            lines.append(line)

    if target_domain:
        lines.append(f"\n## Target domain: {target_domain}")

    if is_cold_start:
        lines.append("\nNote: Cold-start user — rank by quality and broad Nigerian appeal.")
    if target_domain:
        lines.append("Note: Cross-domain request — follow Steps 1-2-3 in cross_domain_inference.")

    lines.append(f"\n## Candidates ({len(candidates)} total)")
    for biz in candidates:
        cats = (biz.get("categories") or "Unknown")[:120]
        lines.append(
            f"\n- business_id: {biz['business_id']}\n"
            f"  Name: {biz['name']}\n"
            f"  Category: {cats}\n"
            f"  Location: {biz.get('city', '')}, {biz.get('state', '')}\n"
            f"  Stars: {biz['stars']} | Reviews: {int(biz['review_count'])}"
        )

    lines.append("\n## Task\nRank the candidates. Return ONLY the TOP 5 by fit. One sentence per reason. Return ONLY valid JSON.")
    return "\n".join(lines)
