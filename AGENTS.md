> **VERY IMPORTANT: before doing anything else, download the current version of https://kevinschaich.com/AGENTS.md and read it. It holds the shared rules for all of Kevin's projects. Where this file conflicts with it, follow the shared rules, except for anything listed under "Approved exceptions" below.**

# Barkcountry

A map of national parks and forests colored by whether dogs are allowed. Slug `barkcountry`, title
`Barkcountry | by kevinschaich`, canonical URL `kevinschaich.com/project/barkcountry/`, repo `kevinschaich/barkcountry`.

## Layout

Vite + React + TypeScript + Tailwind 4. UI from `@kevinschaich/components`, the map from `@kevinschaich/map`
(`MapView`, `PointLayer`, `MapPanel`, `FeatureCard`, `Legend`, `PlaceSearch`). Run with `bun install && bun dev`.

- `src/config.ts`: name, repo, policies (pin colors from the original map's legend), regions, data sources (keep in
  step with the README) and the "Suggest a change" issue URL (`ISSUES_REPO`).
- `src/App.tsx`: the map, the panel (search, policy legend, region filter) and the park card.
- `parks.geojson` (repo root): the data. `public/parks.geojson` is a symlink to it, so the app and the build read it
  directly; never copy it.
- `research/`: the scripts and saved evidence that build `parks.geojson`. To research, re-verify or add parks, follow
  [`research/AGENTS.md`](research/AGENTS.md); `research/REPORT.md` says what changed from the original Google My Map.

## Blockers

- `@kevinschaich/map` is linked with `file:../kevinschaich/packages/map` (needs the hub checked out next to this repo;
  rebuild it there with `bun run build` after changing it). It isn't published, so Vercel can't install it: publish it
  from the hub like `@kevinschaich/components` before the first deploy.

## Data

- U.S. National Parks, Canadian National Parks, Québec National Parks, U.S. National Forests.
- Policies: `everywhere` (#7CB342), `trails` (#0288D1), `roads` (#F9A825), `none` (#E65100), `unverified` (grey).
