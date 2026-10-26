# Sponsored shop photos

Carryolia (from version 2.0.2) shows a photo in a building's **Details** popup
when that building is in `sponsors.json`, marked "📷 Sponsored photo". The game
fetches this list at every game start (and at most once an hour while playing;
2.0.2–2.0.3: once a day), so adding, changing or ending a sponsor needs no app
update: commit to `main` and it shows the next time someone starts the game
(GitHub's file server can lag a few minutes behind a commit).

The photos and this list are **public** (anyone can browse this repository).

## Adding a sponsor

1. **Find the building's OSM key.** Open the shop on
   [openstreetmap.org](https://www.openstreetmap.org) (search its name, or right-click
   ▸ "Query features" and pick it). The address bar shows e.g.
   `openstreetmap.org/node/1234567890` → the key is `node:1234567890`
   (`way:…` for a building outline, `relation:…` rarely). Use the object that
   carries the shop's name and `shop=…` tag; that is the one the game shows.
2. **Prepare the photo**: JPEG or PNG, at most 2 MB (larger ones are not
   downloaded), ideally about 1280 px on the longest side and under 300 kB.
   The game shows it up to 240 dp tall above the popup's text, scaled to fit.
   Only use a photo the shop owns and has allowed you to use.
3. **Give it a new, unique file name** (lower case, no spaces), e.g.
   `photos/kruidvat-horst-2026.jpg`, and put it in `photos/`.
   Replacing a photo? Use a **new file name**: phones keep a photo they
   downloaded under its name and won't fetch the same name again.
4. **Add an entry** to `sponsors.json` (see `sponsors.example.json`):

| Field | Needed | What |
| --- | --- | --- |
| `building` | yes* | OSM key, `node:…` / `way:…` / `relation:…` |
| `name` | yes* | The shop's name as in OpenStreetMap |
| `lat`, `lon` | yes* | The shop's position (from openstreetmap.org, right-click ▸ "Show address") |
| `photo` | yes | Path relative to this folder (`photos/….jpg`), or a full `https://` address |
| `caption` | no | One short line under the photo, shown as written (not translated) |
| `link` | no | The website the sponsor sent you, shown as a 🌐 link. Without it no website is shown (game 2.0.3+; 2.0.2 fell back to the OpenStreetMap website tag) |
| `from` | no | First day shown, `YYYY-MM-DD` |
| `until` | no | Last day shown, `YYYY-MM-DD` (inclusive). After it the entry is ignored. |

\* An entry matches a building by `building` first. If OpenStreetMap redraws
the shop (the key changes), a building with the same `name` (ignoring case,
spaces and punctuation) within 100 m of `lat`/`lon` matches instead. So
always fill in all four; an entry with only `name` + `lat`/`lon` also works.

5. **Check** before committing:

   ```
   python tools/check_sponsors.py            # format, files, sizes, dates
   python tools/check_sponsors.py --osm      # also: does the OSM key still exist, same name?
   ```

   The "Check sponsors" workflow runs the first check on every push that
   touches `sponsors/`.

## Example: Slagerij Joosten, Steenstraat 16, Horst

openstreetmap.org shows it as `Knooppunt: Slagerij Joosten (2792432398)`, location
`51.4532143, 6.0529437` ("Knooppunt" = node). Photo saved as
`photos/slagerij-joosten-horst.jpg`. The entry in `sponsors.json`:

```json
{
  "format": 1,
  "sponsors": [
    {
      "building": "node:2792432398",
      "name": "Slagerij Joosten",
      "lat": 51.4532143,
      "lon": 6.0529437,
      "photo": "photos/slagerij-joosten-horst.jpg",
      "caption": "Ambachtelijke slager in Horst",
      "link": "https://slagerijjoosten.nl/site/",
      "from": "2026-11-01",
      "until": "2027-10-31"
    }
  ]
}
```

More sponsors: add another `{ … }` block inside the `[ ]`, separated by a comma.

## Ending a sponsor

Let `until` pass (nothing to do), or remove the entry. Phones delete photos
that are no longer in the list the next time they fetch it. Delete the photo
file here too once it is no longer used.

## Monthly check

Run `python tools/check_sponsors.py --osm` now and then: it lists entries
whose OSM object is gone or renamed (the game then relies on the name +
position fallback; update `building` to the new key).

## Format

`"format": 1`. A future game version that needs more fields will raise it;
older games then ignore the whole list rather than misread it.
