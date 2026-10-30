import type { DataSource } from '@kevinschaich/components'
import { BASEMAP_SOURCES, PHOTON_SOURCE } from '@kevinschaich/map'

export const NAME = 'Barkcountry'
export const REPO = 'kevinschaich/barkcountry'
/** Where "Suggest a change" opens a new issue. */
export const ISSUES_REPO = REPO

export type Policy = 'everywhere' | 'trails' | 'roads' | 'none' | 'unverified'
export type Region = 'us-parks' | 'us-forests' | 'canada-parks' | 'quebec-parks'
export type Park = {
    id: string
    name: string
    policy: Policy
    region: Region
    link: string | null
    verified: boolean
    summary?: string
    excerpts?: { quote: string; url: string }[]
    dogRules?: { text: string; url: string }[]
    officialUrl?: string
    lastVerified?: string
}

// The original map's pin colors and legend.
export const POLICIES: { value: Policy; label: string; short: string; color: string }[] = [
    { value: 'everywhere', label: 'Dogs welcome (almost) everywhere', short: 'Almost everywhere', color: '#7CB342' },
    { value: 'trails', label: 'Dogs allowed on some trails', short: 'Some trails', color: '#0288D1' },
    { value: 'roads', label: 'Dogs allowed where cars can go', short: 'Where cars go', color: '#F9A825' },
    { value: 'none', label: 'No dogs allowed', short: 'No dogs', color: '#E65100' },
    // Not researched yet: neutral grey, never read as "no dogs".
    { value: 'unverified', label: 'No verified data', short: 'No verified data', color: '#A1A1AA' },
]
export const POLICY = Object.fromEntries(POLICIES.map((p) => [p.value, p])) as Record<Policy, (typeof POLICIES)[number]>

export const REGIONS: { value: Region; label: string; long: string }[] = [
    { value: 'us-parks', label: 'US parks', long: 'U.S. National Park' },
    { value: 'us-forests', label: 'US forests', long: 'U.S. National Forest' },
    { value: 'canada-parks', label: 'Canada', long: 'Canadian National Park' },
    { value: 'quebec-parks', label: 'Québec', long: 'Québec National Park' },
]
export const REGION = Object.fromEntries(REGIONS.map((r) => [r.value, r])) as Record<Region, (typeof REGIONS)[number]>

// Keep in step with the README.
export const SOURCES: DataSource[] = [
    { what: 'Park pet policies and locations', from: "Kevin Schaich's research of each park's official pages", href: 'https://github.com/kevinschaich/barkcountry/blob/main/research/REPORT.md', license: '© Kevin Schaich' },
    { what: 'Pet rules, quotes and summaries', from: "Each park's official website (linked on its card)", href: 'https://www.nps.gov', license: 'Quoted for reference' },
    ...BASEMAP_SOURCES,
    PHOTON_SOURCE,
]

export const suggestUrl = (park?: Park) => {
    const title = park ? `Change: ${park.name}` : 'Suggest a park'
    const body = park
        ? `**Park:** ${park.name}\n**Shown as:** ${POLICY[park.policy].label}\n\n**What should change?**\n\n\n**Source (park website or rules page):**\n`
        : `**Park name and where it is:**\n\n**Are dogs allowed? Where?**\n\n**Source (park website or rules page):**\n`
    return `https://github.com/${ISSUES_REPO}/issues/new?${new URLSearchParams({ title, body })}`
}
