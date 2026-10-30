"""Build the full list of parks from Wikidata: every US national park, US national forest,
Parks Canada national park and Québec national park, with official site and location.

    .venv/bin/python roster.py

Writes roster.json. Parks already on the map keep their ids, so the original data lines up.
"""
import json, re, unicodedata, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
UA = 'dog-friendly-national-parks-research/1.0 (+https://github.com/kevinschaich/dog-friendly-national-parks)'
CLASSES = {'us-parks': 'Q34918903', 'us-forests': 'Q612741', 'canada-parks': 'Q1896949', 'quebec-parks': 'Q3364923'}
QUERY = """SELECT ?p ?label ?fr ?site ?coord ?end WHERE {
  ?p wdt:P31 wd:%s .
  OPTIONAL { ?p rdfs:label ?label FILTER(lang(?label) = 'en') }
  OPTIONAL { ?p rdfs:label ?fr FILTER(lang(?fr) = 'fr') }
  OPTIONAL { ?p wdt:P856 ?site }
  OPTIONAL { ?p wdt:P625 ?coord }
  OPTIONAL { ?p wdt:P576 ?end }
}"""


def slug(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')


def sparql(q):
    url = 'https://query.wikidata.org/sparql?' + urllib.parse.urlencode({'query': q})
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/sparql-results+json'})
    return json.load(urllib.request.urlopen(req, timeout=60))['results']['bindings']


def main():
    original = {p['id']: p for p in json.load(open(ROOT / 'parks.json'))}
    by_name = {slug(p['name']): p for p in original.values()}
    roster = {}
    for region, cls in CLASSES.items():
        for b in sparql(QUERY % cls):
            qid = b['p']['value'].rsplit('/', 1)[1]
            name = (b.get('label') or b.get('fr') or {}).get('value')
            if not name or 'end' in b: continue  # dissolved units were merged into current ones
            e = roster.setdefault(qid, {'wikidata': qid, 'name': name, 'region': region, 'sites': [], 'coordinates': None})
            if b.get('site') and b['site']['value'] not in e['sites']: e['sites'].append(b['site']['value'])
            if b.get('coord') and not e['coordinates']:
                lon, lat = re.findall(r'-?[\d.]+', b['coord']['value'])
                e['coordinates'] = [float(lon), float(lat)]
    def near(a, b):
        return a and b and abs(a[0] - b[0]) < 0.25 and abs(a[1] - b[1]) < 0.25

    def key(n):
        return re.sub(r'-?(national-park|national-forest|parc-national|de-la|du|des|de|d|of-the|the|reserve|and|national-park-reserve)-?', '-', slug(n)).strip('-')

    by_key = {key(p['name']): p for p in original.values()}
    # matches the name and location rules get wrong
    pinned = {'Q1327997': 'parc-national-des-iles-de-boucherville'}
    taken = set(pinned.values())
    for e in roster.values():
        if e['wikidata'] in pinned:
            e['id'] = pinned[e['wikidata']]; e['original'] = original[e['id']]['original']; continue
        match = by_name.get(slug(e['name'])) or by_key.get(key(e['name'])) or next(
            (p for p in original.values() if p['region'] == e['region'] and near(p['original'].get('coordinates'), e['coordinates'])), None)
        if match and match['id'] in taken: match = None
        e['id'] = match['id'] if match else slug(e['name'])
        e['original'] = match['original'] if match else None
    # one map entry can't stand for two parks (e.g. US and Canada Glacier): the name match keeps it
    seen = {}
    for e in sorted(roster.values(), key=lambda e: slug(e['name']) != e['id']):
        if e['id'] in seen:
            e['id'] = slug(e['name']) if slug(e['name']) not in seen else f"{slug(e['name'])}-{e['region']}"
            e['original'] = None
        seen[e['id']] = e
    matched = {e['id'] for e in roster.values()}
    for p in original.values():  # on the map but not a current Wikidata unit (renamed or merged): keep it
        if p['id'] not in matched:
            roster[p['id']] = {'wikidata': None, 'name': p['name'], 'region': p['region'], 'id': p['id'],
                               'sites': [p['original']['link']] if p['original'].get('link') else [],
                               'coordinates': p['original'].get('coordinates'), 'original': p['original']}
    def us(e):  # Wikidata's class also holds Liberian and long-gone US forests
        c = e['coordinates']
        return any('fs.usda.gov' in s or 'fs.fed.us' in s for s in e['sites']) or (c and -170 < c[0] < -60 and 17 < c[1] < 72)
    roster = {k: e for k, e in roster.items() if e['region'] != 'us-forests' or e['original'] or (us(e) and e['sites'])}
    out = sorted(roster.values(), key=lambda e: (e['region'], e['name']))
    json.dump(out, open(ROOT / 'roster.json', 'w'), indent=1, ensure_ascii=False)
    for r in CLASSES:
        rs = [e for e in out if e['region'] == r]
        print(r, len(rs), 'on map:', sum(bool(e['original']) for e in rs), 'no site:', sum(not e['sites'] for e in rs),
              'no coords:', sum(not e['coordinates'] for e in rs))


if __name__ == '__main__':
    main()
