"""
Collect Nigerian restaurant reviews from Chowdeck using Playwright.

Two-phase approach:
  Phase 1 — scrape chowdeck.com/store/restaurants to discover restaurant URLs
            (each card is an <a href="/store/{area}/restaurants/{slug}">)
  Phase 2 — visit each restaurant page, click the ratings arrow to open the
            Radix UI dialog, and extract review cards

Review card structure inside the dialog:
  div.py-6.border-b (one per review)
    div.flex.items-center > svg[fill="#FFC501"] × N  → star count
    p.mt-3.text-sm.text-black                        → review text

Usage:
    pip install playwright
    playwright install chromium
    cd project_root
    python scripts/collect_chowdeck.py

Output:
    app/data/nigerian_reviews_chowdeck.json
"""

from __future__ import annotations

import json
import time
from pathlib import Path

OUTPUT_PATH = Path(__file__).parent.parent / "app" / "data" / "nigerian_reviews_chowdeck.json"

BASE_URL = "https://chowdeck.com"

# Paths extracted directly from the listing page HTML.
# Individual restaurant pages load without location selection.
# Add more by visiting chowdeck.com, picking a restaurant, copying the URL path.
RESTAURANT_PATHS = [
    "/store/unilag/restaurants/freyvouritefoodsuniversity-of-lagosf66p64",
    "/store/alagomeji/restaurants/the-jollof-shop-by-ndiilicious-alagomejip383xb",
    "/store/unilag/restaurants/yem-yem-supermarketyabamlrk8d",
    "/store/unilag/restaurants/item-7-(go)-surulereyaba2s3t6a",
    "/store/unilag/restaurants/cafe-one-yabaakokac2e1rj",
    "/store/unilag/restaurants/ay-pizza",
]

MAX_RESTAURANTS = 30
MIN_REVIEWS = 1


# ── tone / region inference ───────────────────────────────────────────────────

def _infer_tone(text: str) -> str:
    t = text.lower()
    if any(w in t for w in ["terrible", "awful", "worst", "avoid", "waste", "horrible",
                             "never again", "rubbish", "nonsense", "disappointed",
                             "do not", "don't", "stay away", "poor", "bad experience"]):
        return "blunt"
    if any(w in t for w in ["!!", "love", "amazing", "abeg", "mehn", "omo", "chai", "ehn",
                             "wow", "excellent", "outstanding", "fantastic", "obsessed",
                             "best ever", "absolutely", "blown away", "incredible", "so good"]):
        return "expressive"
    if any(w in t for w in ["however", "overall", "recommend", "establishment", "would suggest",
                             "consistently", "professional", "quality", "experience", "commend",
                             "exceeded", "satisfaction", "efficient", "appreciate"]):
        return "formal"
    return "casual"


def _infer_region(text: str) -> str:
    t = text.lower()
    if any(w in t for w in ["ehn", "sha", "abeg", "abi", "oya", "nah", "ehen",
                             "jare", "na wa", "wetin", "e don", "e be like"]):
        return "yoruba"
    if any(w in t for w in ["chei", "nna", "chai", "biko", "nna men", "tufiakwa"]):
        return "igbo"
    if any(w in t for w in ["wallahi", "kai", "dan allah", "in sha allah", "mashallah"]):
        return "hausa"
    return "general"




# ── phase 2: open reviews dialog & extract ────────────────────────────────────

def _open_ratings_popup(page) -> bool:
    """
    Click the ratings trigger button (Radix UI dialog trigger) to open
    the 'Ratings and Reviews' modal on a restaurant page.
    """
    # Primary: any button with aria-haspopup="dialog" that is NOT inside an
    # already-open dialog (the Sort button inside the popup also has this attr).
    opened = page.evaluate("""
        () => {
            const triggers = [...document.querySelectorAll('button[aria-haspopup="dialog"]')];
            for (const btn of triggers) {
                if (btn.closest('[role="dialog"]')) continue;
                btn.click();
                return true;
            }
            return false;
        }
    """)

    if opened:
        time.sleep(1.8)
        dialog = page.query_selector('[role="dialog"]')
        if dialog:
            heading = dialog.query_selector("h2")
            if heading and "rating" in heading.inner_text().lower():
                return True
            # Wrong dialog — close and fall through to fallback
            page.keyboard.press("Escape")
            time.sleep(0.5)

    # Fallback: click any visible element whose text looks like "4.7(50)"
    page.evaluate("""
        () => {
            const all = [...document.querySelectorAll('*')];
            for (const el of all) {
                const t = (el.innerText || '').trim();
                if (/^\\d+\\.\\d+$/.test(t) && el.children.length === 0) {
                    // Click the closest ancestor that might be clickable
                    let target = el.parentElement;
                    for (let i = 0; i < 4 && target; i++, target = target.parentElement) {
                        if (['BUTTON', 'A'].includes(target.tagName) ||
                            target.getAttribute('tabindex') !== null) {
                            target.click();
                            return true;
                        }
                    }
                    el.click();
                    return true;
                }
            }
            return false;
        }
    """)
    time.sleep(1.8)
    dialog = page.query_selector('[role="dialog"]')
    if dialog:
        heading = dialog.query_selector("h2")
        if heading and "rating" in heading.inner_text().lower():
            return True

    return False


def _scroll_reviews_in_dialog(page) -> None:
    """Scroll the overflow container inside the dialog to reveal all reviews."""
    page.evaluate("""
        () => {
            const c = document.querySelector(
                '[role="dialog"] .overflow-y-auto, [role="dialog"] [class*="overflow-y-auto"]'
            );
            if (c) c.scrollTop = c.scrollHeight;
        }
    """)
    time.sleep(0.8)


def _extract_reviews_from_dialog(page, overall_stars: int) -> list[dict]:
    """
    Parse review cards from the open dialog.

    Each card: div.py-6 (inside [role="dialog"])
      stars:  count svg[fill="#FFC501"]
      text:   p.mt-3
    """
    dialog = page.query_selector('[role="dialog"]')
    if not dialog:
        return []

    _scroll_reviews_in_dialog(page)

    cards = dialog.query_selector_all("div.py-6")
    if not cards:
        cards = dialog.query_selector_all("div[class*='py-6']")

    results: list[dict] = []
    seen_texts: set[str] = set()

    for card in cards:
        # Review text
        text_el = (
            card.query_selector("p.mt-3")
            or card.query_selector("p[class*='mt-3']")
        )
        if not text_el:
            continue
        text = text_el.inner_text().strip()
        if not text or len(text.split()) < 3 or text in seen_texts:
            continue
        seen_texts.add(text)

        # Stars: count filled yellow SVGs in this card
        filled = card.query_selector_all('svg[fill="#FFC501"]')
        stars = len(filled) if 1 <= len(filled) <= 5 else overall_stars

        results.append({
            "text": text,
            "stars": stars,
            "tone": _infer_tone(text),
            "region": _infer_region(text),
            "source": "chowdeck",
            "business_category": "Restaurants",
        })

    return results


def _get_overall_stars(page) -> int:
    """Read the overall restaurant rating from the sidebar."""
    try:
        rating_str = page.evaluate("""
            () => {
                const spans = [...document.querySelectorAll('span, div')];
                for (const el of spans) {
                    const t = (el.innerText || '').trim();
                    if (/^\\d+\\.\\d+$/.test(t)) return t;
                }
                return null;
            }
        """)
        if rating_str:
            return round(float(rating_str))
    except Exception:
        pass
    return 4  # safe Nigerian food app default


# ── main ─────────────────────────────────────────────────────────────────────

def collect_with_playwright() -> list[dict]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise SystemExit(
            "Playwright not installed.\n"
            "Run: pip install playwright && playwright install chromium"
        )

    all_reviews: list[dict] = []

    CUSTOMER_ADDRESS = json.dumps({
        "id": 23487,
        "street": "Faculty Of Arts Theatre, Akoka 101245, Lagos, Nigeria",
        "pretty_name": "Faculty Of Arts Theatre, Akoka, Lagos",
        "city": "Akoka",
        "state": "Lagos",
        "country": "Nigeria",
        "coordinate": {"x": 3.3983531, "y": 6.5196318},
        "house_number": None,
        "floor": None,
        "direction": None,
        "created_at": "2022-07-30T16:32:28.000Z",
        "updated_at": "2026-05-18T17:56:13.000Z",
        "last_used": "2026-05-18T17:56:13.000Z",
        "tag": None,
        "is_active": True,
        "is_current": False,
    }, separators=(",", ":"))

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Linux; Android 10; SM-G975U) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Mobile Safari/537.36"
            ),
            timezone_id="Africa/Lagos",
        )
        # Inject localStorage keys before every page navigation
        context.add_init_script(f"""
            localStorage.setItem('cookies_consent', 'accept');
            localStorage.setItem('customer_address', {json.dumps(CUSTOMER_ADDRESS)});
        """)
        page = context.new_page()

        # ── discover restaurant paths from listing page ───────────────────────
        print(f"\nDiscovering restaurants from {BASE_URL}/store/restaurants ...")
        page.goto(BASE_URL + "/store/restaurants", wait_until="load", timeout=60_000)
        time.sleep(8)

        paths: list[str] = []
        seen: set[str] = set()
        for _ in range(8):
            new_hrefs: list[str] = page.evaluate("""
                () => [...document.querySelectorAll('a[href]')]
                    .map(a => a.getAttribute('href'))
                    .filter(h => h && h.includes('/restaurants/'))
            """)
            added = sum(1 for h in new_hrefs if h not in seen and not seen.add(h) and paths.append(h) is None)
            print(f"  {len(paths)} paths found (+{added})")
            if added == 0 or len(paths) >= MAX_RESTAURANTS:
                break
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(2)

        paths = (paths or RESTAURANT_PATHS)[:MAX_RESTAURANTS]
        print(f"  Using {len(paths)} restaurants")

        # ── collect reviews ──────────────────────────────────────────────────
        for i, path in enumerate(paths, 1):
            url = BASE_URL + path
            print(f"\n[{i}/{len(paths)}] {url}")

            try:
                page.goto(url, wait_until="load", timeout=60_000)
                time.sleep(8)

                name_el = page.query_selector("h1")
                business_name = name_el.inner_text().strip() if name_el else path.split("/")[-1]

                overall_stars = _get_overall_stars(page)

                if not _open_ratings_popup(page):
                    print(f"  Could not open ratings popup — skipping")
                    continue

                reviews = _extract_reviews_from_dialog(page, overall_stars)

                if len(reviews) < MIN_REVIEWS:
                    print(f"  No reviews found in popup")
                    page.keyboard.press("Escape")
                    time.sleep(0.5)
                    continue

                for r in reviews:
                    r["business_name"] = business_name
                all_reviews.extend(reviews)
                print(f"  {business_name}: {len(reviews)} reviews (★{overall_stars} avg)")

                page.keyboard.press("Escape")
                time.sleep(0.5)

            except Exception as e:
                print(f"  Error: {e}")
                try:
                    page.keyboard.press("Escape")
                except Exception:
                    pass
                continue

        context.close()
        browser.close()

    return all_reviews


def main():
    print("Starting Chowdeck collection (auto-discovering restaurants)...")
    reviews = collect_with_playwright()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(reviews, f, indent=2, ensure_ascii=False)

    from collections import Counter
    tones = Counter(r["tone"] for r in reviews)
    stars = Counter(r["stars"] for r in reviews)
    print(f"\nDone. {len(reviews)} reviews → {OUTPUT_PATH.name}")
    print(f"  Tones: {dict(tones)}")
    print(f"  Stars: {dict(sorted(stars.items()))}")


if __name__ == "__main__":
    main()
