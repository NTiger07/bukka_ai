"""
Distils the full Yelp dataset into two slim files that can be committed to git
and deployed to Vercel:

  app/data/businesses.csv      (~8-12 MB)  — Task B candidate retrieval
  app/data/review_examples.json (~3-5 MB)  — Task A few-shot examples

Run once from the project root:
    python3 scripts/prepare_dataset.py
"""

from __future__ import annotations

import json
import csv
import os
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "yelp_dataset"
OUT_DIR = PROJECT_ROOT / "app" / "data"

BIZ_IN = DATA_DIR / "yelp_academic_dataset_business.json"
REV_IN = DATA_DIR / "yelp_academic_dataset_review.json"

BIZ_OUT = OUT_DIR / "businesses.csv"
REV_OUT = OUT_DIR / "review_examples.json"

# ── tunables ──────────────────────────────────────────────────────────────────
MIN_REVIEW_COUNT = 10          # skip rarely-reviewed businesses
MAX_REVIEWS_PER_BIZ = 3        # few-shot examples per business
MAX_REVIEWS_PER_CATEGORY = 15  # few-shot examples per category
REVIEW_TEXT_LIMIT = 400        # chars to keep per review (saves space)
REVIEW_STREAM_LIMIT = 500_000  # how many review records to scan


def stream_ndjson(path: Path, limit: int | None = None):
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f):
            if limit and i >= limit:
                break
            line = line.strip()
            if line:
                yield json.loads(line)


def build_businesses():
    print(f"Reading {BIZ_IN} ...")
    rows = []
    for rec in stream_ndjson(BIZ_IN):
        if not rec.get("is_open", 0):
            continue
        rc = int(rec.get("review_count") or 0)
        if rc < MIN_REVIEW_COUNT:
            continue
        rows.append({
            "business_id": rec.get("business_id", ""),
            "name": rec.get("name", ""),
            "categories": (rec.get("categories") or "").strip(),
            "city": rec.get("city", ""),
            "state": rec.get("state", ""),
            "stars": float(rec.get("stars") or 0),
            "review_count": rc,
        })

    print(f"  {len(rows):,} businesses after filtering (open, review_count >= {MIN_REVIEW_COUNT})")

    BIZ_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(BIZ_OUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["business_id", "name", "categories", "city", "state", "stars", "review_count"],
        )
        writer.writeheader()
        writer.writerows(rows)

    size_mb = BIZ_OUT.stat().st_size / 1_048_576
    print(f"  Wrote {BIZ_OUT}  ({size_mb:.1f} MB)")
    return {r["business_id"] for r in rows}


def build_review_examples(valid_biz_ids: set[str]):
    print(f"\nReading {REV_IN} (limit={REVIEW_STREAM_LIMIT:,}) ...")

    by_biz: dict[str, list[dict]] = defaultdict(list)
    by_cat: dict[str, list[dict]] = defaultdict(list)

    # Build business → categories map from existing CSV
    biz_cats: dict[str, str] = {}
    with open(BIZ_OUT, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            biz_cats[row["business_id"]] = row["categories"]

    biz_caps: dict[str, int] = defaultdict(int)
    cat_caps: dict[str, int] = defaultdict(int)

    scanned = 0
    for rec in stream_ndjson(REV_IN, limit=REVIEW_STREAM_LIMIT):
        scanned += 1
        bid = rec.get("business_id", "")
        if bid not in valid_biz_ids:
            continue
        text = (rec.get("text") or "").strip()[:REVIEW_TEXT_LIMIT]
        if not text:
            continue
        stars = int(rec.get("stars") or 3)
        entry = {"stars": stars, "text": text}

        if biz_caps[bid] < MAX_REVIEWS_PER_BIZ:
            by_biz[bid].append(entry)
            biz_caps[bid] += 1

        for cat in biz_cats.get(bid, "").split(", "):
            cat = cat.strip()
            if cat and cat_caps[cat] < MAX_REVIEWS_PER_CATEGORY:
                by_cat[cat].append(entry)
                cat_caps[cat] += 1

        if scanned % 100_000 == 0:
            print(f"  scanned {scanned:,} reviews ...")

    print(f"  Scanned {scanned:,} reviews")
    print(f"  by_biz entries: {len(by_biz):,}  |  by_cat entries: {len(by_cat):,}")

    out = {"by_biz": dict(by_biz), "by_cat": dict(by_cat)}
    with open(REV_OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, separators=(",", ":"))

    size_mb = REV_OUT.stat().st_size / 1_048_576
    print(f"  Wrote {REV_OUT}  ({size_mb:.1f} MB)")


if __name__ == "__main__":
    if not BIZ_IN.exists():
        print(f"ERROR: {BIZ_IN} not found. Run this script from the project root with the Yelp dataset in place.")
        sys.exit(1)

    valid_ids = build_businesses()
    if REV_IN.exists():
        build_review_examples(valid_ids)
    else:
        print(f"\nSkipping review examples — {REV_IN} not found.")

    print("\nDone. Commit app/data/businesses.csv and app/data/review_examples.json.")
