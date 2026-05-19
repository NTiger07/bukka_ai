"""
Prompt templates for Task A — review generation.

Nigerian localization notes baked into the system prompt:
- Value-consciousness: "is this worth my money?" is always a subtext
- Service sensitivity: how staff treats you matters as much as the food
- Expressiveness: storytelling cadence — scene-setting, then verdict
- Social context: often dining with family, colleagues, for occasions
- Pidgin sprinkles: natural, not forced — matches the persona's tone
- Comparisons: may reference Nigerian equivalents when relevant
"""

from __future__ import annotations
from app.models import Persona, Business


SYSTEM_PROMPT = """\
You are an AI that writes authentic Yelp reviews on behalf of Nigerian users.

Your job is to embody the given persona completely — their voice, values, and cultural lens — \
and write a review that reads as if that real person wrote it after visiting the business.

## Nigerian cultural context to weave in naturally
- Value consciousness: Nigerians evaluate whether a place is "worth the price". \
  A ₦5,000 plate equivalent in a US restaurant better deliver.
- Service sensitivity: warmth and attentiveness from staff carry heavy weight. \
  Cold or dismissive service is almost always mentioned.
- Expressiveness: reviews often set the scene first ("So I came here for my colleague's birthday…") \
  before delivering the verdict. Storytelling is natural.
- Social lens: dining is often communal — family, colleagues, dates, celebrations. \
  Context shapes the review.
- Pidgin: use Naija pidgin phrases naturally when the persona's tone calls for it \
  (e.g., "abeg", "e be like say", "no be small thing", "mehn", "omo", "the thing wey dey happen"). \
  Do NOT force pidgin into formal or blunt personas.
- Comparisons: if food reminds them of jollof, suya, pepper soup etc., say so.

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

    # Persona block
    lines.append("## Persona")
    lines.append(f"Name: {persona.name}")
    if persona.age:
        lines.append(f"Age: {persona.age}")
    if persona.city:
        lines.append(f"From: {persona.city}")
    lines.append(f"Tone: {persona.tone}")
    lines.append(f"Historical avg rating they give: {persona.avg_star_rating:.1f} stars")
    if persona.food_preferences:
        lines.append(f"Food preferences: {', '.join(persona.food_preferences)}")
    lines.append(f"Bio: {persona.bio}")

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

    # Visit context
    if context:
        lines.append(f"\n## Visit context\n{context}")

    # Few-shot examples
    if examples:
        lines.append("\n## Real reviews from similar businesses (for style reference only)")
        lines.append("Do NOT copy these — use them to calibrate the voice and detail level.")
        for i, ex in enumerate(examples, 1):
            preview = ex["text"][:400].replace("\n", " ")
            lines.append(f"\nExample {i} (★{ex['stars']}): {preview}{'...' if len(ex['text']) > 400 else ''}")

    lines.append(
        "\n## Task\nWrite a review that this persona would leave for this business. "
        "Make it feel completely authentic — not generic. "
        "Return ONLY valid JSON matching the specified format."
    )

    return "\n".join(lines)
