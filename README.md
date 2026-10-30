[![Barkcountry by kevinschaich](https://kevinschaich.com/og/barkcountry.png)](https://kevinschaich.com/project/barkcountry/)

# Barkcountry

Find national parks where your dog can hike with you

**[Try it →](https://kevinschaich.com/project/barkcountry/)**

## How it works

- Every U.S. and Canadian national park, Québec national park and U.S. national forest on one map, colored by its pet
  policy: allowed (almost) everywhere, on one or more trails, only where cars can go, or not at all.
- Search finds parks first, then any town or address. Pick a park for its dog rules, quotes from its official pages and
  a link to its site. Always check the park's own rules before you go.
- It started as a Google My Map; every park has since been checked against its official pages (see Research).
- Something out of date or missing? Use "Suggest a change" on a park or "Suggest a park", which open a pre-filled
  [GitHub issue](https://github.com/kevinschaich/barkcountry/issues).

## Research

`parks.geojson` holds every park with its color, quotes from its official pages and a "last verified" date. The app
reads it directly. It's built by the scripts in [`research/`](research/), and every page they read is saved there as
evidence. See [`research/REPORT.md`](research/REPORT.md) for what changed from the original map, and
[`research/AGENTS.md`](research/AGENTS.md) for how to redo it.

## Data sources

| What | From | License |
| --- | --- | --- |
| Park pet policies and locations | Kevin Schaich's research of each park's official pages ([`research/`](research/)) | © Kevin Schaich |
| Pet rules, quotes and summaries | Each park's official website, such as the [U.S. National Park Service](https://www.nps.gov) | Quoted for reference |
| Dark and Streets basemaps | [OpenStreetMap contributors](https://www.openstreetmap.org/copyright) | ODbL |
| Satellite basemap | [USGS The National Map](https://www.usgs.gov/programs/national-geospatial-program/national-map) | Public domain |
| Place search | [Photon by Komoot](https://photon.komoot.io) | OSM data, ODbL |

## Run locally

```sh
bun install && bun dev
```
