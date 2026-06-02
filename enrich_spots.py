"""
Enrich every logged + to-try + recommended spot with Google Places data and
merge it into data/restaurants.json so the website can match the names.

Logged spots are pulled live from the Sheets API; to-try / recommendation
lists mirror index.html. Requires GOOGLE_PLACES_API_KEY in .env.
Run after scrape_nyc_restaurants.py:  python3 enrich_spots.py
"""
import csv
import json
import os
import re
import sys
import time

import requests

from scrape_nyc_restaurants import load_api_key, search_places, CSV_FIELDS, SHEETS_API

# section/city label -> Google query suffix
CITY_QUERY = {
    "NYC": "New York, NY",
    "Hamptons": "the Hamptons, NY",
    "Palm Beach": "Palm Beach, FL",
    "Stockholm": "Stockholm, Sweden",
    "Ithaca": "Ithaca, NY",
    "Bangor": "Bangor, ME",
    "Maine": "Maine",
}

# To-try + recommendation lists (mirror of index.html)
TRY_LISTS = {
    "NYC — Lunch": ["Commerce Inn", "Skinny Louie (GF Burger)", "abcV", "Sixteen Mill (bakery)", "Rubirosa", "The Elk (matcha + coffee)", "Bubby's"],
    "NYC — Dinner": ["Cecchi's", "Elio's", "Hoexter's", "Altro Paradiso", "Dante NYC", "Palma", "Monkey Bar", "Casa Carmen", "Giulietta", "The Corner Store", "Torrisi", "Bar Bianchi", "JoJo", "Catch", "Au Cheval", "The Clocktower", "The Lobster Club", "Dudley's", "Buvette", "Cucina Alba", "Raoul's", "Sartiano's", "Perry Street"],
    "Hamptons": ["Bilboquet", "Sagaponack General Store", "Sunlife", "Sag Coffee", "East Hampton Grill", "Duryea's", "La Fondita", "Sag Pizza", "Double's Amagansett", "Goldberg's", "Buddah Berry", "Big Olaf's", "Camp Rubirosa", "Jack's Coffee", "Clam Bar", "Joni's Montauk", "Montauk General Store", "Town Line BBQ"],
    "Palm Beach": ["Le Bilboquet"],
}
REC_LISTS = {
    "NYC — Dinner": ["Via Carota", "Lilia", "I Sodi", "Rezdôra", "Roscioli", "4 Charles Prime Rib"],
    "NYC — Lunch": ["La Cabra", "Librae Bakery", "Sadelle's"],
    "Hamptons": ["Calissa", "Topping Rose", "Morgan's Fork"],
    "Palm Beach": ["Renato's", "Casa Bella"],
}


def section_city(section):
    if "Hamptons" in section:
        return "Hamptons"
    if "Palm Beach" in section:
        return "Palm Beach"
    if "NYC" in section:
        return "NYC"
    return "NYC"


def norm_key(s):
    s = str(s or "").lower().replace("&", "and")
    return re.sub(r"[^a-z0-9]", "", s)


def clean_name(name):
    return re.sub(r"\s*\(.*?\)\s*", " ", name).strip()


def fetch_logged():
    try:
        r = requests.get(SHEETS_API, timeout=30)
        rows = r.json().get("data", [])
    except Exception as e:
        print("Could not fetch logged dishes:", e, file=sys.stderr)
        return []
    seen = {}
    for d in rows:
        n = (d.get("restaurant") or "").strip()
        c = (d.get("city") or "").strip()
        if n and n not in seen:
            seen[n] = c
    return [(n, c) for n, c in seen.items()]


def best_match(api_key, name, city_label):
    suffix = CITY_QUERY.get(city_label, city_label)
    query = f"{clean_name(name)}, {suffix}"
    data = search_places(api_key, query)
    results = data.get("results", [])
    if not results:
        return None
    p = results[0]
    price_level = p.get("price_level", "")
    skip = {"restaurant", "food", "point_of_interest", "establishment"}
    types = [t.replace("_", " ").title() for t in p.get("types", []) if t not in skip]
    return {
        "name": clean_name(name),
        "city": city_label,
        "neighborhood": "",
        "address": p.get("formatted_address", ""),
        "cuisine": types[0] if types else "",
        "google_rating": p.get("rating", ""),
        "review_count": p.get("user_ratings_total", ""),
        "price": "$" * price_level if isinstance(price_level, int) else "",
        "place_id": p.get("place_id", ""),
    }


def main():
    api_key = load_api_key()
    if not api_key:
        print("Missing GOOGLE_PLACES_API_KEY (see docs/SCRAPER_SETUP.md)", file=sys.stderr)
        sys.exit(1)

    root = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(root, "data", "restaurants.json")
    rows = []
    if os.path.isfile(json_path):
        with open(json_path, encoding="utf-8") as f:
            rows = json.load(f)
    existing = {norm_key(r["name"]) for r in rows}
    by_place = {r.get("place_id") for r in rows if r.get("place_id")}

    targets = []
    for n, c in fetch_logged():
        targets.append((n, c))
    for section, names in {**TRY_LISTS}.items():
        for n in names:
            targets.append((n, section_city(section)))
    for section, names in {**REC_LISTS}.items():
        for n in names:
            targets.append((n, section_city(section)))

    added, skipped, missed = 0, 0, []
    for name, city in targets:
        key = norm_key(clean_name(name))
        if key in existing:
            skipped += 1
            continue
        print(f"Enriching: {clean_name(name)} ({city})...")
        try:
            entry = best_match(api_key, name, city)
        except Exception as e:
            print(f"  → error: {e}")
            entry = None
        if not entry:
            missed.append(f"{name} ({city})")
            continue
        if entry["place_id"] and entry["place_id"] in by_place:
            # already in directory under a different name — adopt our name key
            existing.add(key)
        rows.append(entry)
        existing.add(key)
        if entry["place_id"]:
            by_place.add(entry["place_id"])
        added += 1
        gr = entry["google_rating"]
        print(f"  → {entry['name']} · {gr or 'no'} rating · {entry['cuisine'] or 'n/a'}")
        time.sleep(0.3)

    # write outputs
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=0)
    csv_path = os.path.join(root, "data", "restaurants.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n✅ Enriched {added} spots · {skipped} already in directory · {len(rows)} total")
    if missed:
        print("No Google match for:", ", ".join(missed))


if __name__ == "__main__":
    main()
