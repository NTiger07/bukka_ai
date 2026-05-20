"""
Loads the Yelp dataset into memory once at startup.

Production / Vercel path:
  Reads from pre-processed slim files committed to the repo:
    app/data/businesses.csv        (~10 MB, 7 fields, open businesses only)
    app/data/review_examples.json  (~12 MB, sampled few-shot examples)

Local development path (fallback):
  If the slim files are absent, falls back to the full raw dataset at
  YELP_DATA_DIR (default: yelp_dataset/).  This path is never deployed.

Generate the slim files once with:
    python3 scripts/prepare_dataset.py
"""

from __future__ import annotations

import csv
import json
import logging
import os
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Slim files live next to this module inside app/data/
_MODULE_DIR = Path(__file__).resolve().parent
SLIM_BIZ_PATH = _MODULE_DIR / "businesses.csv"
SLIM_REV_PATH = _MODULE_DIR / "review_examples.json"


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
        self.reviews_by_business: dict[str, list[dict]] = defaultdict(list)
        self.reviews_by_category: dict[str, list[dict]] = defaultdict(list)

    # ── public ────────────────────────────────────────────────────────────────

    def load(self):
        if SLIM_BIZ_PATH.exists():
            logger.info("Loading slim businesses from %s ...", SLIM_BIZ_PATH)
            self._load_slim_businesses()
        else:
            biz_path = self.data_dir / "yelp_academic_dataset_business.json"
            if not biz_path.exists():
                logger.warning(
                    "No dataset found (tried %s and %s). "
                    "Run scripts/prepare_dataset.py to generate slim files. "
                    "Task B will return no candidates.",
                    SLIM_BIZ_PATH,
                    biz_path,
                )
                return
            logger.info("Loading full businesses from %s ...", biz_path)
            self._load_businesses()

        if SLIM_REV_PATH.exists():
            logger.info("Loading slim review examples from %s ...", SLIM_REV_PATH)
            self._load_slim_reviews()
        else:
            rev_path = self.data_dir / "yelp_academic_dataset_review.json"
            if rev_path.exists():
                logger.info("Indexing full reviews (limit=%d) ...", self.review_limit)
                self._index_reviews()
            else:
                logger.info("No review examples file found — Task A will use gold examples only.")

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
        diverse: bool = False,
    ) -> list[dict]:
        if self.businesses.empty:
            return []

        df = self.businesses.copy()

        if city:
            df = df[df["city"].str.lower() == city.lower()]
        if state:
            df = df[df["state"].str.upper() == state.upper()]
        if min_stars:
            df = df[df["stars"] >= min_stars]
        if categories:
            mask = df["categories"].fillna("").apply(
                lambda cats: any(c.lower() in cats.lower() for c in categories)
            )
            df = df[mask]

        if df.empty:
            return []

        df = df.copy()
        df["_score"] = df["stars"] * np.log1p(df["review_count"].clip(lower=0))

        if diverse and categories is None:
            df["_primary_cat"] = (
                df["categories"].fillna("Other").str.split(",").str[0].str.strip()
            )
            df = (
                df.groupby("_primary_cat", group_keys=False)
                .apply(lambda g: g.nlargest(3, "_score"))
                .sort_values("_score", ascending=False)
                .head(limit)
            )
        else:
            df = df.sort_values("_score", ascending=False).head(limit)

        return df[
            ["business_id", "name", "categories", "city", "state", "stars", "review_count"]
        ].to_dict(orient="records")

    def get_review_examples(
        self, business_id: str | None, categories: str | None, n: int = 3
    ) -> list[dict]:
        if business_id and business_id in self.reviews_by_business:
            return self.reviews_by_business[business_id][:n]
        if categories:
            for cat in categories.split(", "):
                cat = cat.strip()
                if cat in self.reviews_by_category:
                    return self.reviews_by_category[cat][:n]
        return []

    def find_business_id(self, name: str, city: str | None = None) -> str | None:
        if self.businesses.empty:
            return None
        df = self.businesses
        match = df[df["name"] == name]
        if city:
            city_match = match[match["city"].str.lower() == city.lower()]
            if not city_match.empty:
                return city_match.iloc[0]["business_id"]
        if not match.empty:
            return match.iloc[0]["business_id"]
        match = df[df["name"].str.lower() == name.lower()]
        if not match.empty:
            return match.iloc[0]["business_id"]
        return None

    # ── slim loaders (production) ─────────────────────────────────────────────

    def _load_slim_businesses(self):
        rows = []
        with open(SLIM_BIZ_PATH, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                row["stars"] = float(row["stars"])
                row["review_count"] = int(row["review_count"])
                rows.append(row)
        self.businesses = pd.DataFrame(rows)

    def _load_slim_reviews(self):
        with open(SLIM_REV_PATH, encoding="utf-8") as f:
            data = json.load(f)
        for bid, examples in data.get("by_biz", {}).items():
            self.reviews_by_business[bid] = examples
        for cat, examples in data.get("by_cat", {}).items():
            self.reviews_by_category[cat] = examples

    # ── full dataset loaders (local dev fallback) ─────────────────────────────

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

            if biz_caps[bid] < self.MAX_EXAMPLES_PER_BUSINESS:
                self.reviews_by_business[bid].append({"stars": stars, "text": text})
                biz_caps[bid] += 1

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
        logger.warning("get_loader() called before init_loader() — creating stub loader")
        _loader = YelpLoader(data_dir=Path("."), review_limit=0)
    return _loader


def init_loader() -> YelpLoader:
    global _loader
    data_dir = os.getenv("YELP_DATA_DIR", "yelp_dataset")
    data_path = Path(data_dir)
    if not data_path.is_absolute():
        project_root = Path(__file__).resolve().parent.parent.parent
        data_path = project_root / data_dir
    review_limit = int(os.getenv("REVIEW_SAMPLE_LIMIT", "100000"))
    _loader = YelpLoader(data_dir=data_path, review_limit=review_limit)
    _loader.load()
    return _loader
