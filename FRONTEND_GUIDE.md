# Bukka AI — Frontend Integration Guide

---

## Overview

The backend exposes two AI agent endpoints via a FastAPI server:

| Agent | Endpoint | What it does |
|-------|----------|-------------|
| **Task A – Review Generator** | `POST /generate-review` | Persona + business → realistic review + star rating |
| **Task B – Recommender** | `POST /recommend` | Persona + optional history → ranked business recommendations |

Both agents have a Nigerian cultural localisation layer — tone, phrasing, and cultural references reflect a Nigerian user's voice.

---

## Base URL

```
https://bukka-ai.vercel.app/
```

All endpoints return `application/json`. All request bodies are `application/json`.

---

## Endpoints

### `GET /health`

Quick liveness check.

**Response**
```json
{ "status": "ok" }
```

---

### `POST /generate-review`

**Task A.** Given a user persona and a business, generate a realistic review with a star rating.

**Request body**
```json
{
  "persona": {
    "name": "Chisom",
    "age": 28,
    "city": "Lagos",
    "region": "igbo",
    "tone": "expressive",
    "food_preferences": ["spicy food", "local cuisine"],
    "avg_star_rating": 3.8,
    "bio": "A foodie who is very vocal about bad service and loves recommending hidden gems."
  },
  "business": {
    "name": "The Cheesecake Factory",
    "category": "Restaurants, American (Traditional)",
    "city": "Philadelphia",
    "state": "PA",
    "stars": 3.5,
    "attributes": {
      "price_range": "$$",
      "outdoor_seating": true,
      "wifi": false,
      "reservations": false
    }
  },
  "context": "First visit, came for lunch with colleagues."
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `persona` | object | yes | See [Persona Object](#persona-object) |
| `business` | object | yes | See [Business Object](#business-object) |
| `context` | string | no | Free-text visit context e.g. "Date night", "Solo lunch" |

**Response**
```json
{
  "review": "E be like say I enter this place with high hopes o!...",
  "stars": 3,
  "word_count": 112,
  "sentiment": "mixed",
  "generation_time_ms": 1840
}
```

| Field | Type | Notes |
|-------|------|-------|
| `review` | string | Generated review text (80–150 words) |
| `stars` | integer | 1–5, anchored to persona's `avg_star_rating` |
| `word_count` | integer | |
| `sentiment` | string | `"positive"`, `"negative"`, `"mixed"` |
| `generation_time_ms` | integer | LLM latency in ms |

**Error responses**

| Status | Meaning |
|--------|---------|
| `422` | Validation error — check required fields |
| `500` | LLM call failed — show a retry button |

---

### `POST /recommend`

**Task B.** Given a user persona and optional visit history, return personalised business recommendations.

Supports three modes selected automatically by the request:
- **Cold-start** — no bio, no food preferences, no history: ranks by quality + Nigerian cultural appeal
- **Standard** — warm user, same domain as history
- **Cross-domain** — set `filters.target_domain` to recommend in a different category than the user's history

**Request body — standard mode**
```json
{
  "persona": {
    "name": "Emeka",
    "age": 34,
    "city": "Philadelphia",
    "region": "igbo",
    "tone": "blunt",
    "food_preferences": ["suya", "grilled meats", "seafood"],
    "avg_star_rating": 4.2,
    "bio": "Busy professional, values speed and quality. Hates pretentious restaurants."
  },
  "filters": {
    "city": "Philadelphia",
    "state": "PA",
    "min_stars": 3.5,
    "max_results": 10
  },
  "history": [
    { "business_name": "Amara Kitchen", "category": "Nigerian", "stars": 5, "notes": "Bold pepper soup, felt at home" },
    { "business_name": "Generic Diner", "category": "American", "stars": 2, "notes": "Bland and overpriced" }
  ],
  "use_agent_pipeline": false
}
```

**Request body — cross-domain mode**

Set `filters.target_domain` to a different category than the user's history. The agent infers preference signals from `history` and maps them to the target domain.

```json
{
  "persona": {
    "name": "Chisom",
    "age": 29,
    "region": "igbo",
    "tone": "expressive",
    "avg_star_rating": 4.3,
    "bio": "Loves fine dining and curated experiences, hates chaotic environments"
  },
  "filters": {
    "city": "Philadelphia",
    "state": "PA",
    "target_domain": "Nightlife",
    "min_stars": 3.5,
    "max_results": 5
  },
  "history": [
    { "business_name": "Lacroix", "category": "Fine Dining, French", "stars": 5, "notes": "Impeccable service, perfect atmosphere" },
    { "business_name": "The Noisy Sports Bar", "category": "Bars, Sports Bars", "stars": 2, "notes": "Couldn't hear myself think" }
  ],
  "use_agent_pipeline": true
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `persona` | object | yes | See [Persona Object](#persona-object) |
| `filters.city` | string | no | Filter by city |
| `filters.state` | string | no | 2-letter state code |
| `filters.categories` | array | no | Leave empty for cross-category diversity |
| `filters.target_domain` | string | no | Triggers cross-domain mode e.g. `"Nightlife"`, `"Spas"`, `"Shopping"` |
| `filters.min_stars` | float | no | Default `3.0` |
| `filters.max_results` | integer | no | Default `10`, max `10` |
| `history` | array | no | Past visits. Each item needs `business_name`, `category`, `stars`. `notes` optional. |
| `use_agent_pipeline` | boolean | no | Default `false`. `true` = three-agent pipeline with auditable reasoning (slower, richer output). `false` = single fast call. |

**Response**
```json
{
  "recommendations": [
    {
      "rank": 1,
      "business_id": "zahav-philadelphia-pa",
      "name": "Zahav",
      "category": "Israeli, Mediterranean",
      "city": "Philadelphia",
      "stars": 4.5,
      "review_count": 3812,
      "reason": "Award-winning hummus and wood-roasted meats match his demand for bold, unapologetic flavour; near-flawless service record means no wasted time.",
      "match_score": 0.94
    }
  ],
  "persona_summary": "Emeka is a results-driven Igbo professional who expects bold, high-quality food and has zero tolerance for mediocrity.",
  "preference_profile": "Values: bold flavours, attentive service, high quality-to-price ratio. Avoids: bland cooking, slow or dismissive staff. Price sensitivity: mid-range to premium.",
  "cross_domain_inference": null,
  "generation_time_ms": 1143
}
```

| Field | Type | Notes |
|-------|------|-------|
| `recommendations` | array | Ranked list, up to `max_results` items |
| `recommendations[].rank` | integer | Position in ranked list |
| `recommendations[].reason` | string | Why this business suits this persona — the key LLM output |
| `recommendations[].match_score` | float | 0.0–1.0 relevance score |
| `persona_summary` | string | 1–2 sentence read of the persona — good to show in UI |
| `preference_profile` | string \| null | Agent 1 output (what the user values). Only populated when `use_agent_pipeline: true` and user is not cold-start. |
| `cross_domain_inference` | string \| null | Agent 2 output (how signals translate across domains). Only populated in cross-domain mode. |
| `generation_time_ms` | integer | Total latency in ms |

**Latency guide**

| Mode | Typical latency |
|------|----------------|
| Fast path (single call) | 0.9–1.5s |
| Pipeline, warm same-domain (2 calls) | 2–3s |
| Pipeline, cross-domain (3 calls) | 3–4s |

---

## Persona Object

Full schema for the `persona` field used in both endpoints.

```json
{
  "name": "string — display name (required)",
  "age": "integer — optional",
  "city": "string — home city, optional",
  "region": "yoruba | igbo | hausa | edo | general",
  "tone": "expressive | blunt | formal | casual | sarcastic",
  "food_preferences": ["array of strings — optional"],
  "avg_star_rating": "float 1.0–5.0, default 3.5",
  "bio": "string — free-text personality/preferences. Empty string = cold-start."
}
```

Only `name` is strictly required. `region` significantly improves Nigerian voice quality. Empty `bio` triggers cold-start mode in the recommender.

---

## Business Object

Used only in `/generate-review`.

```json
{
  "name": "string (required)",
  "category": "string — comma-separated Yelp categories (required)",
  "city": "string — optional",
  "state": "string — 2-letter code, optional",
  "stars": "float 1.0–5.0 — business Yelp rating, optional",
  "attributes": {
    "price_range": "$ | $$ | $$$ | $$$$",
    "outdoor_seating": "boolean",
    "wifi": "boolean",
    "reservations": "boolean"
  }
}
```

`name` and `category` are required. `attributes` is optional but improves realism in the generated review.

---

## UI Pages / Views

### Page 1 — Home

Simple landing with two entry points:
- **"Generate a Review"** → Page 2
- **"Get Recommendations"** → Page 3

### Page 2 — Review Generator

**Inputs**
- Persona form: name, bio (textarea), tone (dropdown), region (dropdown), avg rating (slider 1–5), food preferences (tag input)
- Business form: name, category, city, state, Yelp stars, optional attributes (price range, outdoor seating, wifi)
- "Visit context" text field (optional)
- **Generate** button

**Output**
- Star rating displayed visually (1–5 filled stars)
- Review text in a styled card
- Sentiment badge (`positive` / `negative` / `mixed`)
- Word count + generation time in small text
- **Copy** button on the review card
- **Regenerate** button (resends same inputs)

**Loading state:** spinner with *"Your agent is writing..."* — typical wait 1.5–3s

### Page 3 — Recommender

**Inputs**
- Same persona builder (reuse component from Page 2)
- Filters: city, state, min stars (slider), max results (3 / 5 / 10 selector)
- Target domain field (optional — text input, e.g. "Nightlife", "Spas", "Shopping")
- History section: add/remove past visits (business name, category, stars 1–5, optional notes)
- **Agent pipeline toggle** (`use_agent_pipeline`) — default off. When on, label it "Deep reasoning mode" and warn *"Takes 3–4s but shows full reasoning"*
- **Get Recommendations** button

**Output**
- `persona_summary` card at the top
- If `preference_profile` is not null: show as a collapsible "What the agent learned about you" card
- If `cross_domain_inference` is not null: show as a highlighted "Cross-domain reasoning" card — this is the interesting bit
- Ranked recommendation cards:
  - Business name + category + city + star rating
  - `reason` in italics — make this visually prominent
  - `match_score` as a small progress bar or badge
- Loading text: *"Your agent is thinking..."*

---

## Error Handling

Always surface errors to the user — never swallow them silently.

| Scenario | What to show |
|----------|-------------|
| `422` validation | Highlight the missing/invalid field inline |
| `500` / network error | Toast: *"Something went wrong. Please try again."* + Retry button |
| Response takes >5s | Show: *"Still working on it..."* |

---

## CORS

CORS is enabled for all origins (`*`) in development. If you hit a CORS error in staging or production, add your origin to the allowed list in `app/main.py`.

---

## Example `fetch` calls (JavaScript)

**Task A — generate a review**
```js
const res = await fetch('http://localhost:8001/generate-review', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    persona: {
      name: 'Chisom',
      region: 'igbo',
      tone: 'expressive',
      avg_star_rating: 3.8,
      bio: 'Loud foodie from Lagos who rates honestly.',
    },
    business: {
      name: 'The Cheesecake Factory',
      category: 'Restaurants, American (Traditional)',
      city: 'Philadelphia',
      state: 'PA',
      stars: 3.5,
    },
    context: 'Lunch with colleagues',
  }),
});
const data = await res.json();
console.log(data.review);   // generated text
console.log(data.stars);    // 1–5
```

**Task B — recommendations (fast path)**
```js
const res = await fetch('http://localhost:8001/recommend', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    persona: {
      name: 'Emeka',
      region: 'igbo',
      tone: 'blunt',
      avg_star_rating: 4.2,
      bio: 'Busy professional, values quality, hates mediocrity.',
    },
    filters: { city: 'Philadelphia', state: 'PA', min_stars: 3.5, max_results: 5 },
    history: [
      { business_name: 'Amara Kitchen', category: 'Nigerian', stars: 5 },
    ],
    use_agent_pipeline: false,
  }),
});
const data = await res.json();
console.log(data.recommendations);      // ranked list
console.log(data.persona_summary);      // agent's read of the persona
console.log(data.preference_profile);   // null on fast path
```

**Task B — cross-domain with pipeline**
```js
const res = await fetch('http://localhost:8001/recommend', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    persona: {
      name: 'Chisom',
      region: 'igbo',
      tone: 'expressive',
      avg_star_rating: 4.3,
      bio: 'Loves fine dining and curated experiences.',
    },
    filters: { city: 'Philadelphia', state: 'PA', target_domain: 'Nightlife', max_results: 5 },
    history: [
      { business_name: 'Lacroix', category: 'Fine Dining, French', stars: 5, notes: 'Impeccable service' },
      { business_name: 'The Noisy Sports Bar', category: 'Bars', stars: 2 },
    ],
    use_agent_pipeline: true,
  }),
});
const data = await res.json();
console.log(data.cross_domain_inference);  // shows how restaurant prefs map to nightlife
console.log(data.preference_profile);      // Agent 1 structured profile
console.log(data.recommendations);         // cocktail bars, not clubs
```

---

## Notes for the Frontend Dev

- **Port is 8001**, not 8000.
- **`reason` is the money shot** — make it the most visually prominent text on each recommendation card.
- **`cross_domain_inference` is interesting to show** — when present, it reveals the full cross-domain reasoning chain. Put it above the results list.
- **`preference_profile` is nice but secondary** — collapsible is fine.
- **`use_agent_pipeline` adds real latency** — make the toggle clearly labelled and the loading state obvious.
- **Nigerian tone is intentional** — pidgin phrases and culturally specific references in reviews are a feature, not a bug. Don't try to clean them up.
- **Don't hardcode business data** — the business input in Page 2 should be free-form so judges can test with any business.
- Keep the UI clean. Judges will be clicking through multiple demos.

---

*Bukka AI — Backend: Favour | Frontend integration questions → ping on the team channel*
