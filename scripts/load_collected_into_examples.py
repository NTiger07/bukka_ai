"""
Inspect collected Nigerian review data from Chowdeck.

Usage:
    cd project_root
    python scripts/load_collected_into_examples.py
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "app" / "data"

SOURCE_FILES = {
    "Chowdeck":      DATA_DIR / "nigerian_reviews_chowdeck.json",
}


def _report(label: str, reviews: list[dict]):
    tones   = Counter(r["tone"] for r in reviews)
    regions = Counter(r["region"] for r in reviews)
    stars   = Counter(r["stars"] for r in reviews)

    print(f"\n{'─' * 54}")
    print(f"  {label}  ({len(reviews)} reviews)")
    print(f"{'─' * 54}")
    print(f"  Stars:    {dict(sorted(stars.items()))}")
    print(f"  Tones:    {dict(tones)}")
    print(f"  Regions:  {dict(regions)}")

    print("\n  Sample per tone:")
    for tone in ["expressive", "blunt", "casual", "formal", "sarcastic"]:
        sample = next((r for r in reviews if r["tone"] == tone), None)
        if sample:
            preview = sample["text"][:160].replace("\n", " ")
            ellipsis = "..." if len(sample["text"]) > 160 else ""
            print(f"\n  [{tone}] ★{sample['stars']} — {sample['business_name']}")
            print(f"    {preview}{ellipsis}")

    print("\n  Coverage gaps:")
    for star in range(1, 6):
        count = stars.get(star, 0)
        flag = "✓" if count >= 3 else "⚠ low"
        print(f"    ★{star}: {count}  {flag}")
    for region in ["yoruba", "igbo", "hausa", "edo", "general"]:
        count = regions.get(region, 0)
        flag = "✓" if count >= 2 else "⚠ low"
        print(f"    {region}: {count}  {flag}")


def main():
    any_found = False
    for label, path in SOURCE_FILES.items():
        if not path.exists():
            print(f"\n{label}: file not found ({path.name}) — run the collector script first.")
            continue
        any_found = True
        with open(path, encoding="utf-8") as f:
            reviews = json.load(f)
        _report(label, reviews)

    if not any_found:
        print("No collected data found. Run collect_chowdeck.py first.")


if __name__ == "__main__":
    main()
