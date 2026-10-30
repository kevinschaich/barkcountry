"""Fill in coordinates Wikidata doesn't have: Wikipedia's page summary first, then OSM Nominatim.

    .venv/bin/python coords.py

Updates roster.json in place and records where each point came from in coordinatesSource.
"""
import json, urllib.parse
from pathlib import Path
from fetch import fetch

ROOT = Path(__file__).parent


def from_wikipedia(name):
    r = fetch('https://en.wikipedia.org/api/rest_v1/page/summary/' + urllib.parse.quote(name.replace(' ', '_')))
    if r['status'] != 200: return None
    c = json.loads((ROOT / r['path']).read_text()).get('coordinates')
    return ([c['lon'], c['lat']], f"Wikipedia: {name}") if c else None


def from_nominatim(name):
    r = fetch('https://nominatim.openstreetmap.org/search?' + urllib.parse.urlencode({'q': name, 'format': 'json', 'limit': 1}))
    if r['status'] != 200: return None
    hits = json.loads((ROOT / r['path']).read_text())
    return ([float(hits[0]['lon']), float(hits[0]['lat'])], f"OpenStreetMap: {hits[0]['display_name'][:80]}") if hits else None


def main():
    roster = json.load(open(ROOT / 'roster.json'))
    for e in roster:
        if e['wikidata'] and e['coordinates']:
            e['coordinatesSource'] = f"Wikidata {e['wikidata']}"
        elif e['coordinates']:
            e['coordinatesSource'] = 'original map'
        else:
            found = from_wikipedia(e['name']) or from_nominatim(e['name'])
            if found:
                e['coordinates'], e['coordinatesSource'] = found
            print(e['id'], found)
    json.dump(roster, open(ROOT / 'roster.json', 'w'), indent=1, ensure_ascii=False)


if __name__ == '__main__':
    main()
