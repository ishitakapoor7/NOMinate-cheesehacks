"""Google Places API (New) text search for restaurants serving a dish.

Replaces the legacy Yelp scraper (which Yelp's anti-bot page reliably broke).
Returns card-ready dicts; photo URLs point at our own proxy route so the API
key never reaches the browser.
"""
import requests
from flask import current_app

SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
TIMEOUT = 10

FIELD_MASK = ",".join(
    [
        "places.displayName",
        "places.formattedAddress",
        "places.rating",
        "places.userRatingCount",
        "places.priceLevel",
        "places.currentOpeningHours.openNow",
        "places.nationalPhoneNumber",
        "places.googleMapsUri",
        "places.websiteUri",
        "places.photos",
    ]
)

PRICE_LEVEL_LABEL = {
    "PRICE_LEVEL_INEXPENSIVE": "$",
    "PRICE_LEVEL_MODERATE": "$$",
    "PRICE_LEVEL_EXPENSIVE": "$$$",
    "PRICE_LEVEL_VERY_EXPENSIVE": "$$$$",
}

# Our budget tiers -> Places price-level filters
BUDGET_PRICE_LEVELS = {
    "<$50": ["PRICE_LEVEL_INEXPENSIVE", "PRICE_LEVEL_MODERATE"],
    "$50-$100": ["PRICE_LEVEL_INEXPENSIVE", "PRICE_LEVEL_MODERATE"],
    "$100-$200": ["PRICE_LEVEL_MODERATE", "PRICE_LEVEL_EXPENSIVE"],
    "$200+": ["PRICE_LEVEL_EXPENSIVE", "PRICE_LEVEL_VERY_EXPENSIVE"],
}


def _to_card(place: dict) -> dict:
    photos = place.get("photos") or []
    photo_name = photos[0].get("name", "") if photos else ""
    open_now = (place.get("currentOpeningHours") or {}).get("openNow")
    maps_url = place.get("googleMapsUri", "")
    return {
        "name": (place.get("displayName") or {}).get("text", ""),
        "rating": place.get("rating"),
        "review_count": place.get("userRatingCount"),
        "price": PRICE_LEVEL_LABEL.get(place.get("priceLevel", ""), ""),
        "address": place.get("formattedAddress", ""),
        "open_now": open_now,
        "phone": place.get("nationalPhoneNumber", ""),
        "maps_url": maps_url,
        "order_url": place.get("websiteUri") or maps_url,
        "photo_url": f"/api/takeout/photo?name={photo_name}" if photo_name else "",
    }


def _text_query(dish_name: str, cuisine: str | None, location: str) -> str:
    """What to ask Google for. Quirky catalog dish names ("Spicy Sprouts Pilaf
    Pressure Cooker") match restaurants loosely and pull in the wrong cuisine, so
    we anchor the search on the dish's cuisine — that's what "order it out" means
    for the diner. Falls back to the dish name when a cuisine isn't known."""
    anchor = (cuisine or "").strip() or (dish_name or "").strip()
    return f"{anchor} restaurant in {location}"


def search_restaurants(dish_name: str, location: str, budget: str | None = None,
                       cuisine: str | None = None, max_results: int = 6) -> list[dict]:
    """Restaurants near ``location`` matching the dish's cuisine, best first.

    Raises requests.RequestException / ValueError upward — the route decides
    how to degrade.
    """
    api_key = current_app.config["GOOGLE_PLACES_API_KEY"]
    body = {
        "textQuery": _text_query(dish_name, cuisine, location),
        "includedType": "restaurant",
        "pageSize": max_results,
    }
    price_levels = BUDGET_PRICE_LEVELS.get(budget or "")
    if price_levels:
        body["priceLevels"] = price_levels

    response = requests.post(
        SEARCH_URL,
        json=body,
        headers={
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": FIELD_MASK,
            "Content-Type": "application/json",
        },
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    places = (response.json() or {}).get("places") or []
    return [_to_card(place) for place in places]


def fetch_photo(photo_name: str, max_width: int = 800) -> tuple[bytes, str]:
    """The photo bytes and content type for a Places photo resource name."""
    api_key = current_app.config["GOOGLE_PLACES_API_KEY"]
    response = requests.get(
        f"https://places.googleapis.com/v1/{photo_name}/media",
        params={"maxWidthPx": max_width, "key": api_key},
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    return response.content, response.headers.get("Content-Type", "image/jpeg")
