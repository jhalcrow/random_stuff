# KvK #19 scouting: K203 (us) vs K365

## Rules
- **Aggregate numbers only.** Never write player names, governor IDs, or rosters
  to any file, report, commit, or chat output. Alliance tags/names are OK.
- **Never print or log `MIGHTPULSE_API_KEY`.** Read it from the environment only.
- **Label anything unconfirmed** (estimates, projections, stale data, inconsistencies).
- Raw API responses that contain member data stay in memory only; they are never
  written to disk.

## Event
- KvK #19, castle day ~**Sat 10 Oct 2026** (estimated from the 4-week cadence:
  recent castle days were 23 May, 20 Jun, 18 Jul, 15 Aug, 12 Sep; not officially confirmed).
- Next transfer window: 8 Nov 2026. Gen 8 reaches K365's bracket: 9 Nov 2026.

## Verified data (StratForge + Kingshot.net, early Oct 2026)
"Real power" = heroes + gear + gems + pets, no troops.

| | K203 (us) | K365 |
|---|---|---|
| Bracket | K116-235 | K236-417 |
| Age | ~514 days | ~488 days |
| Stage | Advanced Truegold / Gen 7 | Advanced Truegold / Gen 7 |
| Real power | 2.8B | 2.7B |
| Top-10 total | 8.3B | 8.4B |
| Cities / alliances | 1,204 / 385 (snapshot 17 days old) | 1,375 / 486 |
| Top 5 players (M) | 381, 372, 358, 341, 340 | 351, 325, 308, 308, 281 |
| KvK prep | 16-0 | 14-1 |
| KvK castle | 11-5 | 10-5 |

Top alliances (real power, members):
- K203: ORM 12.7B/93, PRO 12.6B/92, BR4 12.4B/98, SRT 10.1B/89, BR1 8.3B/98
- K365: LTR 14.4B/100, AOS 14.2B/100, ORG 12.8B/96, SCC 11.3B/95, SDH 8.6B/84

KvK history (oldest -> newest, opponent prep/castle):
- K203: 195 W/W, 176 W/W, 177 W/L, 224 W/W, 190 W/L, 263 W/W, 195 W/W, 249 W/L,
  184 W/W, 187 W/W, 222 W/L, 270 W/W, 156 W/W, 194 W/L, 151 W/W, 100 W/W
- K365: 347 L/L, 340 W/W, 363 W/W, 336 W/L, 402 W/W, 385 W/W, 347 W/W, 331 W/L,
  337 W/W, 384 W/W, 358 W/L, 144 W/W, 233 W/W, 393 W/L, 414 W/W

Other: prep and battle results correlate only ~31% across kingdoms.

Current read (before MightPulse data): prep ~50-55% K203, castle close to even.
K203 is stronger at the very top; K365 is deeper in its lead alliances.

### Data caveats (unconfirmed, flag in the report)
- Kingdom "real power" (2.8B / 2.7B) is smaller than a single top alliance's
  real power (e.g. ORM 12.7B), and "top-10 total" (8.3B / 8.4B) doesn't equal the
  sum of the top players (top 5 alone ~1.8B) or of the top alliances. The metric
  definitions of these two fields are unclear; compare them like-for-like only.
- K203 city/alliance counts are a 17-day-old snapshot.

## MightPulse API
- Base `https://api.mightpulse.com/v1`, header `Authorization: Bearer <key>`.
- 60 req/min, 5,000/day, 429 if exceeded. Data up to 1h old.
- `GET /kingdoms/{kid}`, `GET /kingdoms/{kid}/ranks?board=alliance_power&limit=N`,
  `GET /alliances/{kid}/{tag}?include=info,roster` (tags are case-sensitive).

## Layout
- `data/known_data.json`: the verified data above, machine-readable.
- `scripts/mightpulse_pull.py`: pulls kingdom + top-6 alliance activity.
  `--probe` prints response shapes only (keys/types, no values); the default run
  writes aggregates to `data/mightpulse_summary.json`.
