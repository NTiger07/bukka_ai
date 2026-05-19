"""
Loads the Yelp dataset into memory once at startup.

Businesses (~150k) are loaded in full — they're the backbone of Task B.
Reviews are streamed up to REVIEW_SAMPLE_LIMIT and indexed by business_id
so Task A can pull real few-shot examples for any business in the dataset.
A secondary category index lets us fall back to category-level examples when
the requested business isn't in the dataset.
"""

from __future__ import annotations

import json
import logging
import os
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def _stream_ndjson(path: Path, limit: int | None = None):
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f):
            if limit and i >= limit:
                break
            line = line.strip()
            if line:
                yield json.loads(line)


class YelpLoader:
    MAX_EXAMPLES_PER_BUSINESS = 5
    MAX_EXAMPLES_PER_CATEGORY = 20

    def __init__(self, data_dir: str | Path, review_limit: int = 100_000):
        self.data_dir = Path(data_dir)
        self.review_limit = review_limit

        self.businesses: pd.DataFrame = pd.DataFrame()
        # business_id → list of {"stars": int, "text": str}
        self.reviews_by_business: dict[str, list[dict]] = defaultdict(list)
        # category → list of {"stars": int, "text": str}
        self.reviews_by_category: dict[str, list[dict]] = defaultdict(list)

    # ── public ────────────────────────────────────────────────────────────────

    def load(self):
        logger.info("Loading Yelp businesses...")
        self._load_businesses()
        logger.info("Indexing Yelp reviews (limit=%d)...", self.review_limit)
        self._index_reviews()
        logger.info(
            "YelpLoader ready: %d businesses, %d businesses with review examples",
            len(self.businesses),
            len(self.reviews_by_business),
        )

    def search_businesses(
        self,
        city: str | None = None,
        state: str | None = None,
        categories: list[str] | None = None,
        min_stars: float = 3.0,
        limit: int = 20,
    ) -> list[dict]:
        """Filter and rank businesses for the recommendation pipeline."""
        df = self.businesses.copy()

        if city:
            df = df[df["city"].str.lower() == city.lower()]
        if state:
            df = df[df["state"].str.upper() == state.upper()]
        if min_stars:
            df = df[df["stars"] >= min_stars]
        if categories:
            mask = df["categories"].fillna("").apply(
                lambda cats: any(
                    c.lower() in cats.lower() for c in categories
                )
            )
            df = df[mask]

        if df.empty:
            return []

        # Quality score: stars weighted by review popularity (log scale)
        df = df.copy()
        df["_score"] = df["stars"] * np.log1p(df["review_count"].clip(lower=0))
        df = df.sort_values("_score", ascending=False).head(limit)

        return df[
            ["business_id", "name", "categories", "city", "state", "stars", "review_count"]
        ].to_dict(orient="records")

    def get_review_examples(
        self, business_id: str | None, categories: str | None, n: int = 3
    ) -> list[dict]:
        """
        Return up to n review examples for few-shot prompting.
        Priority: exact business match → category match → empty list.
        """
        if business_id and business_id in self.reviews_by_business:
            return self.reviews_by_business[business_id][:n]

        if categories:
            for cat in categories.split(", "):
                cat = cat.strip()
                if cat in self.reviews_by_category:
                    return self.reviews_by_category[cat][:n]

        return []

    def find_business_id(self, name: str, city: str | None = None) -> str | None:
        """Fuzzy-ish lookup: exact name match first, then case-insensitive."""
        df = self.businesses
        match = df[df["name"] == name]
        if city:
            city_match = match[match["city"].str.lower() == city.lower()]
            if not city_match.empty:
                return city_match.iloc[0]["business_id"]
        if not match.empty:
            return match.iloc[0]["business_id"]

        # Case-insensitive fallback
        match = df[df["name"].str.lower() == name.lower()]
        if not match.empty:
            return match.iloc[0]["business_id"]

        return None

    # ── private ───────────────────────────────────────────────────────────────

    def _load_businesses(self):
        path = self.data_dir / "yelp_academic_dataset_business.json"
        records = list(_stream_ndjson(path))
        self.businesses = pd.DataFrame(records)
        self.businesses["review_count"] = pd.to_numeric(
            self.businesses["review_count"], errors="coerce"
        ).fillna(0)
        self.businesses["stars"] = pd.to_numeric(
            self.businesses["stars"], errors="coerce"
        ).fillna(0)

    def _index_reviews(self):
        path = self.data_dir / "yelp_academic_dataset_review.json"
        biz_caps: dict[str, int] = defaultdict(int)
        cat_caps: dict[str, int] = defaultdict(int)

        biz_categories: dict[str, str] = {}
        if not self.businesses.empty:
            for _, row in self.businesses[["business_id", "categories"]].iterrows():
                if pd.notna(row["categories"]):
                    biz_categories[row["business_id"]] = row["categories"]

        for record in _stream_ndjson(path, limit=self.review_limit):
            bid = record.get("business_id", "")
            text = record.get("text", "").strip()
            stars = int(record.get("stars", 3))
            if not text:
                continue

            # Business-level index
            if biz_caps[bid] < self.MAX_EXAMPLES_PER_BUSINESS:
                self.reviews_by_business[bid].append({"stars": stars, "text": text})
                biz_caps[bid] += 1

            # Category-level index
            cats_str = biz_categories.get(bid, "")
            for cat in cats_str.split(", "):
                cat = cat.strip()
                if cat and cat_caps[cat] < self.MAX_EXAMPLES_PER_CATEGORY:
                    self.reviews_by_category[cat].append({"stars": stars, "text": text})
                    cat_caps[cat] += 1


# ── module-level singleton ────────────────────────────────────────────────────

_loader: YelpLoader | None = None


def get_loader() -> YelpLoader:
    global _loader
    if _loader is None:
        raise RuntimeError("YelpLoader not initialised — call init_loader() at startup")
    return _loader


def init_loader() -> YelpLoader:
    global _loader
    data_dir = os.getenv("YELP_DATA_DIR", "yelp_dataset")
    # If the path is relative, anchor it to the project root (two levels up from
    # this file: app/data/yelp_loader.py → app/ → project root)
    data_path = Path(data_dir)
    if not data_path.is_absolute():
        project_root = Path(__file__).resolve().parent.parent.parent
        data_path = project_root / data_dir
    review_limit = int(os.getenv("REVIEW_SAMPLE_LIMIT", "100000"))
    _loader = YelpLoader(data_dir=data_path, review_limit=review_limit)
    _loader.load()
    return _loader
