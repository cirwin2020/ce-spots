/**
 * C+E Spots — Google Sheets backend
 * Deploy: Extensions → Apps Script → paste this file → Deploy → New deployment → Web app
 *   Execute as: Me | Who has access: Anyone
 *
 * Sheets: "Dishes" (existing) + "Restaurants" (directory from Places API)
 */
const DISH_SHEET = 'Dishes';
const REST_SHEET = 'Restaurants';

function doGet() {
  return jsonOut({
    ok: true,
    data: readDishes(),
    restaurants: readRestaurants(),
  });
}

function doPost(e) {
  try {
    const body = JSON.parse(e.postData.contents);
    if (body.action === 'save_all') {
      writeDishes(body.data || []);
      return jsonOut({ ok: true });
    }
    if (body.action === 'save_restaurants') {
      writeRestaurants(body.restaurants || []);
      return jsonOut({ ok: true, count: (body.restaurants || []).length });
    }
    return jsonOut({ ok: false, error: 'Unknown action' });
  } catch (err) {
    return jsonOut({ ok: false, error: String(err) });
  }
}

function jsonOut(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(
    ContentService.MimeType.JSON
  );
}

function ss() {
  return SpreadsheetApp.getActiveSpreadsheet();
}

function readDishes() {
  const sh = ss().getSheetByName(DISH_SHEET);
  if (!sh || sh.getLastRow() < 2) return [];
  const rows = sh.getDataRange().getValues();
  const h = rows[0].map(String);
  const idx = (n) => h.indexOf(n);
  const out = [];
  for (let i = 1; i < rows.length; i++) {
    const r = rows[i];
    if (!r[idx('dish')] && !r[idx('restaurant')]) continue;
    out.push({
      id: Number(r[idx('id')]) || i,
      dish: String(r[idx('dish')] || ''),
      restaurant: String(r[idx('restaurant')] || ''),
      city: String(r[idx('city')] || ''),
      rating: Number(r[idx('rating')]) || 0,
      notes: String(r[idx('notes')] || ''),
      date: r[idx('date')] ? String(r[idx('date')]) : '',
      type: String(r[idx('type')] || 'dish'),
      emoji: String(r[idx('emoji')] || '🍽️'),
    });
  }
  return out;
}

function writeDishes(data) {
  let sh = ss().getSheetByName(DISH_SHEET);
  if (!sh) {
    sh = ss().insertSheet(DISH_SHEET);
  }
  const headers = ['id', 'dish', 'restaurant', 'city', 'rating', 'notes', 'date', 'type', 'emoji'];
  sh.clear();
  sh.getRange(1, 1, 1, headers.length).setValues([headers]);
  if (!data.length) return;
  const rows = data.map((d) => [
    d.id,
    d.dish,
    d.restaurant,
    d.city,
    d.rating,
    d.notes || '',
    d.date || '',
    d.type || 'dish',
    d.emoji || '🍽️',
  ]);
  sh.getRange(2, 1, rows.length, headers.length).setValues(rows);
}

function readRestaurants() {
  const sh = ss().getSheetByName(REST_SHEET);
  if (!sh || sh.getLastRow() < 2) return [];
  const rows = sh.getDataRange().getValues();
  const h = rows[0].map(String);
  const idx = (n) => h.indexOf(n);
  const out = [];
  for (let i = 1; i < rows.length; i++) {
    const r = rows[i];
    if (!r[idx('name')]) continue;
    out.push({
      name: String(r[idx('name')] || ''),
      city: String(r[idx('city')] || ''),
      neighborhood: String(r[idx('neighborhood')] || ''),
      address: String(r[idx('address')] || ''),
      cuisine: String(r[idx('cuisine')] || ''),
      google_rating: r[idx('google_rating')] !== '' ? r[idx('google_rating')] : '',
      review_count: r[idx('review_count')] !== '' ? r[idx('review_count')] : '',
      price: String(r[idx('price')] || ''),
      place_id: String(r[idx('place_id')] || ''),
    });
  }
  return out;
}

function writeRestaurants(list) {
  let sh = ss().getSheetByName(REST_SHEET);
  if (!sh) {
    sh = ss().insertSheet(REST_SHEET);
  }
  const headers = [
    'name',
    'city',
    'neighborhood',
    'address',
    'cuisine',
    'google_rating',
    'review_count',
    'price',
    'place_id',
  ];
  sh.clear();
  sh.getRange(1, 1, 1, headers.length).setValues([headers]);
  if (!list.length) return;
  const rows = list.map((r) => [
    r.name,
    r.city,
    r.neighborhood || '',
    r.address || '',
    r.cuisine || '',
    r.google_rating != null ? r.google_rating : '',
    r.review_count != null ? r.review_count : '',
    r.price || '',
    r.place_id || '',
  ]);
  sh.getRange(2, 1, rows.length, headers.length).setValues(rows);
}
