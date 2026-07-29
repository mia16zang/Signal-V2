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
`title`, `url`, `snippet`, `query` and `used_in_prompt` per item. Only the first
`PROMPT_EVIDENCE_ITEMS` reached the model, and `used_in_prompt` says which. Set
`INCLUDE_EVIDENCE=false` to return it empty.

`GET /health` and `GET /` are liveness probes.

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

## Verifying

```bash
cd backend
python verify_contract.py            # live collection, stubbed LLM
python verify_contract.py --offline  # no network at all
```

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
