# Deploy updated Apps Script (required for Sheets restaurant sync)

The website loads restaurants from your Sheets API (`json.restaurants`) with a fallback to `data/restaurants.json` on GitHub Pages.

## Steps

1. Open the **Google Sheet** linked to your C+E Spots app.
2. **Extensions → Apps Script**.
3. Replace the editor contents with `google-apps-script/Code.gs` from this repo.
4. **Deploy → Manage deployments → Edit (pencil) → Version: New version → Deploy**  
   (Or **New deployment → Web app**, Execute as **Me**, access **Anyone**.)
5. Keep the same Web App URL — no need to change `index.html` if the URL is unchanged.

After deploy, run locally:

```bash
python3 scrape_nyc_restaurants.py --sync-only
```

Then refresh the site — Rankings should show the full directory.

## New sheet tab

The script creates a **Restaurants** tab with columns:  
`name`, `city`, `neighborhood`, `address`, `cuisine`, `google_rating`, `review_count`, `price`, `place_id`

Your existing **Dishes** tab is unchanged.
