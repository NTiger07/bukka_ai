from __future__ import annotations

import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Make `from app.xxx import ...` work whether you run:
#   python3 app/main.py          (from project root)
#   python3 main.py              (from inside app/)
#   uvicorn app.main:app         (from project root)
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

load_dotenv(dotenv_path=_project_root / ".env")

from app.agents import recommend_agent, review_agent
from app.data.yelp_loader import init_loader
from app.models import RecommendRequest, RecommendResponse, ReviewRequest, ReviewResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up — loading Yelp dataset...")
    init_loader()
    logger.info("Dataset loaded. Server ready.")
    yield


app = FastAPI(
    title="Yelp AI Agents",
    description="Task A: review generation | Task B: personalized recommendations",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/generate-review", response_model=ReviewResponse)
def generate_review(request: ReviewRequest):
    """Task A — generate a realistic review + star rating for a business."""
    try:
        return review_agent.generate_review(
            persona=request.persona,
            business=request.business,
            context=request.context,
        )
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error in /generate-review")
        raise HTTPException(status_code=500, detail="Review generation failed") from e


@app.post("/recommend", response_model=RecommendResponse)
def recommend(request: RecommendRequest):
    """Task B — return personalised business recommendations for a persona."""
    try:
        return recommend_agent.get_recommendations(
            persona=request.persona,
            filters=request.filters,
            history=request.history,
            use_agent_pipeline=request.use_agent_pipeline,
        )
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error in /recommend")
        raise HTTPException(status_code=500, detail="Recommendation failed") from e


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8001, reload=True)
