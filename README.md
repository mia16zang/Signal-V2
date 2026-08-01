# Signal — market intelligence prototype

FastAPI backend that takes a topic, collects public evidence, extracts
deterministic signals from it, and asks an LLM for a customer / market /
competitive read plus an investment-style synthesis.

## Running

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

`.env` keys: `GEMINI_API_KEY`, `OPENROUTER_API_KEY`, `YOUTUBE_API_KEY`,
and `PRODUCTHUNT_CLIENT_ID` / `PRODUCTHUNT_CLIENT_SECRET` if Product Hunt is
enabled.

## API

`POST /analyze` with `{"topic": "..."}` returns:

```
{ "meta": {...}, "signals": {...}, "intelligence": {...}, "synthesis": {...},
  "evidence": [...] }
```

`evidence` is the ranked source list the briefing was built from — `rank`, `source`,
`title`, `url`, `snippet`, `query` and `used_in_prompt` per item, plus `id`,
`source_key`, `display_name` and `exclusion_reason`. Only the first
`PROMPT_EVIDENCE_ITEMS` reached the model, and `used_in_prompt` says which. Set
`INCLUDE_EVIDENCE=false` to return it empty.

`GET /health` and `GET /` are liveness probes.

### `report` — the v2 view

`report`, `metric_definitions`, `score_scale`, `evidence_summary` and
`signals_unavailable` are additive. Nothing above them was removed or retyped, so a
client reading only the original keys is unaffected.

Everything in `report` is published in one of two envelopes, defined in
[`app/payload/envelopes.py`](backend/app/payload/envelopes.py):

- **`Estimate`** — one figure, plus `display` (pre-formatted), `confidence`,
  `confidence_band`, `basis`, `source_count`, `evidence_ids` and `collected`.
- **`Insight`** — one ranked row: `label` (≤10 words), `detail`, `score`,
  `score_band`, `evidence_ids` and `rank`.

Three things the payload now refuses to do:

1. **Report a figure it can't support.** An `Estimate` whose confidence is under 55
   returns `value: null` and says why in `basis`. The model rating its own market
   size at 50 means it inferred the number; printing it anyway makes it quotable.
2. **Emit `0` for "we didn't look".** Each raw signal names the collector it derives
   from. If that collector contributed nothing, `collected` is `false`, `value` is
   `null` and `display` is `—`. With Product Hunt off, `competitive.launches` was
   reporting `0` — indistinguishable from a market with no launches.
3. **Imply precision it doesn't have.** Scores are `90 | 75 | 50` and nothing else,
   because that is all the model ever emitted; `score_scale` documents what each
   band asserts. Percentages round to whole numbers and display as `~77%`; currency
   is capped at two significant figures. Exact counts are left alone — 481 comments
   is a measurement, and rounding it would add error.

Every `Insight` cites `evidence_ids`. The model is asked for them, a validator
rejects an item without any, and one corrective retry is attempted. Ids that don't
match a collected source are dropped rather than repaired — a citation the server
invented would be worse than none.

## Modes

Everything tunable lives in [`backend/app/config.py`](backend/app/config.py)
and can be overridden by environment variable.

| | `PORTFOLIO_MODE=true` (default) | `PORTFOLIO_MODE=false` |
|---|---|---|
| LLM calls per request | 1 merged | 4 sequential |
| Collectors | DDGS + YouTube + Google Trends | + Product Hunt |
| Evidence kept | 30 ranked | 200 |
| Typical cold request | ~23–30s measured | ~100s |
| Cached request | 1ms measured | 1ms measured |

The cold-request figure is two samples taken the same day, and both DDGS and
Gemini ran slower that day than when the 17.7–22.3s range was first measured
(one of the two runs included a Gemini retry). Treat it as the pessimistic end
of the range rather than a regression.

Product Hunt stays off in both modes by default. Its query is `posts(first: 50)` —
the global launch feed with no topic filter — so it returned the same posts, and
therefore an identical `competition_score` of 100, for two unrelated topics. See
the note in `app/config.py`.

Collection is capped at `COLLECTOR_TIMEOUT_SECONDS` (8) **per DDGS query**, not
per batch. DDGS has a tail that never fully drains, so collection takes about
the full budget on most requests; the cap decides how much of the tail is worth
waiting for, not whether the request succeeds.

The response shape is identical in both modes.

## Rate limits and seeded suggestions

Measured on the Gemini free tier, 2026-08-02:

```
quotaId    GenerateRequestsPerMinutePerProjectPerModel-FreeTier
quotaValue 5
retryDelay 33s
```

Five requests **per minute** per model — not a daily allowance, and it clears
itself. One analysis is one call, so the ceiling is roughly five concurrent
visitors, and daily volume is unconstrained. Two people clicking the same
suggestion at the same moment was enough to exceed it.

`backend/fixtures/seed/` holds a committed briefing for each of the four
landing-page suggestions, served with no TTL, so those topics never call the
provider. `cache/` is gitignored and expires after `CACHE_TTL_HOURS`, so it
cannot do this job — a fresh deploy starts empty. A live cache entry always
takes precedence over a seed. Seeded responses carry `meta.seeded: true` and
their original `generated_at`, so nothing claims to be fresher than it is.

Regenerate them when the payload shape changes:

```bash
cd backend
python scripts/warm_cache.py
```

When the provider does fail, `POST /analyze` returns **503** with
`retry_after_seconds` rather than a 200 containing an empty briefing. That
mattered: `normalise_synthesis` fills an absent decision with `"Monitor"` and a
confidence of `0`, so a rate limit used to reach the reader as a considered
"Monitor" verdict with all 30 sources rendered underneath it. Measured on 2 of
15 live runs. Failed briefings are also never written to the cache — that turned
a 33-second rate limit into a 24-hour one.

## Variance

`backend/fixtures/variance/` holds five runs of each of three queries plus a
report. The headline: the same query does not return the same briefing. On one
topic `market_pulse` ranged 8–100 and the recommendation moved between
`Strong Yes` and `Yes`; across all three, under 10% of ranked insights recur
even under fuzzy matching. Regenerate with:

```bash
python scripts/variance_check.py                # live, 15 requests
python scripts/variance_check.py --from-fixtures  # re-analyse saved runs
```

## Verifying

```bash
cd backend
python verify_contract.py            # live collection, stubbed LLM
python verify_contract.py --offline  # no network at all
python test_normalise.py             # normalisation rules, no network
python check_payload.py fixtures/after.json   # the payload acceptance checks
```

`fixtures/before.json` and `fixtures/after.json` are full responses for the same
topic either side of the payload change, kept so the diff is reviewable.

Runs without API keys — the LLM is stubbed. Exercises the JSON recovery path
against fenced, truncated, prose-wrapped and wrong-typed model output, and
confirms a provider outage still returns a renderable response.

The expected response shape is `FROZEN_CONTRACT` in `verify_contract.py`,
derived from the recorded production responses that completed successfully.
`backend/cache/` is a runtime artifact and is not in version control, so a
fresh clone uses the frozen copy; if a cache is present the verifier derives
the contract from it instead and the frozen copy is ignored.

## History

The first commit is the original backend, unmodified, so the optimisation
work is reviewable as a diff:

```bash
git diff $(git rev-list --max-parents=0 HEAD) HEAD --stat
```
