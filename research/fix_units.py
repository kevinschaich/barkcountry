"""Forests merged into one administrative unit keep their own name and location on the map.

    .venv/bin/python fix_units.py

The park file's `name` goes back to the forest's own name, the current unit's name moves to `unit`,
and when the point was shared, the forest's own point comes from Wikipedia (or OpenStreetMap).
"""
import json
from pathlib import Path
from coords import from_wikipedia, from_nominatim

ROOT = Path(__file__).parent
roster = {e['id']: e for e in json.load(open(ROOT / 'roster.json'))}
files = {p.stem: json.load(open(p)) for p in (ROOT / 'parks').glob('*.json')}
live = {i: f for i, f in files.items() if f.get('policy') and roster.get(i, {}).get('region') == 'us-forests'}
points = {}
for i, f in live.items():
    points.setdefault(tuple(f['coordinates']), []).append(i)
for i, f in live.items():
    own = roster[i]['name']
    changed = False
    if f.get('name') and f['name'] != own:
        f['unit'], f['name'] = f['name'], own
        changed = True
    if len(points[tuple(f['coordinates'])]) > 1:
        found = from_wikipedia(own) or from_nominatim(own)
        if found:
            f['coordinates'], f['coordinatesSource'] = found
            changed = True
        print(i, found)
    if changed:
        json.dump(f, open(ROOT / 'parks' / f'{i}.json', 'w'), indent=1, ensure_ascii=False)
