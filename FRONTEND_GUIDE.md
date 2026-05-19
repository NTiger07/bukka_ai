# Frontend Integration Guide
**DSN x BCT LLM Agent Hackathon — Yelp AI Agents**

---

## Overview

The backend exposes two AI agent endpoints via a FastAPI server:

| Agent | What it does |
|-------|-------------|
| **Task A – Review Generator** | Give it a user persona + a business → get a realistic review + star rating |
| **Task B – Recommender** | Give it a user persona → get a ranked list of personalized business recommendations |

Both agents have a Nigerian cultural localization layer baked into the LLM — the tone, phrasing, and cultural references will reflect a Nigerian user's voice.

---

## Base URL

```
http://localhost:8000
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
      "wifi": false
    }
  },
  "context": "First visit, came for lunch with colleagues."
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `persona` | object | yes | See [Persona Object](#persona-object) |
| `business` | object | yes | See [Business Object](#business-object) |
| `context` | string | no | Free-text visit context, e.g. "Date night", "Solo lunch" |

**Response**
```json
{
  "review": "E be like say I enter this place with high hopes o! ...",
  "stars": 3,
  "word_count": 112,
  "sentiment": "mixed",
  "generation_time_ms": 1840
}
```

| Field | Type | Notes |
|-------|------|-------|
| `review` | string | Generated review text |
| `stars` | integer | 1–5 |
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
**Task B.** Given a user persona (+ optional history), return personalised recommendations.

Supports two modes — same-domain and cross-domain — selected automatically based on whether `filters.target_domain` is set.

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
    "categories": ["Restaurants", "Nightlife"],
    "min_stars": 3.5,
    "max_results": 10
  },
  "history": []
}
```

**Request body — cross-domain mode**

Set `filters.target_domain` to a different category than the user's history. The agent infers preference signals from `history` and applies them to the target domain.

```json
{
  "persona": {
    "name": "Emeka",
    "tone": "blunt",
    "bio": "Busy professional who values intensity and quality over price."
  },
  "filters": {
    "city": "Philadelphia",
    "state": "PA",
    "target_domain": "Spas & Beauty",
    "min_stars": 3.5,
    "max_results": 5
  },
  "history": [
    { "business_name": "Han Dynasty", "category": "Chinese, Szechuan", "stars": 5, "notes": "loved the intense heat" },
    { "business_name": "Zahav", "category": "Israeli, Mediterranean", "stars": 4, "notes": "grilled meats, bold flavors" },
    { "business_name": "Applebees", "category": "American", "stars": 2, "notes": "bland and forgettable" }
  ]
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `persona` | object | yes | See [Persona Object](#persona-object) |
| `filters.city` | string | no | Filter by city |
| `filters.state` | string | no | 2-letter state code |
| `filters.categories` | array | no | Leave empty for cross-category diversity |
| `filters.target_domain` | string | no | Triggers cross-domain mode. e.g. `"Spas & Beauty"`, `"Arts & Entertainment"`, `"Shopping"` |
| `filters.min_stars` | float | no | Default `3.0` |
| `filters.max_results` | integer | no | Default `10`, max `10` |
| `history` | array | no | Past visits — each needs `business_name`, `category`, `stars`. `notes` optional. |

**Response**
```json
{
  "recommendations": [
    {
      "rank": 1,
      "business_id": "abc123",
      "name": "Rescue Rituals Spa",
      "category": "Spas, Beauty & Spas",
      "city": "Philadelphia",
      "stars": 4.6,
      "review_count": 312,
      "reason": "Emeka's 5-star Szechuan habit signals a preference for bold intensity over gentle comfort — this spa's deep tissue focus mirrors that same unapologetic strength.",
      "match_score": 0.91
    }
  ],
  "persona_summary": "Emeka is a high-standards professional who gravitates toward intense, well-executed experiences.",
  "cross_domain_inference": "User consistently rates high-intensity, authentic experiences (Szechuan heat, grilled meats) and punishes blandness (2★ Applebees). In the spa domain: bold intensity → deep tissue over Swedish; authenticity → specialist boutiques over chain spas; value-conscious → mid-range with strong reviews.",
  "generation_time_ms": 2840
}
```

| Field | Type | Notes |
|-------|------|-------|
| `recommendations` | array | Ranked list |
| `recommendations[].reason` | string | References cross-domain inference directly when in cross-domain mode |
| `recommendations[].match_score` | float | 0–1 relevance score |
| `cross_domain_inference` | string \| null | Only present in cross-domain mode — show this to the user, it explains the reasoning |
| `persona_summary` | string | Agent's read of the persona — nice to show in the UI |
| `generation_time_ms` | integer | |

---

## Persona Object

Full schema for the `persona` field used in both endpoints.

```json
{
  "name": "string — display name",
  "age": "integer — optional",
  "city": "string — home city",
  "region": "yoruba | igbo | hausa | edo | general — Nigerian regional background, shapes voice",
  "tone": "expressive | blunt | formal | casual | sarcastic",
  "food_preferences": ["array of strings — optional"],
  "avg_star_rating": "float 1.0–5.0 — user's historical average rating",
  "bio": "string — free-text description of the user's personality/preferences"
}
```

Only `name` is strictly required. `bio` empty = cold-start mode. `region` significantly improves the Nigerian voice quality.

---

## Business Object

Used only in `/generate-review`.

```json
{
  "name": "string",
  "category": "string — comma-separated Yelp categories",
  "city": "string",
  "state": "string — 2-letter code",
  "stars": "float — business's Yelp rating",
  "attributes": {
    "price_range": "$ | $$ | $$$ | $$$$",
    "outdoor_seating": "boolean",
    "wifi": "boolean",
    "reservations": "boolean"
  }
}
```

`name` and `category` are required. `attributes` is optional but improves realism.

---

## UI Pages / Views

### Page 1 — Home
Simple landing with two entry points:
- **"Generate a Review"** → goes to Page 2
- **"Get Recommendations"** → goes to Page 3

### Page 2 — Review Generator

**Inputs (left panel or form)**
- Persona builder form (name, bio, tone dropdown, avg rating slider 1–5, food preferences as tags)
- Business search or manual entry (name, category, city, optional attributes)
- "Visit context" text field (optional)
- **Generate** button

**Output (right panel or below)**
- Star rating display (1–5 stars rendered visually)
- Review text in a styled card
- Sentiment badge (`positive` / `negative` / `mixed`)
- Word count + generation time in small text
- **Copy** button on the review card
- **Regenerate** button (resends same inputs)

**Loading state**
- Show a spinner with text: *"Your agent is writing..."*
- Typical latency: 1.5–3 seconds

### Page 3 — Recommender

**Inputs**
- Same persona builder (reuse the component from Page 2)
- Filters: city, state, categories (multi-select), minimum stars (slider)
- Max results selector (3 / 5 / 10)
- **Get Recommendations** button

**Output**
- Persona summary card at the top
- Ranked recommendation cards:
  - Business name + category + star rating
  - `reason` field in italics (this is the key LLM output)
  - Match score as a small progress bar or badge
- Loading text: *"Your agent is thinking..."*

---

## Error Handling

Always show errors to the user — never swallow them silently.

| Scenario | What to show |
|----------|-------------|
| `422` validation | Highlight the missing/invalid field inline |
| `500` / network error | Toast: *"Something went wrong. Please try again."* + Retry button |
| Slow response (>5s) | Show: *"Still working on it..."* |

---

## CORS

The backend will have CORS enabled for `localhost:3000` (or whichever port the frontend runs on). If you hit a CORS error, ping the backend dev to add your origin.

---

## Example `fetch` call (JavaScript)

```js
const response = await fetch('http://localhost:8000/generate-review', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    persona: {
      name: 'Chisom',
      bio: 'Loud foodie from Lagos who rates honestly.',
      tone: 'expressive',
      avg_star_rating: 3.5,
    },
    business: {
      name: 'The Cheesecake Factory',
      category: 'Restaurants, American (Traditional)',
      city: 'Philadelphia',
      state: 'PA',
      stars: 3.5,
    },
  }),
});

const data = await response.json();
console.log(data.review);   // generated text
console.log(data.stars);    // 1–5
```

---

## Notes for the Frontend Dev

- **Don't hardcode business data** — the business input should be free-form so judges can test with any business.
- **The `reason` field in recommendations is the money shot** — make it visually prominent.
- **Nigerian tone is intentional** — the reviews may include pidgin phrases or culturally specific references. This is a feature, not a bug.
- Keep the UI clean and fast. Judges will be clicking through multiple demos.
- Mobile-responsive is a nice-to-have, not required.

---

*Backend dev: Favour | Frontend integration questions → ping on the team channel*
