# Researching dog rules: instructions for agents

This folder holds the research behind the map: each park's color (policy), its card, a "last verified"
date and a verified check. Follow these steps exactly every time the research is redone. The check is only
trustworthy because scripts, not agents, record what was fetched and test what was quoted.

## Ground rules

- **Official pages only:** nps.gov, fs.usda.gov, parks.canada.ca, sepaq.com, and the forest orders and
  closure orders they publish. Never use memory, search-result snippets, a fetch tool's summary or a
  third-party site as the source of a rule.
- **Every page goes through `fetch.py`:** `.venv/bin/python fetch.py <url>`. It sends an honest user agent,
  waits 3 s between requests to the same host, saves the page text to `pages/` and appends the real status
  and time to `fetch-log.jsonl`. Never write the log or a page file by hand.
  - sepaq.com blocks scripts. Open those pages in the built-in browser pane, then pipe the page text into
    `.venv/bin/python save_browser.py <url> 200`.
  - Never disguise a request as a browser.
- **You may search to find URLs** (WebSearch, or the site's own search). Then fetch the page itself with
  `fetch.py` and read the saved text.
- **One agent at a time.** Parallel crawlers got the hosts to block us, and their logs couldn't be trusted.
- **Failures don't change anything.** If a park's pages can't be fetched or read, or they say nothing about
  dogs, write the park file with `"failed": {"why": "...", "urls": [...]}`. `check.py` puts it in the failed
  category, shown as "no verified data" until it's redone. Missing data is never "not allowed".

## Setup

```sh
cd research
python3 -m venv .venv && .venv/bin/pip install pypdf
```

## Pipeline

1. `roster.py`: the full park list (US national parks, US national forests, Parks Canada, Québec) from
   Wikidata → `roster.json`. Parks already on the map keep their ids and original data.
2. `scrape.py`: finds each park's official site and dog pages (Firecrawl search and map), then fetches them
   all in one Firecrawl batch. It needs `FIRECRAWL_API_KEY` in `research/.env`, which is git-ignored and must
   never be committed. Pages land in `pages/`, and every fetch, with its status, is in `fetch-log.jsonl`.
   `sources.json` maps each park to the pages scraped for it. Pages that already loaded with a 200 are never
   fetched again. `scrape.py --failed` redoes only the parks in `failed.json`.
3. `digest.py`: every dog-related passage per park → `digest/<region>.md`, for the agent.
4. An agent writes `parks/<id>.json` for each park from the digest (below), one region at a time, quoting
   only text that's in the saved pages.
5. `check.py`: verifies and builds everything (see Outputs).

`fetch.py` and `save_browser.py` are for single pages Firecrawl can't get.

## Writing each park file

1. Read the park's section of `digest/<region>.md`. Open `pages/<sha1>.txt` when you need more context.
2. Write `parks/<id>.json`:

```json
{
  "id": "acadia-national-park",
  "name": "Acadia National Park",
  "policy": "everywhere | trails | roads | none",
  "policyReason": "one sentence, required when the policy differs from parks.json's original",
  "summary": "one plain sentence for the top of the card",
  "excerpts": [{ "quote": "a sentence copied word for word from the page", "url": "..." }],
  "dogRules": [{ "text": "a short plain-English bullet", "url": "..." }],
  "officialUrl": "the park's home page",
  "petsUrl": "the park's pets page, or null",
  "coordinates": [-68.21, 44.35],
  "coordinatesSource": "Wikipedia: Acadia National Park"
}
```

- **policy**:
  - `everywhere`: allowed on most trails and areas
  - `trails`: allowed on at least one named trail (or a beach or open area away from roads), but not most
  - `roads`: allowed only where cars go (roads, parking, campgrounds, picnic and developed areas) and on no
    trail at all. A paved path in a developed area or campground doesn't count as a trail.
  - `none`: not allowed at all (service animals aside)
- **excerpts** are what the site shows as quotes from the park's own page. Copy each one exactly, from a
  single sentence up to a short paragraph. They must contain the sentences the policy rests on. `check.py`
  rejects any excerpt that isn't word for word in the saved page.
- **dogRules** are the card's bullets: every dog-related rule on the pages you read, each with its URL.
  This covers where dogs are allowed and where they're banned (every named trail or area), leash rules,
  campgrounds, beaches, buildings, lodging, shuttles and boats, seasonal and wildlife closures, heat,
  kennels, BARK Ranger and service animals. Leave out rules that are the same in every park of the system;
  put those in `network/<region>.json` instead, as a `{text, url}` array.
- **coordinates**: a point inside the park, from the Wikipedia page summary API
  (`https://en.wikipedia.org/api/rest_v1/page/summary/<Title>`, fetched with `fetch.py`) or OSM Nominatim.
  For combined forests, make sure the point lands in the right unit.
- **Renamed or merged units** (for example Uinta → Uinta-Wasatch-Cache): put the current official name in
  `name`.

3. Run `.venv/bin/python check.py`. Fix anything it lists for your park, or mark the park failed.

## Outputs (all written by `check.py`)

- `../parks.geojson`: what the site renders. Verified parks have `verified: true` and `lastVerified`;
  failed and pending parks get `policy: "unverified"` (shown as "no verified data"), never "none" or the old color.
- `progress.json`: counts by status and region, read by `progress.html`.
- `failed.json`: the failed category, to redo.
- `REPORT.md`: every change against the original map, why, and the quoted sources.

## Watching progress

```sh
python3 -m http.server 8765 --directory research
```

Then open <http://localhost:8765/progress.html>.
