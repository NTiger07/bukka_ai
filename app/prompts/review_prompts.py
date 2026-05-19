"""
Prompt templates for Task A — review generation.

Nigerian localization is deep here:
- Regional voice notes (Yoruba / Igbo / Hausa / Edo / general)
- Naija English sentence patterns (openers, comparisons, verdicts)
- Nigerian occasion taxonomy (birthday chops, owambe, office hangout, etc.)
- Curated Nigerian gold-set examples injected before any Yelp dataset examples
"""

from __future__ import annotations
from app.models import Persona, Business
from app.prompts.nigerian_voice import (
    SENTENCE_PATTERNS,
    get_occasion_context,
    get_regional_voice,
)


SYSTEM_PROMPT = """\
You are an AI that writes authentic Yelp reviews on behalf of Nigerian users.

Your job is to embody the given persona completely — their voice, values, cultural lens, \
and regional identity — and write a review that reads as if that real person wrote it \
after visiting the business.

## Core Nigerian cultural context
- Value consciousness: Nigerians evaluate whether a place is "worth the price". \
  A ₦5,000 plate equivalent in a US restaurant better deliver.
- Service sensitivity: warmth and attentiveness from staff carry heavy weight. \
  Cold or dismissive service is almost always mentioned.
- Expressiveness: reviews often set the scene first ("So I came here for my colleague's birthday…") \
  before delivering the verdict. Storytelling is natural.
- Social lens: dining is often communal — family, colleagues, dates, celebrations. \
  Context shapes the review.
- Pidgin: use Naija pidgin phrases naturally when the persona's tone calls for it. \
  Do NOT force pidgin into formal or blunt personas.
- Comparisons: if food reminds them of jollof, suya, pepper soup, pounded yam etc., say so.

## Review length
Target 80–150 words. Long enough to cover food, service, atmosphere, and value. \
Short enough to read naturally. Do not pad or repeat yourself.

## Star rating calibration
The persona's historical average rating is provided. Your star rating MUST be anchored \
to that baseline — only deviate if the experience clearly warrants it. \
Do not give extreme scores (1 or 5) unless the bio and visit context strongly support them.

## Output format
Respond with a JSON object and nothing else:
{
  "review": "<the full review text>",
  "stars": <integer 1-5>,
  "sentiment": "<positive|negative|mixed>",
  "reasoning": "<one sentence: why you gave those stars>"
}
"""


def build_user_prompt(
    persona: Persona,
    business: Business,
    context: str | None,
    examples: list[dict],
) -> str:
    lines: list[str] = []

    # Regional voice
    lines.append("## Regional voice for this persona")
    lines.append(get_regional_voice(persona.region))

    # Sentence patterns
    lines.append(SENTENCE_PATTERNS)

    # Persona block
    lines.append("## Persona")
    lines.append(f"Name: {persona.name}")
    if persona.age:
        lines.append(f"Age: {persona.age}")
    if persona.city:
        lines.append(f"From: {persona.city}")
    if persona.region:
        lines.append(f"Regional background: {persona.region.title()}")
    lines.append(f"Tone: {persona.tone}")
    lines.append(f"Historical avg rating they give: {persona.avg_star_rating:.1f} stars")
    lines.append(
        f"Star calibration: stay within ±1 star of {persona.avg_star_rating:.1f} "
        f"unless this visit was clearly exceptional or terrible."
    )
    if persona.food_preferences:
        lines.append(f"Food preferences: {', '.join(persona.food_preferences)}")
    if persona.bio:
        lines.append(f"Bio: {persona.bio}")
    else:
        lines.append(
            "Bio: A typical Nigerian user with no detailed history — "
            "infer reasonable preferences from their rating average and tone."
        )

    # Business block
    lines.append("\n## Business being reviewed")
    lines.append(f"Name: {business.name}")
    lines.append(f"Category: {business.category}")
    if business.city:
        lines.append(f"Location: {business.city}{', ' + business.state if business.state else ''}")
    if business.stars:
        lines.append(f"Yelp rating: {business.stars} stars")
    if business.attributes:
        attrs = business.attributes
        attr_parts = []
        if attrs.price_range:
            attr_parts.append(f"Price: {attrs.price_range}")
        if attrs.outdoor_seating is not None:
            attr_parts.append(f"Outdoor seating: {'yes' if attrs.outdoor_seating else 'no'}")
        if attrs.wifi is not None:
            attr_parts.append(f"WiFi: {'yes' if attrs.wifi else 'no'}")
        if attrs.reservations is not None:
            attr_parts.append(f"Reservations: {'yes' if attrs.reservations else 'no'}")
        if attr_parts:
            lines.append("Attributes: " + " | ".join(attr_parts))

    # Visit context — enrich with occasion taxonomy if it matches
    if context:
        lines.append(f"\n## Visit context\n{context}")
        occasion_frame = get_occasion_context(context)
        if occasion_frame:
            lines.append(f"\nOccasion framing: {occasion_frame}")

    # Nigerian gold examples (always first)
    if examples:
        lines.append("\n## Authentic Nigerian review examples (style reference)")
        lines.append(
            "These are real Nigerian-voice reviews. Use them to calibrate rhythm, "
            "idiom, and cultural framing — do NOT copy the content."
        )
        for i, ex in enumerate(examples, 1):
            source = "Nigerian gold" if ex.get("is_gold") else f"Yelp ★{ex['stars']}"
            preview = ex["text"][:450].replace("\n", " ")
            suffix = "..." if len(ex["text"]) > 450 else ""
            lines.append(f"\nExample {i} ({source}): {preview}{suffix}")

    lines.append(
        "\n## Task\nWrite a review that this persona would leave for this business. "
        "Apply the regional voice notes and sentence patterns naturally — not all at once. "
        "Make it feel completely authentic, not generic or performative. "
        "Return ONLY valid JSON matching the specified format."
    )

    return "\n".join(lines)
