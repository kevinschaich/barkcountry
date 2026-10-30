"""Fetch every park's official pages in bulk with Firecrawl, logging each page like fetch.py does.

    .venv/bin/python scrape.py            # parks not planned yet; skips pages already fetched with a 200
    .venv/bin/python scrape.py --failed   # re-plan and re-fetch only the parks in failed.json

For each park in roster.json:
  1. Missing official site → Firecrawl search restricted to the official domains.
  2. Firecrawl map of the site, searched for dog/pet pages → the most relevant few URLs
     (nps.gov parks also get their standard /planyourvisit/pets.htm).
  3. One Firecrawl batch scrape of every park's home page and dog pages, live (maxAge 0).

Each page is saved to pages/<sha1>.txt and logged in fetch-log.jsonl with via "firecrawl".
Writes sources.json: park id → the official site and the pages scraped for it.
"""
import json, os, re, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from fetch import save
from check import load_log

ROOT = Path(__file__).parent
API = 'https://api.firecrawl.dev/v1'
OFFICIAL = re.compile(r'https?://([a-z0-9-]+\.)*(nps\.gov|fs\.usda\.gov|parks\.canada\.ca|pc\.gc\.ca|sepaq\.com)\b', re.I)
for line in (ROOT / '.env').read_text().splitlines():
    k, _, v = line.partition('=')
    os.environ.setdefault(k.strip(), v.strip())
KEY = os.environ['FIRECRAWL_API_KEY']
DEEP = '--failed' in sys.argv


def call(method, path, body=None):
    for attempt in range(5):
        req = urllib.request.Request(API + path, method=method, data=json.dumps(body).encode() if body else None,
                                     headers={'Authorization': f'Bearer {KEY}', 'Content-Type': 'application/json'})
        try:
            return json.load(urllib.request.urlopen(req, timeout=120))
        except urllib.error.HTTPError as e:
            if e.code in (429, 502, 503) and attempt < 4:
                time.sleep(5 * (attempt + 1)); continue
            return {'success': False, 'error': f'{e.code} {e.read()[:200]!r}'}
        except Exception as e:
            if attempt < 4: time.sleep(5); continue
            return {'success': False, 'error': repr(e)}


def find_site(park):
    official = [s for s in park['sites'] if OFFICIAL.match(s)]
    if official:
        site = official[0].replace('http://', 'https://')
        # pc.gc.ca retired: /en/pn-np/ab/banff/index.aspx → parks.canada.ca/pn-np/ab/banff
        m = re.match(r'https://(?:www\.)?pc\.gc\.ca/(?:\w+/)?(pn-np|lhn-nhs|amnc-nmca)/(\w+)/(\w+)', site)
        return f'https://parks.canada.ca/{m.group(1)}/{m.group(2)}/{m.group(3)}' if m else site
    domain = {'us-parks': 'nps.gov', 'us-forests': 'fs.usda.gov', 'canada-parks': 'parks.canada.ca',
              'quebec-parks': 'sepaq.com'}[park['region']]
    r = call('POST', '/search', {'query': f"{park['name']} site:{domain}", 'limit': 3})
    hits = [x['url'] for x in (r.get('data') or []) if OFFICIAL.match(x.get('url', ''))]
    return hits[0] if hits else None


def dog_pages(park, site):
    m = re.match(r'https://(?:www\.)?nps\.gov/(\w+)', site)
    urls = [f'https://www.nps.gov/{m.group(1)}/planyourvisit/pets.htm'] if m else []
    query = 'chiens animaux' if park['region'] == 'quebec-parks' else 'dogs pets'
    r = call('POST', '/map', {'url': site, 'search': query, 'limit': 8})
    for u in r.get('links') or []:
        u = u if isinstance(u, str) else u.get('url')
        if u and re.search(r'pet|dog|chien|animaux|animal|leash', u, re.I) and u not in urls:
            urls.append(u)
    # Search by content: most forest and Parks Canada dog rules sit on pages without "dog" in the URL
    host = re.match(r'https://([^/]+)', site).group(1)
    # the unit's own slug, since old Wikidata addresses (fs.usda.gov/mendocino) now live at /r05/mendocino
    tail = [t for t in re.sub(r'/index\.html?$', '', site.rstrip('/')).split('/')[3:] if t] or ['']
    slug = tail[-1].lower()
    words = 'chiens animaux' if park['region'] == 'quebec-parks' else 'dogs pets leash'
    hits = []
    queries = [f"{park['name']} {words} site:{host}"]
    if DEEP:  # parks that failed before: several angles, including orders and PDFs
        queries += [f"{park['name']} {q} site:{host}" for q in (
            ['animaux de compagnie règlements', 'chien sentier'] if park['region'] == 'quebec-parks' else
            ['pets allowed trails', 'leash campground', 'forest order animals', 'know before you go', 'regulations'])]
    for q in queries:
        hits += (call('POST', '/search', {'query': q, 'limit': 10}).get('data') or [])
    for x in hits:
        u = x.get('url') if isinstance(x, dict) else None
        title = (x.get('title') or '').lower()
        if u and host.replace('www.', '') in u and (slug in u.lower() or any(w in u.lower() or w in title for w in words_of(park['name']))) and u not in urls:
            urls.append(u)
    return urls[:12 if DEEP else 6]


def words_of(name):
    """Distinctive words of a park's name, e.g. 'gaspesie', 'apache', 'sitgreaves'."""
    import unicodedata
    n = unicodedata.normalize('NFKD', re.sub(r'[\u2010-\u2015]', ' ', name)).encode('ascii', 'ignore').decode().lower()
    stop = {'national', 'park', 'parks', 'forest', 'forests', 'parc', 'de', 'la', 'le', 'du', 'des', 'and',
            'reserve', 'preserve', 'grassland', 'grasslands', 'in', 'of', 'the', 'riviere', 'mount', 'lac'}
    return [w for w in re.findall(r'[a-z]{4,}', n) if w not in stop]


def plan(park):
    site = find_site(park)
    return park['id'], {'site': site, 'urls': ([site] + dog_pages(park, site)) if site else []}


def batch(urls):
    job = call('POST', '/batch/scrape', {'urls': urls, 'formats': ['markdown'], 'onlyMainContent': True,
                                         'maxAge': 0, 'ignoreInvalidURLs': True})
    if not job.get('success'): raise SystemExit(f'batch failed: {job}')
    url, done = f"/batch/scrape/{job['id']}", {}
    while True:
        r = call('GET', url)
        status = r.get('status')
        print(f"batch {status}: {r.get('completed')}/{r.get('total')}", flush=True)
        if status in ('completed', 'failed', 'cancelled'):
            page = r
            while True:
                for d in page.get('data') or []:
                    meta = d.get('metadata') or {}
                    src = meta.get('sourceURL') or meta.get('url')
                    done[src] = save(src, d.get('markdown') or '', meta.get('statusCode') or meta.get('error') or 'error', 'firecrawl')
                if not page.get('next'): break
                page = call('GET', page['next'].replace(API, ''))
            break
        time.sleep(10)
    for u in urls:
        if u not in done:
            done[u] = save(u, '', 'not returned by firecrawl', 'firecrawl')
    return done


def main():
    roster = json.load(open(ROOT / 'roster.json'))
    path = ROOT / 'sources.json'
    sources = json.load(open(path)) if path.exists() else {}
    if '--failed' in sys.argv:
        failed = set(json.load(open(ROOT / 'redo.json')))  # written by digest.py
        for pid in failed: sources.pop(pid, None)
    todo = [p for p in roster if p['id'] not in sources]
    with ThreadPoolExecutor(8) as ex:
        for pid, s in ex.map(plan, todo):
            sources[pid] = s
            print('planned', pid, len(s['urls']), flush=True)
    json.dump(sources, open(path, 'w'), indent=1)
    log = load_log()
    urls = sorted({u for s in sources.values() for u in s['urls'] if (log.get(u) or {}).get('status') != 200})
    print(len(urls), 'pages to scrape', flush=True)
    batch(urls)


if __name__ == '__main__':
    main()
