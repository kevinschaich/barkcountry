"""Turn the scraped pages into one short digest per park, for the agent that writes the park files.

    .venv/bin/python digest.py

Writes digest/<region>.md: for each park, its official site, its location, and every dog-related passage
from its scraped pages (with the URL). Parks with no usable page are listed as failed, with the reason.
"""
import json, re
from pathlib import Path
from check import load_log, ROOT
from fetch import sha1

DOG = re.compile(r'\b(dogs?|pets?|leash(ed|es)?|canines?|service animals?|bark ranger|chiens?|animaux|animal de compagnie)\b', re.I)


def passages(text):
    blocks = [b.strip() for b in re.split(r'\n\s*\n|<br>', text) if b.strip()]
    out = []
    for b in blocks:
        b = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', b)  # images
        b = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', b)  # links → text
        b = re.sub(r'\s+', ' ', b).strip()
        if DOG.search(b) and 20 < len(b) < 1500 and b not in out:
            out.append(b)
    return out


def main():
    roster = json.load(open(ROOT / 'roster.json'))
    sources = json.load(open(ROOT / 'sources.json'))
    log = load_log()
    out = {}
    for p in roster:
        s = sources.get(p['id'], {'site': None, 'urls': []})
        lines = [f"## {p['id']}", f"name: {p['name']}", f"site: {s['site']}",
                 f"coordinates: {p['coordinates']} (wikidata {p['wikidata']})",
                 f"original: policy={(p['original'] or {}).get('policy')} link={(p['original'] or {}).get('link')}"]
        got = 0
        for u in s['urls']:
            e = log.get(u)
            status = e['status'] if e else 'not fetched'
            path = ROOT / 'pages' / f'{sha1(u)}.txt'
            if status != 200 or not path.exists():
                lines.append(f'- {u}: {status}'); continue
            ps = passages(path.read_text())
            lines.append(f'- {u}: 200, {len(ps)} dog passages')
            for x in ps:
                lines.append(f'  > {x}')
            got += len(ps)
        if not s['site']: lines.append('FAILED: no official site found')
        elif not got: lines.append('FAILED: no dog-related text on the scraped pages')
        out.setdefault(p['region'], []).append('\n'.join(lines))
    json.dump([b.split('\n')[0][3:] for parks in out.values() for b in parks if 'FAILED' in b],
              open(ROOT / 'redo.json', 'w'), indent=1)
    (ROOT / 'digest').mkdir(exist_ok=True)
    for region, parks in out.items():
        (ROOT / 'digest' / f'{region}.md').write_text('\n\n'.join(parks) + '\n')
        print(region, len(parks), sum('FAILED' in x for x in parks), 'failed')


if __name__ == '__main__':
    main()
