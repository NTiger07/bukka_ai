# Bukka AI

Two FastAPI AI agents built on the Yelp Open Dataset with deep Nigerian cultural localisation.
Built for the DSN x BCT LLM Agent Hackathon — Team Sentinel.

- **Task A** (`POST /generate-review`) — Given a Nigerian user persona and a business, generate a realistic Yelp-style review with star rating
- **Task B** (`POST /recommend`) — Given a persona and optional visit history, return a ranked list of personalised business recommendations

---

## Project Structure

```
bukka_ai/
├── app/
│   ├── main.py                        # FastAPI app, lifespan startup, both endpoints
│   ├── models.py                      # Pydantic v2 request/response schemas
│   ├── agents/
│   │   ├── review_agent.py            # Task A orchestration
│   │   └── recommend_agent.py         # Task B orchestration (fast path + three-agent pipeline)
│   ├── prompts/
│   │   ├── review_prompts.py          # Task A system prompt + user prompt builder
│   │   ├── recommend_prompts.py       # Task B prompts for all three agents + fast path
│   │   └── nigerian_voice.py          # Regional voice profiles, sentence patterns, occasion taxonomy
│   └── data/
│       ├── yelp_loader.py             # YelpLoader singleton, search_businesses(), quality scoring
│       ├── nigerian_examples.py       # 15 hand-authored gold Nigerian review examples
│       └── nigerian_reviews_chowdeck.json  # 174 real reviews scraped from Chowdeck
├── scripts/
│   ├── collect_chowdeck.py            # Playwright scraper for Chowdeck reviews
│   └── load_collected_into_examples.py # Loads scraped reviews into the examples bank
├── yelp_dataset/                      # Yelp Open Dataset files (not committed — download separately)
│   ├── yelp_academic_dataset_business.json
│   ├── yelp_academic_dataset_review.json
│   └── ...
├── eda.py                             # Exploratory data analysis script
├── eda_output/                        # Charts and CSVs from EDA run
├── task_a_paper.tex                   # Task A technical paper (LaTeX)
├── task_b_paper.tex                   # Task B technical paper (LaTeX)
├── vercel.json                        # Vercel serverless deployment config
├── requirements.txt
└── .env.example
```

---

## Setup

### 1. Clone and install

```bash
git clone <repo-url>
cd bukka_ai
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Environment variables

```bash
cp .env.example .env
# Fill in:
#   ANTHROPIC_API_KEY   — your Anthropic API key
#   YELP_DATA_DIR       — path to the yelp_dataset/ directory (default: yelp_dataset)
#   REVIEW_SAMPLE_LIMIT — how many reviews to index at startup (default: 10000)
#   CLAUDE_MODEL        — Claude model ID (default: claude-haiku-4-5-20251001)
```

### 3. Prepare the dataset

The app uses two slim files committed to the repo that are generated from the full Yelp dataset:

| File | Size | Purpose |
|---|---|---|
| `app/data/businesses.csv` | ~10 MB | Task B candidate retrieval |
| `app/data/review_examples.json` | ~12 MB | Task A few-shot examples |

**Production / Vercel (default):** `YelpLoader` reads these slim files automatically at startup — no raw Yelp data needed.

**Local development (fallback):** If the slim files are absent, the loader falls back to the full raw Yelp JSON files at `YELP_DATA_DIR` (default: `yelp_dataset/`). Download the [Yelp Open Dataset](https://www.yelp.com/dataset), place the files there, and the server will load directly from them.

To regenerate the slim files from a fresh Yelp download (run once from the project root):

```bash
python3 scripts/prepare_dataset.py
```

This script streams `yelp_academic_dataset_business.json` and `yelp_academic_dataset_review.json`, filters to open businesses with ≥10 reviews, and writes the two slim output files. Commit the results — they replace the need to ship the full multi-GB dataset.

### 4. Run the server

```bash
python3 app/main.py
# or
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

Interactive API docs available at `http://localhost:8001/docs`.

---

## Endpoints

### `GET /health`

```json
{ "status": "ok" }
```

---

### `POST /generate-review` — Task A

Generates a realistic Nigerian-voice Yelp review for a given persona visiting a business.

**Request**

```json
{
  "persona": {
    "name": "Temi",
    "age": 28,
    "city": "Lagos",
    "region": "yoruba",
    "tone": "casual",
    "food_preferences": ["jollof rice", "grilled fish"],
    "avg_star_rating": 4.0,
    "bio": "Loves trying new spots with friends, big on ambience and service"
  },
  "business": {
    "name": "Cactus Restaurant",
    "category": "Nigerian, Continental",
    "city": "Victoria Island",
    "state": "Lagos",
    "stars": 4.2
  },
  "context": "Birthday dinner with close friends"
}
```

**Response**

```json
{
  "review": "So we came here for my friend's birthday and I have to say...",
  "stars": 4,
  "word_count": 112,
  "sentiment": "positive",
  "generation_time_ms": 1340
}
```

**`region` values:** `yoruba` | `igbo` | `hausa` | `edo` | `general`

**`tone` values:** `casual` | `formal` | `expressive` | `blunt`

---

### `POST /recommend` — Task B

Returns a ranked list of personalised business recommendations. Supports cold-start users, cross-domain recommendations, and an optional three-agent pipeline for richer reasoning.

**Request**

```json
{
  "persona": {
    "name": "Emeka",
    "age": 34,
    "region": "igbo",
    "tone": "blunt",
    "avg_star_rating": 4.0,
    "bio": "Business consultant, eats out 4-5 times a week, no patience for mediocrity"
  },
  "filters": {
    "city": "Philadelphia",
    "state": "PA",
    "min_stars": 3.5,
    "max_results": 5
  },
  "history": [
    { "business_name": "Amara Kitchen", "category": "Nigerian", "stars": 5, "notes": "Bold pepper soup, felt at home" },
    { "business_name": "Generic Diner", "category": "American", "stars": 2, "notes": "Bland and overpriced" }
  ],
  "use_agent_pipeline": false
}
```

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
      "reason": "Award-winning hummus and wood-roasted meats match his demand for bold, unapologetic flavour.",
      "match_score": 0.94
    }
  ],
  "persona_summary": "Emeka is a results-driven Igbo professional who expects bold, high-quality food.",
  "preference_profile": null,
  "cross_domain_inference": null,
  "generation_time_ms": 1143
}
```

**Key request fields**

| Field | Type | Default | Purpose |
|---|---|---|---|
| `persona.region` | string | — | Cultural voice: `yoruba`, `igbo`, `hausa`, `edo`, `general` |
| `persona.avg_star_rating` | float | — | Price sensitivity signal |
| `persona.bio` | string | `""` | Empty = cold-start |
| `filters.city` / `state` | string | null | Geographic scope |
| `filters.min_stars` | float | `3.0` | Quality floor |
| `filters.max_results` | int | `10` | Aligned with NDCG@10 |
| `filters.target_domain` | string | null | Triggers cross-domain mode |
| `history[].stars` | int | — | User-assigned rating for past visit |
| `use_agent_pipeline` | bool | `false` | `true` = three-agent pipeline with auditable reasoning |

**Cross-domain example** — set `filters.target_domain` to recommend in a different category than the user's history (e.g., history in Restaurants, recommend Nightlife). The three-agent pipeline's Domain Translator agent explicitly maps preference signals across domains.

---

## Architecture

### Task A: Review Generation

```
Persona + Business + Context
        |
        v
Nigerian Gold Examples (2, by region+tone)
+ Yelp dataset examples (2, business-level then category fallback)
        |
        v
claude-sonnet-4-6  (system prompt cached)
        |
        v
ReviewResponse { review, stars, sentiment, word_count, generation_time_ms }
```

The system prompt enforces 80-150 word reviews, JSON output, and five Nigerian cultural signals: value consciousness, service sensitivity, expressiveness, social lens, and Pidgin naturalism. Star ratings are anchored to the persona's historical average.

### Task B: Recommendation Pipeline

```
Persona + Filters + History
        |
        v
YelpLoader.search_businesses()    (up to 20 candidates)
score = stars × log(1 + review_count)
        |
        v
Cold-start detection
(no bio + no food_preferences + no history)
        |
        v
use_agent_pipeline = false?
  └─ Fast path: single Claude call with inline 3-step reasoning scaffold

use_agent_pipeline = true?
  ├─ Cold-start:             Agent 3 only           (1 API call)
  ├─ Warm, same domain:      Agent 1 → Agent 3      (2 API calls)
  └─ Warm, cross-domain:     Agent 1 → 2 → Agent 3  (3 API calls)
```

- **Agent 1 (Preference Analyst):** extracts structured preference profile from persona + history
- **Agent 2 (Domain Translator):** maps source-domain signals to the target domain (cross-domain only)
- **Agent 3 (Ranker):** ranks all candidates with per-business `reason` and `match_score`

---

## Nigerian Localisation

All prompts carry explicit Nigerian cultural context across all five supported regions.

- **Regional voice profiles** — Yoruba, Igbo, Hausa, Edo, general; each with distinct linguistic cadence and cultural emphasis
- **Sentence pattern library** — 20 patterns across 5 categories: openers, food comparisons, service observations, value assessments, and verdicts
- **Occasion taxonomy** — 9 entries including birthday chops, owambe, office hangout, first date, Detty December, and business lunch
- **Gold example set** — 15 hand-authored Nigerian-voice reviews + 174 real reviews scraped from Chowdeck, loaded by region and tone

---

## Deployment (Vercel)

The app is configured for Vercel Python serverless via `vercel.json`. Set the following environment variables in your Vercel project settings:

```
ANTHROPIC_API_KEY
YELP_DATA_DIR
REVIEW_SAMPLE_LIMIT
CLAUDE_MODEL
```

The Yelp dataset files must be bundled with the deployment or mounted via a storage integration. Note that cold-start time depends on `REVIEW_SAMPLE_LIMIT` — keep it at `10000` or lower for serverless environments.

---

## Papers

- [task_a_paper.tex](task_a_paper.tex) — Full technical paper for Task A (review generation)
- [task_b_paper.tex](task_b_paper.tex) — Full technical paper for Task B (recommendation system)

Compile with `pdflatex` (requires `tikz`, `booktabs`, `tabularx`).

```bash
pdflatex task_a_paper.tex
pdflatex task_b_paper.tex
```
