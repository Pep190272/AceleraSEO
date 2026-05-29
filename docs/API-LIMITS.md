# Verified API limits & constraints (research log)

Every constraint here was verified against primary/authoritative sources in May 2026. These facts **define the architecture** — read before proposing any "magic" feature.

## 1. Backlink index — NOT replicable open source

| Fact | Value (2025) | Source |
|------|-------------|--------|
| Ahrefs pages indexed | 456.5 billion | ahrefs.com/big-data |
| External backlinks | 35 trillion | ahrefs.com/big-data |
| Crawl rate | 8B+ pages/day | Ahrefs stats |
| Infrastructure | 3,600 servers · 691K cores · 4PB RAM · ~500PB SSD | ahrefs.com/big-data |
| Cloud spend | ~$900M / 3 years (~$300M/yr) | Ahrefs stats |

**Conclusion:** The moat is the *data*, not the code. No OSS project can build a web-scale link graph.
→ **Design decision:** backlink data = third-party API integration with the user's own key. We do NOT crawl the web.

## 2. Google Indexing API — JobPosting / BroadcastEvent ONLY

- Officially supports **only** pages with `JobPosting` or `BroadcastEvent` (in `VideoObject`) structured data.
- Google **ignores** requests for blog posts, products, category pages.
- John Mueller (Bluesky, May 2025): *"We see a lot of spammers misuse the Indexing API like this, so I'd recommend just sticking to the documented & supported use-cases."*
- Gary Illyes: API may stop supporting unsupported formats without notice.
- Default quota: 200 publish/day.
- Source: developers.google.com/search/apis/indexing-api/v3/using-api

→ **Design decision:** We do NOT use the Indexing API for general pages. Doing so risks penalties.

## 3. URL Inspection API — READ ONLY

- Returns index status, coverage, rich-results, mobile usability.
- **Does NOT submit URLs for indexing.** There is no programmatic "request indexing" for Google.
- Quota: 2,000 queries/day, 600/min.
- Source: developers.google.com/webmaster-tools/v1/urlInspection.index/inspect

→ **Design decision:** Use it to *monitor* index status and *alert* when Google hasn't indexed a URL — not to force it.

## 4. IndexNow — instant indexing, but NOT Google

- Supported: **Bing, Yandex, Naver, Seznam, Yep.**
- **Google does NOT support it** (testing since Oct 2021, still out as of Feb 2026).
- Real impact: 22% of Bing clicked URLs originate from IndexNow; 5B+ submissions/day.
- Source: indexnow.org, en.wikipedia.org/wiki/IndexNow

→ **Design decision:** IndexNow = our instant-ACT channel for everything except Google. For Google: sitemap + internal links + monitoring.

## 5. The READ side is fully open (this is our power)

| API | Gives us | Cost |
|-----|----------|------|
| **GSC Search Analytics API** | 16 months: clicks, impressions, position, CTR by query/page | Free |
| **GA4 Data API** | sessions, conversions, revenue per landing page | Free |
| **URL Inspection API** | index status per URL | Free (2k/day) |

→ **Design decision:** The closed feedback loop (LEARN) is built entirely on free, official, read APIs. This is where AceleraSEO beats Ahrefs — Ahrefs never touches your GSC/GA4.

## Summary of what shaped the design

| Want | Reality | Our approach |
|------|---------|--------------|
| Own backlink index | $300M/yr — impossible | BYO third-party API key |
| Auto-index any page in Google | API forbidden for general pages | IndexNow (Bing/etc) + monitor Google |
| "Test before indexing" | Wrong order; index then measure | Publish → index → measure → iterate |
| Guaranteed fast #1 | Rankings compound | Pick winnable battles → fast *impact* |
