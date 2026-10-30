import { Badge, Byline, Separator } from '@kevinschaich/components'
import { BasemapTabs, FeatureCard, Legend, MapPanel, MapView, PlaceSearch, PointLayer, useMap, type SearchHit } from '@kevinschaich/components/map'
import { ArrowUpRight, BadgeCheck, MessageSquarePlus, Download, Trees } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { NAME, POLICIES, POLICY, REGION, REGIONS, REPO, SOURCES, suggestUrl, type Park, type Region } from './config'

type Parks = GeoJSON.FeatureCollection<GeoJSON.Point, Park>

const store = <T,>(k: string, fallback: T): T => {
    try {
        return JSON.parse(localStorage.getItem(k) ?? 'null') ?? fallback
    } catch {
        return fallback
    }
}
const save = (k: string, v: unknown) => {
    try {
        localStorage.setItem(k, JSON.stringify(v))
    } catch {}
}

/** The parks map: a panel (search, policy legend, region filter) and a card for the chosen park. */
export function App() {
    const [parks, setParks] = useState<Parks | null>(null)
    const [hiddenPolicies, setHiddenPolicies] = useState<string[]>(() => store('hiddenPolicies', []))
    const [regions, setRegions] = useState<Region[]>(() => store('regions', REGIONS.map((r) => r.value)))
    const [selected, setSelected] = useState<string | null>(null)

    useEffect(() => {
        fetch('parks.geojson')
            .then((r) => r.json())
            .then(setParks)
            .catch(() => setParks({ type: 'FeatureCollection', features: [] }))
    }, [])
    useEffect(() => save('hiddenPolicies', hiddenPolicies), [hiddenPolicies])
    useEffect(() => save('regions', regions), [regions])

    const byId = useMemo(() => new Map(parks?.features.map((f) => [f.properties.id, f]) ?? []), [parks])
    const park = selected ? byId.get(selected)?.properties : undefined
    const hiddenRegions = REGIONS.map((r) => r.value).filter((r) => !regions.includes(r))

    return (
        <MapView center={[-104, 46]} zoom={3} storageKey="dog-parks" sources={SOURCES} onBackgroundClick={() => setSelected(null)}>
            {parks && (
                <>
                    <PointLayer
                        id="parks"
                        data={parks as GeoJSON.FeatureCollection}
                        color={{ property: 'policy', colors: Object.fromEntries(POLICIES.map((p) => [p.value, p.color])) }}
                        hide={{ property: 'policy', values: hiddenPolicies }}
                        filter={['in', ['get', 'region'], ['literal', regions]]}
                        selectedId={selected}
                        onSelect={(f) => setSelected(String(f.properties.id))}
                        radius={6}
                        label="name"
                        labelMinZoom={6}
                    />
                    <Panel
                        parks={parks}
                        hiddenPolicies={hiddenPolicies}
                        setHiddenPolicies={setHiddenPolicies}
                        regions={regions}
                        setRegions={setRegions}
                        hiddenRegions={hiddenRegions}
                        select={setSelected}
                    />
                </>
            )}
            {park && <ParkCard park={park} onClose={() => setSelected(null)} />}
        </MapView>
    )
}

function Panel({
    parks,
    hiddenPolicies,
    setHiddenPolicies,
    regions,
    setRegions,
    hiddenRegions,
    select,
}: {
    parks: Parks
    hiddenPolicies: string[]
    setHiddenPolicies: (h: string[]) => void
    regions: Region[]
    setRegions: (r: Region[]) => void
    hiddenRegions: Region[]
    select: (id: string) => void
}) {
    const { map } = useMap()
    const search = (q: string): SearchHit[] => {
        const words = q.toLowerCase().split(/\s+/).filter(Boolean)
        return parks.features
            .filter((f) => words.every((w) => f.properties.name.toLowerCase().includes(w)))
            .slice(0, 6)
            .map((f) => ({
                key: f.properties.id,
                label: f.properties.name,
                detail: POLICY[f.properties.policy].short,
                icon: <Trees />,
                onSelect: () => {
                    // Make sure the chosen park isn't filtered out.
                    const p = f.properties
                    if (hiddenPolicies.includes(p.policy)) setHiddenPolicies(hiddenPolicies.filter((h) => h !== p.policy))
                    if (hiddenRegions.includes(p.region)) setRegions([...regions, p.region])
                    select(p.id)
                    map.flyTo({ center: f.geometry.coordinates as [number, number], zoom: Math.max(map.getZoom(), 7) })
                },
            }))
    }

    // Each count follows the other filter, so the numbers match what's on the map
    const count = (key: 'policy' | 'region', value: string) =>
        parks.features.filter(
            (f) =>
                f.properties[key] === value &&
                (key === 'policy' ? regions.includes(f.properties.region) : !hiddenPolicies.includes(f.properties.policy)),
        ).length
    const countBadge = (n: number) => <span className="text-xs text-muted-foreground tabular-nums">{n}</span>

    return (
        <MapPanel title={NAME} description="Find national parks where your dog can hike with you" className="sm:w-96">
            <PlaceSearch searchFeatures={search} featuresHeading="Parks" placeholder="Search a park or place" />
            <Legend
                items={POLICIES.map((p) => ({ value: p.value, label: p.label, color: p.color, extra: countBadge(count('policy', p.value)) }))}
                hidden={hiddenPolicies}
                onHiddenChange={setHiddenPolicies}
            />
            <Separator />
            <div className="flex flex-col gap-2">
                <span className="text-sm font-medium">Show</span>
                <Legend
                    items={REGIONS.map((r) => ({ value: r.value, label: r.long + 's', extra: countBadge(count('region', r.value)) }))}
                    hidden={hiddenRegions}
                    onHiddenChange={(h) => setRegions(REGIONS.map((r) => r.value).filter((r) => !h.includes(r)))}
                />
            </div>
            <Separator />
            <div className="flex flex-col gap-2">
                <span className="text-sm font-medium">Basemap</span>
                <BasemapTabs />
            </div>
            <Separator />
            <a
                href={suggestUrl()}
                target="_blank"
                rel="noopener"
                className="inline-flex items-center gap-1.5 text-sm text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
            >
                <MessageSquarePlus className="size-4" /> Suggest a park
            </a>
            <a
                href="parks.geojson"
                download="barkcountry-parks.geojson"
                className="inline-flex items-center gap-1.5 text-sm text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
            >
                <Download className="size-4" /> Download data
            </a>
            <Byline repo={REPO} />
        </MapPanel>
    )
}

const linkClass = 'inline-flex items-center gap-1 text-sm text-muted-foreground underline-offset-4 hover:text-foreground hover:underline'

const fmtDate = (d: string) => new Date(`${d}T12:00:00`).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })

function ParkCard({ park, onClose }: { park: Park; onClose: () => void }) {
    const policy = POLICY[park.policy]
    const site = park.officialUrl ?? park.link ?? `https://duckduckgo.com/?q=${encodeURIComponent(`${park.name} official site`)}`
    return (
        <FeatureCard
            title={park.name}
            subtitle={REGION[park.region].long}
            onClose={onClose}
            badge={
                <Badge className="text-zinc-950" style={{ background: policy.color }}>
                    {policy.label}
                </Badge>
            }
            footer={
                <div className="flex flex-col gap-1.5 border-t pt-3">
                    <a href={site} target="_blank" rel="noopener" className={linkClass}>
                        {park.officialUrl || park.link ? 'Official park site' : 'Find the official site'} <ArrowUpRight className="size-3.5" />
                    </a>
                    <a href={suggestUrl(park)} target="_blank" rel="noopener" className={linkClass}>
                        Suggest a change <ArrowUpRight className="size-3.5" />
                    </a>
                </div>
            }
        >
            {park.verified ? (
                <>
                    <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-sm" title="Checked against the park's official page">
                        <span className="inline-flex items-center gap-1 font-medium text-[#1D9BF0]">
                            <BadgeCheck className="size-4 fill-[#1D9BF0] text-white" /> Verified
                        </span>
                        {park.lastVerified && <span className="text-muted-foreground">Last verified {fmtDate(park.lastVerified)}</span>}
                    </div>
                    {park.summary && <p className="font-medium">{park.summary}</p>}
                    {park.excerpts?.map((e, i) => (
                        <blockquote key={i} className="border-l-2 pl-3 text-muted-foreground italic">
                            “{e.quote}”{' '}
                            <a href={e.url} target="_blank" rel="noopener" className="not-italic underline underline-offset-4 hover:text-foreground">
                                Source
                            </a>
                        </blockquote>
                    ))}
                    {!!park.dogRules?.length && (
                        <ul className="flex list-disc flex-col gap-1 pl-5 text-sm">
                            {park.dogRules.map((r, i) => (
                                <li key={i}>
                                    <a href={r.url} target="_blank" rel="noopener" className="underline-offset-4 hover:underline">
                                        {r.text}
                                    </a>
                                </li>
                            ))}
                        </ul>
                    )}
                </>
            ) : (
                <p className="text-muted-foreground">No verified data yet.</p>
            )}
            <p className="text-xs text-muted-foreground">Rules change: check with the park before you go.</p>
        </FeatureCard>
    )
}
