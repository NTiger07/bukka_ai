"""
Yelp Dataset EDA for DSN x BCT LLM Agent Hackathon
Covers: rating distribution, review length/style, business categories,
        reviews-per-user distribution, and power users for persona building.
"""

import json
import os
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # headless
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

DATA_DIR = Path("yelp_dataset")
OUTPUT_DIR = Path("eda_output")
OUTPUT_DIR.mkdir(exist_ok=True)

# ── helpers ──────────────────────────────────────────────────────────────────

def stream_json(path: Path, limit: int | None = None):
    """Yield one JSON object per line (NDJSON format used by Yelp)."""
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f):
            if limit and i >= limit:
                break
            line = line.strip()
            if line:
                yield json.loads(line)


def save_fig(name: str):
    path = OUTPUT_DIR / f"{name}.png"
    plt.savefig(path, bbox_inches="tight", dpi=150)
    plt.close()
    print(f"  saved → {path}")


# ── 1. Business dataset ───────────────────────────────────────────────────────

def analyze_businesses():
    print("\n=== BUSINESSES ===")
    records = list(stream_json(DATA_DIR / "yelp_academic_dataset_business.json"))
    df = pd.DataFrame(records)

    print(f"Total businesses : {len(df):,}")
    print(f"Unique cities    : {df['city'].nunique():,}")
    print(f"Unique states    : {df['state'].nunique():,}")
    print(f"Stars range      : {df['stars'].min()} – {df['stars'].max()}")
    print(f"Open businesses  : {df['is_open'].sum():,}")

    # ── category counts
    cat_counter: Counter = Counter()
    for cats in df["categories"].dropna():
        for c in cats.split(", "):
            cat_counter[c.strip()] += 1

    top_cats = cat_counter.most_common(25)
    print("\nTop 25 business categories:")
    for cat, cnt in top_cats:
        print(f"  {cat:<40} {cnt:>7,}")

    cats_df = pd.DataFrame(top_cats, columns=["category", "count"])
    fig, ax = plt.subplots(figsize=(10, 7))
    ax.barh(cats_df["category"][::-1], cats_df["count"][::-1], color="steelblue")
    ax.set_xlabel("Number of businesses")
    ax.set_title("Top 25 Business Categories (Yelp)")
    save_fig("business_top_categories")

    # ── star distribution
    fig, ax = plt.subplots(figsize=(7, 4))
    df["stars"].value_counts().sort_index().plot(kind="bar", ax=ax, color="coral", edgecolor="black")
    ax.set_xlabel("Stars")
    ax.set_ylabel("Count")
    ax.set_title("Business Star Rating Distribution")
    save_fig("business_star_distribution")

    return df


# ── 2. User dataset ───────────────────────────────────────────────────────────

def analyze_users():
    print("\n=== USERS ===")
    records = list(stream_json(DATA_DIR / "yelp_academic_dataset_user.json"))
    df = pd.DataFrame(records)

    print(f"Total users            : {len(df):,}")
    print(f"review_count stats:\n{df['review_count'].describe().to_string()}")

    power_users = df[df["review_count"] >= 10]
    print(f"\nUsers with ≥10 reviews : {len(power_users):,}  ({100*len(power_users)/len(df):.1f}%)")
    print(f"Users with ≥50 reviews : {(df['review_count']>=50).sum():,}")
    print(f"Users with ≥100 reviews: {(df['review_count']>=100).sum():,}")

    # ── review count distribution (log-scale histogram)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    axes[0].hist(df["review_count"], bins=100, color="teal", edgecolor="none", log=True)
    axes[0].set_xlabel("Review count")
    axes[0].set_ylabel("Number of users (log)")
    axes[0].set_title("Reviews per User (log y-axis)")

    axes[1].hist(df[df["review_count"] <= 200]["review_count"], bins=50, color="teal", edgecolor="none")
    axes[1].set_xlabel("Review count (capped at 200)")
    axes[1].set_ylabel("Number of users")
    axes[1].set_title("Reviews per User (≤200, linear)")
    plt.tight_layout()
    save_fig("user_review_count_distribution")

    # ── average stars given by users
    print(f"\naverage_stars stats:\n{df['average_stars'].describe().to_string()}")
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.hist(df["average_stars"], bins=50, color="goldenrod", edgecolor="none")
    ax.set_xlabel("Average stars given by user")
    ax.set_ylabel("Number of users")
    ax.set_title("Distribution of User Average Star Ratings")
    save_fig("user_average_stars")

    # ── useful/funny/cool elite signal
    for col in ["useful", "funny", "cool"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # ── save power-user sample for persona building
    sample_cols = ["user_id", "name", "review_count", "average_stars", "fans", "elite"]
    available = [c for c in sample_cols if c in df.columns]
    power_sample = power_users[available].sort_values("review_count", ascending=False).head(500)
    power_sample.to_csv(OUTPUT_DIR / "power_users_sample.csv", index=False)
    print(f"\nPower-user sample (top 500) saved to {OUTPUT_DIR}/power_users_sample.csv")

    return df


# ── 3. Review dataset ─────────────────────────────────────────────────────────

def analyze_reviews(sample_size: int = 200_000):
    print(f"\n=== REVIEWS (sampling first {sample_size:,} records) ===")
    records = list(stream_json(DATA_DIR / "yelp_academic_dataset_review.json", limit=sample_size))
    df = pd.DataFrame(records)

    print(f"Records loaded         : {len(df):,}")
    print(f"Unique users in sample : {df['user_id'].nunique():,}")
    print(f"Unique businesses      : {df['business_id'].nunique():,}")

    # ── star rating distribution
    star_dist = df["stars"].value_counts().sort_index()
    print(f"\nStar distribution:\n{star_dist.to_string()}")

    fig, ax = plt.subplots(figsize=(7, 4))
    star_dist.plot(kind="bar", ax=ax, color=["#d62728","#ff7f0e","#bcbd22","#2ca02c","#1f77b4"],
                   edgecolor="black")
    ax.set_xlabel("Stars")
    ax.set_ylabel("Count")
    ax.set_title(f"Review Star Distribution (n={len(df):,})")
    ax.set_xticklabels([1,2,3,4,5], rotation=0)
    save_fig("review_star_distribution")

    # ── review text length
    df["text_len"] = df["text"].astype(str).str.len()
    df["word_count"] = df["text"].astype(str).str.split().str.len()

    print(f"\nReview length (chars):\n{df['text_len'].describe().to_string()}")
    print(f"\nReview length (words):\n{df['word_count'].describe().to_string()}")

    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    axes[0].hist(df["text_len"].clip(upper=3000), bins=80, color="mediumpurple", edgecolor="none")
    axes[0].set_xlabel("Character count (capped at 3000)")
    axes[0].set_ylabel("Reviews")
    axes[0].set_title("Review Text Length Distribution (chars)")

    axes[1].hist(df["word_count"].clip(upper=500), bins=80, color="mediumpurple", edgecolor="none")
    axes[1].set_xlabel("Word count (capped at 500)")
    axes[1].set_ylabel("Reviews")
    axes[1].set_title("Review Text Length Distribution (words)")
    plt.tight_layout()
    save_fig("review_text_length")

    # ── avg word count per star
    avg_wc = df.groupby("stars")["word_count"].mean().round(1)
    print(f"\nAvg word count per star rating:\n{avg_wc.to_string()}")

    fig, ax = plt.subplots(figsize=(6, 4))
    avg_wc.plot(kind="bar", ax=ax, color="mediumpurple", edgecolor="black")
    ax.set_xlabel("Stars")
    ax.set_ylabel("Average word count")
    ax.set_title("Average Review Length by Star Rating")
    ax.set_xticklabels([1,2,3,4,5], rotation=0)
    save_fig("review_avg_length_by_star")

    # ── review sample per star — handy for prompt engineering
    print("\nSample review per star rating:")
    for star in [1, 2, 3, 4, 5]:
        subset = df[df["stars"] == star]
        if len(subset) == 0:
            continue
        row = subset.sample(1, random_state=42).iloc[0]
        preview = str(row["text"])[:300].replace("\n", " ")
        print(f"\n  ★{star}  [{row['word_count']} words]  {preview}…")

    # ── useful/funny/cool vote distribution
    for col in ["useful", "funny", "cool"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    vote_cols = [c for c in ["useful","funny","cool"] if c in df.columns]
    if vote_cols:
        print(f"\nVote stats:\n{df[vote_cols].describe().to_string()}")

    # ── yearly review trend
    if "date" in df.columns:
        df["year"] = pd.to_datetime(df["date"], errors="coerce").dt.year
        yearly = df["year"].value_counts().sort_index().dropna()
        fig, ax = plt.subplots(figsize=(9, 4))
        yearly.plot(kind="bar", ax=ax, color="darkcyan", edgecolor="black")
        ax.set_xlabel("Year")
        ax.set_ylabel("Number of reviews")
        ax.set_title("Reviews per Year")
        plt.xticks(rotation=45)
        save_fig("review_yearly_trend")
        print(f"\nReviews by year:\n{yearly.to_string()}")

    return df


# ── 4. Tips dataset ───────────────────────────────────────────────────────────

def analyze_tips():
    print("\n=== TIPS ===")
    records = list(stream_json(DATA_DIR / "yelp_academic_dataset_tip.json"))
    df = pd.DataFrame(records)
    print(f"Total tips             : {len(df):,}")
    df["text_len"] = df["text"].astype(str).str.len()
    print(f"Tip length (chars):\n{df['text_len'].describe().to_string()}")

    print("\nSample tips:")
    for _, row in df.sample(5, random_state=7).iterrows():
        print(f"  [{row['text_len']} chars] {str(row['text'])[:200]}")

    return df


# ── 5. Cross-dataset join sanity check ───────────────────────────────────────

def cross_check(review_df: pd.DataFrame, business_df: pd.DataFrame):
    print("\n=== CROSS-DATASET SANITY CHECK ===")
    merged = review_df.merge(business_df[["business_id","name","categories","city","stars"]],
                             on="business_id", how="inner", suffixes=("_review","_business"))
    print(f"Review rows matched to business: {len(merged):,} / {len(review_df):,}")

    top_biz = merged.groupby("name").size().sort_values(ascending=False).head(15)
    print(f"\nMost-reviewed businesses (in sample):\n{top_biz.to_string()}")

    # ── category-level average review stars
    cat_stars = defaultdict(list)
    for _, row in merged.iterrows():
        if pd.isna(row["categories"]):
            continue
        for cat in str(row["categories"]).split(", "):
            cat_stars[cat.strip()].append(row["stars_review"])

    cat_avg = {k: round(np.mean(v), 3) for k, v in cat_stars.items() if len(v) >= 50}
    top_rated = sorted(cat_avg.items(), key=lambda x: x[1], reverse=True)[:15]
    lowest_rated = sorted(cat_avg.items(), key=lambda x: x[1])[:15]
    print("\nTop-rated categories (avg review stars, min 50 reviews):")
    for cat, avg in top_rated:
        print(f"  {cat:<40} {avg}")
    print("\nLowest-rated categories:")
    for cat, avg in lowest_rated:
        print(f"  {cat:<40} {avg}")


# ── main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Starting Yelp EDA...")
    print(f"Output directory: {OUTPUT_DIR.resolve()}\n")

    biz_df = analyze_businesses()
    user_df = analyze_users()
    review_df = analyze_reviews(sample_size=200_000)
    analyze_tips()
    cross_check(review_df, biz_df)

    print("\n✓ EDA complete. Check eda_output/ for charts and CSV.")
