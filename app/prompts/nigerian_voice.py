"""
Nigerian voice engineering for review generation.

Three components:
1. REGIONAL_VOICE  — per-region language notes (Yoruba, Igbo, Hausa, Edo, general Lagos)
2. SENTENCE_PATTERNS — 20 Naija English structural patterns
3. OCCASION_TAXONOMY — Nigerian dining/outing context frames
"""

from __future__ import annotations

# ── 1. Regional voice notes ────────────────────────────────────────────────────

REGIONAL_VOICE: dict[str, str] = {
    "yoruba": """\
Yoruba voice notes:
- Exclamations: "Ehn ehn!", "Oya!", "E don do", "Mo gbe" (I'm finished), "Omo!"
- Sentence rhythm: musical, often builds toward a final verdict with "sha" or "o" at the end
- Hospitality lens: warmth of welcome and whether staff "carried themselves well" matters a lot
- Pride expression: "This place has done well for themselves o"
- Mild exasperation: "See this thing now", "How e take reach this level?"
- Money language: "The price is not smiling" or "The price smiled at us today"
""",
    "igbo": """\
Igbo voice notes:
- Exclamations: "Chei!", "Nna!", "Tufiakwa" (God forbid), "Oya na"
- Directness: Igbo reviewers often state the verdict early, then explain — not the other way around
- Disappointment: "This place disappointed me well well"
- Quality standard: "You do not waste an Igbo person's money"
- Approval: "Nna, this thing is doing something", "The food landed well"
- Community reference: "I will bring my people here" or "I cannot bring my people here"
""",
    "hausa": """\
Hausa voice notes:
- Exclamations: "Wallahi" (I swear), "Allah ya kiyaye" (God protect), "Subhanallah"
- Hospitality focus: how guests are welcomed carries even more weight than food
- Measured tone: less hyperbolic than Yoruba/Igbo, but warmth shows through
- Family reference: decisions are evaluated through "would I bring my family here?"
- Approval: "They received us well", "The place has barakah (blessing)"
- Restraint in negativity: disappointment expressed through understatement, not rage
""",
    "edo": """\
Edo voice notes:
- Address style: "My brother", "My sister" — very warm and inclusive
- Directness: Edo reviewers will say exactly what they think, no softening
- Surprise: "I no expect am o" is a high compliment
- Standards: Bini people measure experiences against high hospitality standards — being made to feel like a valued guest matters
- Food standard: bold flavor, generous portion — "they fed us well" is the bar
- Approval: "This place has sense", "Na here dem dey keep the good food"
""",
    "general": """\
General Lagos/Nigerian voice notes:
- Code-switch freely between Standard Nigerian English and Naija Pidgin
- Reviews often open by setting the scene ("So I came here for X...")
- Value is always evaluated: "Is this place worth the price?"
- Service warmth is mentioned regardless of the food quality
- Comparisons to Nigerian food standards are natural
- Final verdict sentences tend to be short and decisive
""",
}


# ── 2. Naija English sentence patterns ───────────────────────────────────────

SENTENCE_PATTERNS = """\
## Naija English structural patterns (use these naturally, not all at once)

OPENERS — setting the scene:
- "So I come enter this place thinking say..."
- "See ehn, I carry [high/low] expectation come here..."
- "My [friend/colleague/sister] drag me come this place and..."
- "I have been meaning to try this place since [occasion] and finally..."
- "Based on the hype wey I hear, I enter with open mind..."

COMPARISONS TO NIGERIAN FOOD/STANDARDS:
- "The spice level reach almost like [mama's stew / suya from the mallam / correct pepper soup] — almost."
- "This remind me of [Nigerian food equivalent] but with [difference]"
- "E get that smoky depth wey you know means someone actually cook with love"
- "The seasoning was present — not the kind where you chew and nothing is happening"

SERVICE OBSERVATIONS:
- "The waiter carried himself well / carried herself well"
- "They no try to rush us away even when the place filled up"
- "Staff were attentive without being in your face — that balance is hard to find"
- "See as they acted like they dey do us favour..."
- "The [manager/waitress] apologised genuinely — that kind gesture can turn bad situation around"

VALUE ASSESSMENTS:
- "For this price, [verdict]"
- "My money entered [right/wrong] place today"
- "The price smiled at us / The price is not smiling"
- "For what dem dey charge, [expectation] is not optional"
- "E make sense for the quality" / "E no make sense for the quality"

SURPRISE / DISAPPOINTMENT ESCALATION:
- "Mehn, I no expect am but..."
- "Chei. I was not ready."
- "But then [thing happened] and everything changed"
- "I keep saying I will not be surprised and I keep being surprised"

VERDICTS / CLOSERS:
- "Bottom line: [verdict]"
- "E don set." (It's sorted / This place is solid)
- "I go come back, that one is settled."
- "Management needs to [fix X] before [marketing / inviting people]"
- "This place has sense." / "This place has done well for themselves."
- "Too many good [restaurants] to waste your time here."
"""


# ── 3. Nigerian occasion taxonomy ────────────────────────────────────────────

OCCASION_TAXONOMY: dict[str, str] = {
    "birthday chops": (
        "A birthday celebration — expectations are HIGH, the whole experience must feel special. "
        "Food, service, and ambiance all matter. Being remembered or acknowledged by staff scores major points. "
        "Disappointment here is personal and the review tone will reflect that."
    ),
    "owambe": (
        "A big celebration (wedding, naming ceremony, graduation party venue). "
        "Scale and abundance matter — 'they fed us well' is the key metric. "
        "Atmosphere must match the celebratory energy. Value for a large group is paramount."
    ),
    "office hangout": (
        "After-work with colleagues. Casual, quick enough not to run into next morning, "
        "but social enough to unwind. Value-conscious — this is on personal budget, not expense account. "
        "Noise level matters; people need to actually talk."
    ),
    "first date": (
        "Impression matters enormously. Ambiance, service warmth, and food quality "
        "are all proxies for how much the person cared about planning. "
        "Price is secondary to experience. Any embarrassing service failures will be remembered."
    ),
    "family sunday": (
        "Multi-generational outing — grandparents to children. Quantity and variety matter. "
        "Staff patience with children is noticed and appreciated. "
        "The goal is everyone leaves satisfied, not a gourmet experience."
    ),
    "solo treat": (
        "Personal indulgence — the reviewer wants to feel pampered without needing a reason. "
        "Quality and service warmth are personal now, not shared. "
        "A solo diner who is ignored or made to feel unwelcome will mention it."
    ),
    "business lunch": (
        "Professional context — needs to be impressive enough for a client but efficient. "
        "Noise level matters (needs to be able to talk business). "
        "Service speed matters. Price is secondary — the business is paying."
    ),
    "detty december": (
        "Lagos energy imported wherever they are — holiday season, group outing, "
        "the vibe must match the season. Nights out, good music, good food, great company. "
        "This review will be written with energy."
    ),
    "catching up": (
        "Reconnecting with an old friend or family member not seen in a long time. "
        "The place needs to allow long stays without pressure. "
        "Comfort and warmth of environment matters more than Michelin-star food."
    ),
}


def get_regional_voice(region: str | None) -> str:
    """Return the voice notes for a given region, defaulting to general."""
    return REGIONAL_VOICE.get(region or "general", REGIONAL_VOICE["general"])


def get_occasion_context(occasion: str | None) -> str | None:
    """Return enriched occasion framing if the occasion matches a known taxonomy entry."""
    if not occasion:
        return None
    lower = occasion.lower()
    for key, description in OCCASION_TAXONOMY.items():
        if key in lower:
            return description
    return None
