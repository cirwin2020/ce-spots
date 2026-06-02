"""
Scrape restaurants via Google Places Text Search for Manhattan (NYC) and the Hamptons.
Requires GOOGLE_PLACES_API_KEY in .env or environment. See docs/SCRAPER_SETUP.md.

Writes data/restaurants.json (+ CSV) and optionally syncs to Google Sheets via save_restaurants.
"""
import argparse
import csv
import json
import os
import sys
import time

import requests

SHEETS_API = os.environ.get(
    "CE_SPOTS_API",
    "https://script.google.com/macros/s/AKfycbxzlho_0KN_u5IMpCKIeoIMcJ0NQVVnJPU78Aw589nUPquecojnds5NHDeME2ytK-46/exec",
)

# (query, city label for app, neighborhood label for CSV)
SEARCHES = [
    # Manhattan → city "NYC" in C+E Spots
    ("restaurants in Upper East Side Manhattan NYC", "NYC", "Upper East Side"),
    ("restaurants in Upper West Side Manhattan NYC", "NYC", "Upper West Side"),
    ("restaurants in Midtown East Manhattan NYC", "NYC", "Midtown East"),
    ("restaurants in Midtown West Manhattan NYC", "NYC", "Midtown West"),
    ("restaurants in Hell's Kitchen Manhattan NYC", "NYC", "Hell's Kitchen"),
    ("restaurants in Chelsea Manhattan NYC", "NYC", "Chelsea"),
    ("restaurants in Greenwich Village Manhattan NYC", "NYC", "Greenwich Village"),
    ("restaurants in West Village Manhattan NYC", "NYC", "West Village"),
    ("restaurants in SoHo Manhattan NYC", "NYC", "SoHo"),
    ("restaurants in Tribeca Manhattan NYC", "NYC", "Tribeca"),
    ("restaurants in Lower East Side Manhattan NYC", "NYC", "Lower East Side"),
    ("restaurants in East Village Manhattan NYC", "NYC", "East Village"),
    ("restaurants in Nolita Manhattan NYC", "NYC", "Nolita"),
    ("restaurants in Flatiron Manhattan NYC", "NYC", "Flatiron"),
    ("restaurants in Gramercy Manhattan NYC", "NYC", "Gramercy"),
    ("restaurants in Murray Hill Manhattan NYC", "NYC", "Murray Hill"),
    ("restaurants in Financial District Manhattan NYC", "NYC", "Financial District"),
    ("restaurants in Harlem Manhattan NYC", "NYC", "Harlem"),
    ("restaurants in NoMad Manhattan NYC", "NYC", "NoMad"),
    ("restaurants in Chinatown Manhattan NYC", "NYC", "Chinatown"),
    ("restaurants in Little Italy Manhattan NYC", "NYC", "Little Italy"),
    # Hamptons towns → city "Hamptons" in C+E Spots
    ("restaurants in East Hampton NY", "Hamptons", "East Hampton"),
    ("restaurants in Southampton NY", "Hamptons", "Southampton"),
    ("restaurants in Sag Harbor NY", "Hamptons", "Sag Harbor"),
    ("restaurants in Montauk NY", "Hamptons", "Montauk"),
    ("restaurants in Bridgehampton NY", "Hamptons", "Bridgehampton"),
    ("restaurants in Amagansett NY", "Hamptons", "Amagansett"),
    ("restaurants in Water Mill NY", "Hamptons", "Water Mill"),
    ("restaurants in Westhampton Beach NY", "Hamptons", "Westhampton Beach"),
]

CSV_FIELDS = [
    "name", "city", "neighborhood", "address", "cuisine",
    "google_rating", "review_count", "price", "place_id",
]


def load_api_key():
    key = os.environ.get("GOOGLE_PLACES_API_KEY", "").strip()
    if key:
        return key
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.isfile(env_path):
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("#") or "=" not in line:
                    continue
                name, _, value = line.partition("=")
                if name.strip() == "GOOGLE_PLACES_API_KEY":
                    return value.strip().strip("'\"")
    return ""


def search_places(api_key, query, page_token=None):
    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {"query": query, "key": api_key, "type": "restaurant"}
    if page_token:
        params["pagetoken"] = page_token
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    status = data.get("status")
    if status not in ("OK", "ZERO_RESULTS"):
        raise RuntimeError(f"Places API: {status} — {data.get('error_message', '')}")
    return data


def get_all_results(api_key, query):
    results = []
    data = search_places(api_key, query)
    results.extend(data.get("results", []))
    for _ in range(2):
        token = data.get("next_page_token")
        if not token:
            break
        time.sleep(2)
        data = search_places(api_key, query, token)
        results.extend(data.get("results", []))
    return results


def extract(place, city, neighborhood):
    price_level = place.get("price_level", "")
    price_str = "$" * price_level if isinstance(price_level, int) else ""
    skip = {"restaurant", "food", "point_of_interest", "establishment"}
    types = [
        t.replace("_", " ").title()
        for t in place.get("types", [])
        if t not in skip
    ]
    return {
        "name": place.get("name", ""),
        "city": city,
        "neighborhood": neighborhood,
        "address": place.get("formatted_address", ""),
        "cuisine": types[0] if types else "",
        "google_rating": place.get("rating", ""),
        "review_count": place.get("user_ratings_total", ""),
        "price": price_str,
        "place_id": place.get("place_id", ""),
    }


def save_outputs(seen, root):
    data_dir = os.path.join(root, "data")
    os.makedirs(data_dir, exist_ok=True)
    rows = list(seen.values())
    csv_path = os.path.join(data_dir, "restaurants.csv")
    json_path = os.path.join(data_dir, "restaurants.json")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=0)
    return csv_path, json_path, rows


def sync_to_sheets(restaurants):
    body = json.dumps({"action": "save_restaurants", "restaurants": restaurants})
    resp = requests.post(
        SHEETS_API,
        data=body,
        headers={"Content-Type": "text/plain"},
        timeout=120,
        allow_redirects=True,
    )
    try:
        out = resp.json()
    except Exception:
        out = {"ok": False, "raw": resp.text[:500]}
    return out


def scrape_all(api_key):
    seen = {}
    for query, city, neighborhood in SEARCHES:
        label = f"{neighborhood} ({city})"
        print(f"Searching: {label}...")
        try:
            results = get_all_results(api_key, query)
            new = 0
            for place in results:
                pid = place.get("place_id")
                if pid and pid not in seen:
                    seen[pid] = extract(place, city, neighborhood)
                    new += 1
            print(f"  → {new} new  |  {len(seen)} total unique")
        except Exception as e:
            print(f"  → Error: {e}")
        time.sleep(0.5)
    return seen


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--sync-only",
        action="store_true",
        help="Upload existing data/restaurants.json to Sheets (no Places API calls)",
    )
    parser.add_argument("--no-sync", action="store_true", help="Skip Google Sheets upload")
    args = parser.parse_args()
    root = os.path.dirname(os.path.abspath(__file__))

    if args.sync_only:
        json_path = os.path.join(root, "data", "restaurants.json")
        if not os.path.isfile(json_path):
            print(f"No file at {json_path}", file=sys.stderr)
            sys.exit(1)
        with open(json_path, encoding="utf-8") as f:
            rows = json.load(f)
        print(f"Loaded {len(rows)} restaurants from {json_path}")
    else:
        api_key = load_api_key()
        if not api_key:
            print(
                "Missing GOOGLE_PLACES_API_KEY.\n"
                "  cp .env.example .env   # then paste your key\n"
                "  See docs/SCRAPER_SETUP.md",
                file=sys.stderr,
            )
            sys.exit(1)
        seen = scrape_all(api_key)
        _, json_path, rows = save_outputs(seen, root)
        nyc = sum(1 for r in rows if r["city"] == "NYC")
        ham = sum(1 for r in rows if r["city"] == "Hamptons")
        print(f"\n✅ Scraped {len(rows)} restaurants ({nyc} NYC, {ham} Hamptons)")
        print(f"   {json_path}")

    if not args.no_sync:
        print("Syncing to Google Sheets...")
        result = sync_to_sheets(rows)
        if result.get("ok"):
            print(f"✅ Sheets updated ({result.get('count', len(rows))} restaurants)")
            print("   Deploy google-apps-script/Code.gs if GET still has no restaurants.")
        else:
            print("⚠️  Sheets sync failed:", result)
            print("   Paste Code.gs into Apps Script and redeploy, then run:")
            print("   python3 scrape_nyc_restaurants.py --sync-only")


if __name__ == "__main__":
    main()
