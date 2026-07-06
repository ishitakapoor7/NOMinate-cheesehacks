import requests
from bs4 import BeautifulSoup
import time
import random
import json


# ── Cache to avoid re-scraping the same query within a session ───────────────
_cache = {}

HEADERS_LIST = [
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    },
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/119.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.8",
    },
    {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/118.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.7",
    },
]

# Map our budget tiers to Yelp's price filter (1=$, 2=$$, 3=$$$, 4=$$$$)
BUDGET_TO_PRICE = {
    "<$50":      "1",
    "$50-$100":  "1,2",
    "$100-$200": "2,3",
    "$200+":     "3,4",
}


def scrape_yelp_restaurants(dish_name, location, budget=None, max_results=5):
    """
    Scrape Yelp search results for restaurants serving a dish near a location.

    Strategy: Yelp embeds structured JSON-LD data in every search page inside
    a <script type="application/json"> tag. This is more stable than parsing
    CSS class names which Yelp changes frequently.

    Args:
        dish_name:   e.g. "Pad Thai"
        location:    e.g. "Madison, WI" or "10001"
        budget:      one of "<$50", "$50-$100", "$100-$200", "$200+"
        max_results: how many restaurants to return

    Returns:
        list of dicts: [{name, rating, price, address, url}, ...]
        Returns an empty list if scraping fails.
    """
    cache_key = f"{dish_name}|{location}|{budget}"
    if cache_key in _cache:
        return _cache[cache_key]

    params = {
        "find_desc": dish_name,
        "find_loc":  location,
    }
    if budget and budget in BUDGET_TO_PRICE:
        params["attrs"] = f"RestaurantsPriceRange2.{BUDGET_TO_PRICE[budget]}"

    headers = random.choice(HEADERS_LIST)

    try:
        time.sleep(random.uniform(1.0, 2.5))   # polite delay before each request

        response = requests.get(
            "https://www.yelp.com/search",
            params=params,
            headers=headers,
            timeout=10,
        )

        if response.status_code != 200:
            print(f"Yelp returned status {response.status_code}")
            return _fallback_results(dish_name, location)

        soup = BeautifulSoup(response.text, "html.parser")
        restaurants = _parse_yelp_page(soup, max_results)

        if not restaurants:
            return _fallback_results(dish_name, location)

        _cache[cache_key] = restaurants
        return restaurants

    except requests.exceptions.Timeout:
        print("Yelp request timed out")
        return _fallback_results(dish_name, location)
    except Exception as e:
        print(f"Yelp scraping error: {e}")
        return _fallback_results(dish_name, location)


def _parse_yelp_page(soup, max_results):
    """
    Parse the Yelp search results page.

    Yelp embeds business data as JSON inside <script> tags with
    type="application/json". We look for the tag that contains
    the search results and extract name, rating, price, and address.

    Falls back to HTML parsing if the JSON approach doesn't find results.
    """
    restaurants = []

    # ── Approach 1: JSON embedded in script tags ──────────────────────────────
    for script in soup.find_all("script", type="application/json"):
        try:
            data = json.loads(script.string or "")
            # The search results live under different keys depending on Yelp's
            # current page structure — we walk the JSON to find business entries
            businesses = _extract_businesses_from_json(data)
            if businesses:
                for biz in businesses[:max_results]:
                    restaurants.append({
                        "name":    biz.get("name", "Unknown"),
                        "rating":  biz.get("rating", "N/A"),
                        "price":   biz.get("priceRange", ""),
                        "address": biz.get("formattedAddress", ""),
                        "url":     biz.get("businessUrl", "https://www.yelp.com"),
                    })
                if restaurants:
                    return restaurants
        except (json.JSONDecodeError, TypeError):
            continue

    # ── Approach 2: HTML parsing as fallback ──────────────────────────────────
    # Look for business name elements — Yelp uses h3 tags with specific patterns
    cards = soup.find_all("h3", limit=max_results * 2)
    for card in cards:
        link = card.find("a", href=True)
        if link and "/biz/" in link.get("href", ""):
            name = link.get_text(strip=True)
            url  = "https://www.yelp.com" + link["href"]
            if name:
                restaurants.append({
                    "name":    name,
                    "rating":  "N/A",
                    "price":   "",
                    "address": "",
                    "url":     url,
                })
        if len(restaurants) >= max_results:
            break

    return restaurants


def _extract_businesses_from_json(data, depth=0):
    """
    Recursively walk the embedded JSON to find a list that looks like
    business entries (has 'name' and 'rating' keys).
    Yelp's JSON structure changes over time so we search flexibly.
    """
    if depth > 6:   # don't recurse infinitely
        return []

    if isinstance(data, list):
        # Check if this list looks like business results
        if data and isinstance(data[0], dict) and "name" in data[0]:
            return data
        # Otherwise recurse into each element
        for item in data:
            result = _extract_businesses_from_json(item, depth + 1)
            if result:
                return result

    elif isinstance(data, dict):
        for value in data.values():
            result = _extract_businesses_from_json(value, depth + 1)
            if result:
                return result

    return []


def _fallback_results(dish_name, location):
    """
    If Yelp scraping fails entirely, return a helpful message
    instead of crashing the app.
    """
    return [{
        "name":    f"Search '{dish_name} near {location}' on Yelp",
        "rating":  "",
        "price":   "",
        "address": "",
        "url":     f"https://www.yelp.com/search?find_desc={dish_name.replace(' ', '+')}&find_loc={location.replace(' ', '+')}",
    }]
