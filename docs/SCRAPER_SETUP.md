# Restaurant scraper setup

The scraper (`scrape_nyc_restaurants.py`) pulls restaurant names from **Google Places Text Search** for **Manhattan** (saved as city `NYC`) and **Hamptons towns** (saved as city `Hamptons`).

## 1. Rotate your API key (important)

If your key was ever pasted into chat or a file that might be shared, **create a new key** and delete/disable the old one in [Google Cloud Console → Credentials](https://console.cloud.google.com/apis/credentials).

## 2. Enable the API

1. Open [Google Cloud Console](https://console.cloud.google.com/).
2. Select your project.
3. Go to **APIs & Services → Library**.
4. Enable **Places API** (the legacy API used by Text Search: `maps.googleapis.com/maps/api/place/textsearch`).

## 3. Restrict the key (before pushing this repo)

1. Go to **APIs & Services → Credentials**.
2. Click your API key (or the new one you created).
3. Under **API restrictions**:
   - Choose **Restrict key**.
   - Select only **Places API** (uncheck everything else).
4. Under **Application restrictions**:
   - For a script you run on your Mac, choose **None** (IP restrictions are awkward on home networks).
   - Security comes from: key in `.env` only, API restriction above, and never committing `.env`.
5. Click **Save**.

Optional: set a **quota/budget alert** under **Billing → Budgets & alerts**.

## 4. Local `.env` (never commit)

```bash
cd "/Users/charlieirwin/Desktop/C+E Spots"
cp .env.example .env
```

Edit `.env` and set:

```
GOOGLE_PLACES_API_KEY=your_new_restricted_key_here
```

`.env` is in `.gitignore` and will not be pushed.

## 5. Install and run

```bash
python3 -m pip install requests --user
python3 scrape_nyc_restaurants.py
```

Output: `data/restaurants.csv` with columns `name`, `city`, `neighborhood`, `address`, `cuisine`, `google_rating`, `review_count`, `price`, `place_id`.

## 6. Safe to push to GitHub

Safe to commit:

- `scrape_nyc_restaurants.py` (no key inside)
- `.env.example` (placeholder only)
- `.gitignore`
- this doc

Do **not** commit `.env` or `data/restaurants.csv` unless you intend to publish that data.
