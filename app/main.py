from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

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
        )
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error in /recommend")
        raise HTTPException(status_code=500, detail="Recommendation failed") from e
