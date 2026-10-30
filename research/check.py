"""Check every park against its saved evidence, then build the site data, the progress file and the report.

    .venv/bin/python check.py

A park gets the verified check only if this script can prove it: every cited page was fetched with a
200 (the fetch log says so), every excerpt appears word for word in that page's saved text, and every
field the site needs is present. Anything else lands in the "failed" category with the reasons.

Writes:
  progress.json         counts and per-park status (the progress page reads it)
  ../parks.geojson      verified parks for the site; failed parks keep their original data, marked unverified
  failed.json           the failed parks and why, to redo
  REPORT.md             what changed against the original map, why, with citations
"""
import json, re, unicodedata
from datetime import datetime, timezone
from pathlib import Path
from fetch import sha1

ROOT = Path(__file__).parent
POLICIES = ['everywhere', 'trails', 'roads', 'none']
REGION = {'us-parks': 'US national park', 'us-forests': 'US national forest', 'canada-parks': 'Parks Canada',
          'quebec-parks': 'Québec national park'}
LABEL = {'everywhere': 'allowed (almost) everywhere', 'trails': 'allowed on one or more trails',
         'roads': 'allowed only where cars can go', 'none': 'not allowed'}


def norm(s: str) -> str:
    s = unicodedata.normalize('NFKC', s).lower()
    s = re.sub(r'[‘’‛`]', "'", s)
    s = re.sub(r'[“”„]', '"', s)
    s = re.sub(r'[‐-―]', '-', s)
    return re.sub(r'\s+', ' ', s).strip()


def load_log() -> dict:
    latest = {}
    log = ROOT / 'fetch-log.jsonl'
    if log.exists():
        for line in log.read_text().splitlines():
            e = json.loads(line)
            latest[e['url']] = e
    return latest


def page(url: str):
    p = ROOT / 'pages' / f'{sha1(url)}.txt'
    return norm(p.read_text()) if p.exists() else None


def check(park: dict, log: dict) -> tuple[list, list]:
    """Return (problems, fetch entries used)."""
    problems, used = [], {}
    if park.get('failed'):
        return [f"research failed: {park['failed'].get('why')}"], []

    def cite(url, what):
        e = log.get(url)
        if not e:
            problems.append(f'{what}: {url} was never fetched by fetch.py or save_browser.py'); return None
        used[url] = e
        if e['status'] != 200:
            problems.append(f"{what}: {url} returned {e['status']}"); return None
        return page(url)

    if park.get('policy') not in POLICIES: problems.append(f"policy missing or invalid: {park.get('policy')!r}")
    if not park.get('summary'): problems.append('summary missing')
    if not park.get('officialUrl'): problems.append('officialUrl missing')
    else: cite(park['officialUrl'], 'officialUrl')
    c = park.get('coordinates')
    if not (isinstance(c, list) and len(c) == 2 and all(isinstance(v, (int, float)) for v in c)
            and -180 <= c[0] <= 180 and -90 <= c[1] <= 90 and c != [0, 0]):
        problems.append(f'coordinates missing or invalid: {c!r}')
    if not park.get('coordinatesSource'): problems.append('coordinatesSource missing')

    excerpts = park.get('excerpts') or []
    if not excerpts: problems.append('no excerpts: the policy must rest on at least one quoted official sentence')
    for x in excerpts:
        text = cite(x.get('url'), 'excerpt')
        if text is not None and norm(x.get('quote', '')) not in text:
            problems.append(f"excerpt not found word for word in {x.get('url')}: {x.get('quote', '')[:80]!r}")
    for r in park.get('dogRules') or []:
        cite(r.get('url'), 'dogRule')
    if park.get('policyChanged') and not park.get('policyReason'):
        problems.append('policy differs from the original map but policyReason is missing')
    return problems, list(used.values())


def main():
    index = json.load(open(ROOT / 'roster.json'))
    log = load_log()
    sources = json.load(open(ROOT / 'sources.json')) if (ROOT / 'sources.json').exists() else {}
    rows, features, failed, report, excluded, added, corrections, moves = [], [], [], [], [], [], [], {}
    for item in index:
        f = ROOT / 'parks' / f"{item['id']}.json"
        orig = item['original'] or {'policy': None, 'description': None, 'link': None, 'coordinates': None}
        if not f.exists():
            rows.append({'id': item['id'], 'name': item['name'], 'region': item['region'], 'status': 'pending'})
            continue
        park = json.load(open(f))
        if park.get('excluded'):
            excluded.append(f"- **{item['name']}** ({item['region']}): {park['excluded']}")
            continue  # not a place visitors can go, so not on the map
        park['policyChanged'] = park.get('policy') != orig['policy']
        problems, used = check(park, log)
        ok = not problems
        last = min((e['fetched'] for e in used if e['status'] == 200), default=None)
        if any('duplicate of' in x for x in problems):
            continue  # a second listing of a park counted elsewhere, not a park of its own
        rows.append({'id': item['id'], 'name': item['name'], 'region': item['region'],
                     'status': 'verified' if ok else 'failed', 'lastVerified': last if ok else None,
                     'problems': problems})
        if ok:
            features.append({'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': park['coordinates']},
                             'properties': {
                                 'id': item['id'], 'name': park.get('name') or item['name'], 'region': item['region'],
                                 'policy': park['policy'], 'summary': park['summary'],
                                 'excerpts': park['excerpts'], 'dogRules': park.get('dogRules', []),
                                 'link': park.get('petsUrl') or park['officialUrl'],
                                 'officialUrl': park['officialUrl'],
                                 'verified': True, 'lastVerified': last[:10]}})
            cites = '\n'.join(f"  - “{x['quote']}” <{x['url']}>" for x in park['excerpts'])
            head = f"### {park.get('name') or item['name']} ({REGION[item['region']]})"
            if orig['policy'] is None:
                added.append(f"{head}\n\n- **Shown as:** {LABEL[park['policy']]}\n- **Sources** (fetched {last[:10]}):\n{cites}\n")
            elif park['policyChanged']:
                moves[(orig['policy'], park['policy'])] = moves.get((orig['policy'], park['policy']), 0) + 1
                report.append(f"{head}\n\n- **Was:** {LABEL[orig['policy']]}\n- **Now:** {LABEL[park['policy']]}\n"
                              f"- **Why:** {park['policyReason']}\n- **Sources** (fetched {last[:10]}):\n{cites}\n")
            other = []
            if orig['policy'] is not None:
                if park.get('name') and park['name'] != item['name']:
                    other.append(f"name {item['name']} → {park['name']}")
                if park.get('unit'):
                    other.append(f"now part of {park['unit']}")
                if orig.get('coordinates') is None:
                    other.append(f"location added ({park['coordinatesSource']})")
                if (orig.get('link') or '') != (park.get('petsUrl') or park['officialUrl']):
                    other.append(f"link {orig.get('link') or 'missing'} → {park.get('petsUrl') or park['officialUrl']}")
            if other:
                corrections.append(f"- **{item['name']}**: " + '; '.join(other))
        else:
            failed.append({'id': item['id'], 'name': item['name'], 'region': item['region'], 'problems': problems,
                           'failedUrls': (park.get('failed') or {}).get('urls', [])})
            point = item.get('coordinates') or orig.get('coordinates')
            if point and not any('duplicate of' in x for x in problems):
                # No verified data: shown in its own color, never as "not allowed" or the old guess
                features.append({'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': point},
                                 'properties': {'id': item['id'], 'name': item['name'], 'region': item['region'],
                                                'policy': 'unverified', 'link': (sources.get(item['id']) or {}).get('site')
                                                or orig.get('link'), 'verified': False}})

    counts = {s: sum(r['status'] == s for r in rows) for s in ['verified', 'failed', 'pending']}
    by_region = {}
    for r in rows:
        by_region.setdefault(r['region'], {'verified': 0, 'failed': 0, 'pending': 0})[r['status']] += 1
    now = datetime.now(timezone.utc).isoformat(timespec='seconds')
    json.dump({'updated': now, 'total': len(rows), 'counts': counts, 'byRegion': by_region, 'parks': rows},
              open(ROOT / 'progress.json', 'w'), indent=1, ensure_ascii=False)
    json.dump(failed, open(ROOT / 'failed.json', 'w'), indent=1, ensure_ascii=False)
    json.dump({'type': 'FeatureCollection', 'features': features},
              open(ROOT.parent / 'parks.geojson', 'w'), indent=1, ensure_ascii=False)
    matrix = '\n'.join(f"| {LABEL[a]} | {LABEL[b]} | {n} |" for (a, b), n in sorted(moves.items(), key=lambda m: -m[1]))
    (ROOT / 'REPORT.md').write_text(
        f"# What changed\n\nGenerated by `research/check.py` on {now[:10]}: {counts['verified']} of {len(rows)} parks "
        f"verified against their official pages. Only differences from the original map are listed. Every one rests on "
        f"official pages saved in `research/pages/`, fetched as logged in `research/fetch-log.jsonl`.\n\n"
        f"## Color changes ({sum(moves.values())})\n\n| Was | Now | Parks |\n|---|---|---|\n{matrix}\n\n" + '\n'.join(report)
        + f"\n## Added to the map ({len(added)})\n\n" + '\n'.join(added)
        + f"\n## Other corrections ({len(corrections)})\n\n" + '\n'.join(corrections) + '\n'
        + ("\n## Left off the map\n\n" + '\n'.join(excluded) + '\n' if excluded else '')
        + (f"\n## Failed ({len(failed)})\n\n" + '\n'.join(f"- **{x['name']}** ({x['region']}): {'; '.join(x['problems'])}" for x in failed) + '\n' if failed else ''))
    print(json.dumps({'counts': counts, 'byRegion': by_region}))


if __name__ == '__main__':
    main()
