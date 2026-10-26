#!/usr/bin/env python3
"""Checks sponsors/sponsors.json (sponsored shop photos, read by Carryolia 2.0.2+).

    python tools/check_sponsors.py [--osm] [--file sponsors/sponsors.json]

Errors (exit code 1): the list can't be read, a field is wrong, a photo is
missing, too big or not a JPEG/PNG. Warnings: an entry has ended, a photo
is larger than advised, a photo file is not used by any entry.
With --osm: also asks the OpenStreetMap API whether each `building` key
still exists and still carries the entry's name (warnings only).

Matches the game's rules in sponsor/Sponsors.kt (Carryolia).
"""
import argparse
import datetime
import json
import os
import re
import sys
import urllib.error
import urllib.request

FORMAT = 1
MAX_PHOTO_BYTES = 2 * 1024 * 1024
ADVISED_PHOTO_BYTES = 300 * 1024
KEY = re.compile(r"^(node|way|relation):[0-9]+$")
DATE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")


def norm_name(name):
    return "".join(c for c in name.lower() if c.isalnum())


def image_kind(data):
    if data[:3] == b"\xff\xd8\xff":
        return "jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    return None


def osm_tags(key):
    kind, number = key.split(":")
    url = f"https://api.openstreetmap.org/api/0.6/{kind}/{number}.json"
    req = urllib.request.Request(url, headers={"User-Agent": "carryolia-map check_sponsors"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            elements = json.load(r).get("elements", [])
    except urllib.error.HTTPError as e:
        if e.code in (404, 410):
            return None
        raise
    return elements[0].get("tags", {}) if elements else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=os.path.join(os.path.dirname(__file__), "..", "sponsors", "sponsors.json"))
    ap.add_argument("--osm", action="store_true", help="check the OSM keys online")
    args = ap.parse_args()

    folder = os.path.dirname(os.path.abspath(args.file))
    errors, warnings = [], []
    try:
        with open(args.file, encoding="utf-8") as f:
            root = json.load(f)
    except Exception as e:
        print(f"ERROR: {args.file} can't be read: {e}")
        return 1
    if root.get("format") != FORMAT:
        errors.append(f'"format" must be {FORMAT}')
    entries = root.get("sponsors")
    if not isinstance(entries, list):
        print('ERROR: "sponsors" must be a list')
        return 1

    today = datetime.date.today().isoformat()
    used_photos = set()
    keys_seen = {}
    for i, e in enumerate(entries):
        where = f"entry {i + 1}" + (f" ({e.get('name')})" if isinstance(e, dict) and e.get("name") else "")
        if not isinstance(e, dict):
            errors.append(f"{where}: not an object")
            continue
        unknown = set(e) - {"building", "name", "lat", "lon", "photo", "caption", "link", "from", "until"}
        if unknown:
            warnings.append(f"{where}: unknown fields ignored by the game: {', '.join(sorted(unknown))}")
        key = e.get("building")
        if key is not None and not KEY.match(str(key).lower()):
            errors.append(f'{where}: "building" must look like node:123 / way:123 / relation:123')
        has_position = all(isinstance(e.get(k), (int, float)) for k in ("lat", "lon"))
        if ("lat" in e or "lon" in e) and not has_position:
            errors.append(f'{where}: "lat" and "lon" must both be numbers')
        if has_position and not (-90 <= e["lat"] <= 90 and -180 <= e["lon"] <= 180):
            errors.append(f"{where}: lat/lon out of range (swapped?)")
        if key is None and not (e.get("name") and has_position):
            errors.append(f'{where}: needs "building", or "name" + "lat" + "lon"')
        if key is not None and not (e.get("name") and has_position):
            warnings.append(f'{where}: add "name", "lat" and "lon" too, so it still matches if OSM redraws the shop')
        if key:
            k = str(key).lower()
            if k in keys_seen:
                warnings.append(f"{where}: same building as entry {keys_seen[k]} (the first active one wins)")
            keys_seen.setdefault(k, i + 1)

        for d in ("from", "until"):
            if d in e and not (isinstance(e[d], str) and DATE.match(e[d])):
                errors.append(f'{where}: "{d}" must be YYYY-MM-DD')
        if isinstance(e.get("until"), str) and DATE.match(e["until"]) and e["until"] < today:
            warnings.append(f"{where}: ended on {e['until']} (no longer shown)")
        if isinstance(e.get("from"), str) and isinstance(e.get("until"), str) and e["from"] > e["until"]:
            errors.append(f'{where}: "from" is after "until"')

        link = e.get("link")
        if link is not None and not re.match(r"^https?://[^\s/@]+\.[^\s/@]+", str(link)) and not re.match(r"^[^\s:/@]+\.[^\s/@]+", str(link)):
            errors.append(f'{where}: "link" is not a website address')

        photo = e.get("photo")
        if not isinstance(photo, str) or not photo.strip():
            errors.append(f'{where}: "photo" missing')
            continue
        photo = photo.strip()
        if photo.startswith("https://"):
            warnings.append(f"{where}: photo hosted elsewhere ({photo}), not checked")
            continue
        if "://" in photo or ".." in photo or photo.startswith("/") or "\\" in photo:
            errors.append(f'{where}: "photo" must be a path inside sponsors/ (or an https:// address)')
            continue
        path = os.path.join(folder, photo)
        used_photos.add(os.path.normpath(path))
        if not os.path.isfile(path):
            errors.append(f"{where}: photo file {photo} not found")
            continue
        size = os.path.getsize(path)
        with open(path, "rb") as f:
            kind = image_kind(f.read(16))
        if kind is None:
            errors.append(f"{where}: {photo} is not a JPEG or PNG")
        if size > MAX_PHOTO_BYTES:
            errors.append(f"{where}: {photo} is {size // 1024} kB; the game skips photos over {MAX_PHOTO_BYTES // 1024} kB")
        elif size > ADVISED_PHOTO_BYTES:
            warnings.append(f"{where}: {photo} is {size // 1024} kB (advised: under {ADVISED_PHOTO_BYTES // 1024} kB)")
        if " " in photo or photo != photo.lower():
            warnings.append(f"{where}: {photo}: use lower case and no spaces in file names")

        if args.osm and key and KEY.match(str(key).lower()):
            try:
                tags = osm_tags(str(key).lower())
            except Exception as ex:
                warnings.append(f"{where}: couldn't ask OpenStreetMap about {key}: {ex}")
                tags = {}
            if tags is None:
                warnings.append(f"{where}: {key} no longer exists in OpenStreetMap (name + position fallback in use)")
            elif tags and e.get("name") and norm_name(tags.get("name", "")) != norm_name(e["name"]):
                warnings.append(f"{where}: {key} is now called {tags.get('name')!r} in OpenStreetMap")

    photos_dir = os.path.join(folder, "photos")
    if os.path.isdir(photos_dir):
        for name in sorted(os.listdir(photos_dir)):
            path = os.path.normpath(os.path.join(photos_dir, name))
            if name.lower().endswith((".jpg", ".jpeg", ".png")) and path not in used_photos:
                warnings.append(f"photos/{name} is not used by any entry")

    for w in warnings:
        print("warning:", w)
    for e in errors:
        print("ERROR:", e)
    active = sum(1 for e in entries if isinstance(e, dict) and (e.get("from") or "") <= today <= (e.get("until") or "9999"))
    print(f"{len(entries)} entries, {active} shown today, {len(errors)} errors, {len(warnings)} warnings")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
