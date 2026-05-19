"""
Nigerian review examples for few-shot prompting.

Two sources, merged at import time:
1. NIGERIAN_EXAMPLES — hand-written gold set (always present)
2. app/data/nigerian_reviews_collected.json — reviews scraped from Google Maps
   and Chowdeck via the collection scripts in scripts/. Optional: if the file
   doesn't exist the hand-written examples are used alone.

Used in review_agent.py — gold examples are injected BEFORE Yelp dataset
examples so Claude anchors on Nigerian voice first.
"""

from __future__ import annotations
import json
from pathlib import Path

NIGERIAN_EXAMPLES: list[dict] = [
    # ── 5-star ────────────────────────────────────────────────────────────────
    {
        "stars": 5,
        "tone": "expressive",
        "region": "yoruba",
        "category": "Restaurants",
        "text": (
            "Ehn ehn, so this is where they have been hiding the good food! "
            "I came here for my sister's birthday — a whole eight of us — and I was ready to "
            "be disappointed because restaurants abroad always carry big name without substance. "
            "But this place proved me wrong o. The jollof rice energy was present in their rice dishes — "
            "that smoky, well-seasoned depth wey you know means someone actually cooks with love. "
            "Service was warm, the waitress knew the menu inside out and she no try to rush us away "
            "even when we sat long after eating. For the price, e make sense. "
            "This kind place, I will drag everybody I know here. E don set."
        ),
    },
    {
        "stars": 5,
        "tone": "expressive",
        "region": "edo",
        "category": "Seafood",
        "text": (
            "My brother, I need you to hear me when I say this place exceeded every expectation. "
            "I ordered the grilled salmon thinking say it will be the usual oyibo dry fish situation — "
            "but Chei! The thing land on my table looking like it was seasoned by someone who "
            "understood pepper. Rich, fresh, properly cooked. Not the kind where you chew and chew "
            "and nothing is happening. My friend beside me ordered the lobster and she nearly shed tear. "
            "The staff dem were attentive without being in your face. "
            "And the price? For this quality? God is good. I have found my spot."
        ),
    },
    {
        "stars": 5,
        "tone": "formal",
        "region": "general",
        "category": "Fine Dining",
        "text": (
            "I attended a business dinner here and I must say the establishment delivered on every front. "
            "The ambiance struck the right balance — sophisticated without being cold. "
            "My colleagues and I ordered across the menu and the kitchen maintained consistency. "
            "The lamb was exceptional, properly rested and seasoned with intention. "
            "What impressed me most was the service: attentive, professional, and genuinely warm — "
            "the kind of warmth that reminds you of being well-received in a good Nigerian home. "
            "Not performative hospitality. For the calibre of food and experience, the pricing is justified. "
            "I will return and I would recommend without reservation."
        ),
    },
    {
        "stars": 5,
        "tone": "casual",
        "region": "hausa",
        "category": "Restaurants, American",
        "text": (
            "Wallahi this place is doing something right. I came in not expecting much — "
            "American food can be heavy and bland but this one surprised me. "
            "The ribs were well-seasoned, you could taste they marinated it properly. "
            "The staff were respectful and friendly, they greeted well and attended to us without making us feel like a burden. "
            "My family enjoyed it. The children were happy. The portions were generous — "
            "nobody left hungry, which for me is the real test. "
            "Allah ya kiyaye, I will bring more people here."
        ),
    },

    # ── 4-star ────────────────────────────────────────────────────────────────
    {
        "stars": 4,
        "tone": "expressive",
        "region": "yoruba",
        "category": "Restaurants, Chinese",
        "text": (
            "Okay so I enter this Chinese place skeptical because — let me be honest — "
            "the Chinese food I have tried before dey taste like they removed all the pepper "
            "before serving. But this one? E get something. The Szechuan dishes carry heat o, "
            "not suya-level but respectable. I compared the dan dan noodles to my mama's groundnut soup "
            "broth — not the same but the depth of flavour is there. "
            "Service was a bit slow when the place got busy but the staff smiled through it. "
            "Price is fair. I go return, but I will order the spicier options next time."
        ),
    },
    {
        "stars": 4,
        "tone": "casual",
        "region": "general",
        "category": "Bars, Nightlife",
        "text": (
            "Came here on a Friday with the work people and e was a solid night. "
            "The bar area was lively but not the kind of noise where you cannot hear the person "
            "next to you — that balance is hard to find. Drinks were priced well, "
            "the cocktail I ordered was not watered down which I appreciate because some places "
            "will charge you full price for coloured water. The DJ was playing good music, "
            "not too loud. Only thing is the bar got a bit slow around 11pm when it filled up. "
            "But overall? Good vibes. Would come back for a work hangout."
        ),
    },
    {
        "stars": 4,
        "tone": "blunt",
        "region": "igbo",
        "category": "Restaurants, Mediterranean",
        "text": (
            "Food is genuinely good. Hummus, grilled meats, the whole setup. "
            "The lamb skewers reminded me of suya — different spices but same spirit: "
            "flame, smoke, proper seasoning. I respect it. "
            "Service was fine, nothing exceptional, nobody went out of their way. "
            "Price is slightly high but for the quality of ingredients I can accept it. "
            "I subtracted one star because they ran out of two items I wanted to order. "
            "Sort your stock management and this is a five-star place."
        ),
    },
    {
        "stars": 4,
        "tone": "expressive",
        "region": "general",
        "category": "Brunch, American",
        "text": (
            "Sunday brunch with the girls and this place did not disappoint. "
            "The pancakes were thick and soft — I was not expecting to feel this way about pancakes "
            "but here we are. The eggs benedict were well-executed. "
            "Now the wait was long o, almost 25 minutes before someone took our order, "
            "but the waiter apologised genuinely and gave us complimentary juice while we waited — "
            "see that kind gesture is what turns a bad situation around. "
            "The bill was reasonable for the portion size. "
            "We will be back. Maybe on a less busy day."
        ),
    },

    # ── 3-star ────────────────────────────────────────────────────────────────
    {
        "stars": 3,
        "tone": "casual",
        "region": "general",
        "category": "Fast Food, Burgers",
        "text": (
            "It's okay na. Burger was decent, fries were fresh and hot which is the minimum I expect. "
            "Nothing about this place will make me write letter home but nothing offended me either. "
            "Service was fast — I was in and out in 15 minutes — which I actually appreciate "
            "because sometimes you just need to eat and go. "
            "Price is fair for what it is. "
            "I would come back if I am nearby and hungry, not my first choice but e fit do."
        ),
    },
    {
        "stars": 3,
        "tone": "expressive",
        "region": "igbo",
        "category": "Restaurants, Italian",
        "text": (
            "Nna, this pasta confused me. It was not bad but it was not memorable either. "
            "The sauce had potential — you could taste the tomatoes were good — "
            "but they underseasoned it. I kept thinking, one more round of salt and pepper "
            "and this thing would have been singing. "
            "The tiramisu at the end was actually the hero of the meal, properly done. "
            "Staff were pleasant. Place was clean and nicely decorated. "
            "For this price I expected the pasta to match the dessert. It did not. "
            "Chei. Come back stronger with the seasoning."
        ),
    },

    # ── 2-star ────────────────────────────────────────────────────────────────
    {
        "stars": 2,
        "tone": "blunt",
        "region": "igbo",
        "category": "Restaurants",
        "text": (
            "Cold food. That is the summary. "
            "I ordered the pasta, it arrived cold. I told the waiter. "
            "He looked at me like I said something offensive. Chei. "
            "They took it back, returned it five minutes later — still not properly hot. "
            "For what they are charging, temperature control is not optional. "
            "The ambiance is nice, I will give them that. "
            "But food quality and staff attitude brought this down to two stars. "
            "My money entered the wrong place today."
        ),
    },
    {
        "stars": 2,
        "tone": "sarcastic",
        "region": "general",
        "category": "Restaurants, American",
        "text": (
            "Wow. Just wow. I came here based on the hype and I have never felt so personally attacked "
            "by a plate of food in my life. "
            "The steak arrived overcooked — I said medium rare, not 'sole of a shoe'. "
            "When I raised it, the server explained that their chef 'cooks to well done for safety reasons'. "
            "My friend, I did not ask for their food philosophy. "
            "The sides were fine. Water was cold. "
            "I have found two stars hiding somewhere in this experience but I had to look very hard."
        ),
    },
    {
        "stars": 2,
        "tone": "expressive",
        "region": "yoruba",
        "category": "Restaurants",
        "text": (
            "See ehn, I carry high hope enter this place. Instagram was selling it well. "
            "But the real experience? Omo. "
            "We waited 45 minutes for our food. When it came the jollof rice was dry — "
            "dry like it was cooked yesterday and reheated without mercy. "
            "The chicken was tough. The pepper soup had no pepper in it — abeg what kind joke is that? "
            "The waiter was apologetic sha, I will not take that from him. "
            "But apology no make food taste better. "
            "Management needs to fix their kitchen before marketing on social media."
        ),
    },

    # ── 1-star ────────────────────────────────────────────────────────────────
    {
        "stars": 1,
        "tone": "blunt",
        "region": "general",
        "category": "Restaurants",
        "text": (
            "Do not come here. I will keep this short. "
            "Food was inedible — overcooked, underseasoned, served cold. "
            "When we complained, the manager argued with us instead of apologising. "
            "They charged full price for food that went back to the kitchen twice. "
            "The only reason this gets one star is because zero is not available. "
            "There are too many good restaurants to waste your time and money here."
        ),
    },
    {
        "stars": 1,
        "tone": "expressive",
        "region": "general",
        "category": "Service, Restaurant",
        "text": (
            "I want to cry as I type this review. "
            "My birthday dinner. I had planned this for weeks. "
            "Table was not ready despite a confirmed reservation. "
            "We stood by the door for 30 minutes while they 'sorted it out'. "
            "When we finally sat, two of our orders were wrong. "
            "The manager offered a 10% discount like that was supposed to fix ruined memories. "
            "Abeg keep your discount. I want my birthday back. "
            "This is not the kind of thing you do to people. Terrible."
        ),
    },
]


def get_examples_by_tone(tone: str, n: int = 3) -> list[dict]:
    """Return examples matching the given tone, falling back to general ones."""
    matches = [e for e in NIGERIAN_EXAMPLES if e["tone"] == tone]
    if len(matches) < n:
        others = [e for e in NIGERIAN_EXAMPLES if e["tone"] != tone]
        matches = matches + others
    return matches[:n]


def _load_file(filename: str) -> list[dict]:
    path = Path(__file__).parent / filename
    if not path.exists():
        return []
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


# Full pool: hand-written gold first (highest priority), then Chowdeck
ALL_EXAMPLES: list[dict] = (
    NIGERIAN_EXAMPLES
    + _load_file("nigerian_reviews_chowdeck.json")
)


def get_examples_by_stars(target_stars: float, n: int = 3) -> list[dict]:
    """Return examples closest to the target star rating."""
    return sorted(ALL_EXAMPLES, key=lambda e: abs(e["stars"] - target_stars))[:n]


def get_examples_by_region(region: str | None, tone: str, n: int = 2) -> list[dict]:
    """
    Return region-matched examples first, then tone-matched backfill.
    Hand-written gold examples take priority over scraped ones because they
    are already ordered first in ALL_EXAMPLES.
    """
    region_matches = [e for e in ALL_EXAMPLES if e.get("region") == region]
    tone_matches = [e for e in ALL_EXAMPLES if e["tone"] == tone and e not in region_matches]
    return (region_matches + tone_matches)[:n]
