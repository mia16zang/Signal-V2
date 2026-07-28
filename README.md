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
{ "meta": {...}, "signals": {...}, "intelligence": {...}, "synthesis": {...} }
```

`GET /health` and `GET /` are liveness probes.

## Modes

Everything tunable lives in [`backend/app/config.py`](backend/app/config.py)
and can be overridden by environment variable.

| | `PORTFOLIO_MODE=true` (default) | `PORTFOLIO_MODE=false` |
|---|---|---|
| LLM calls per request | 1 merged | 4 sequential |
| Collectors | DDGS + YouTube | + Google Trends + Product Hunt |
| Evidence kept | 30 ranked | 200 |
| Typical cold request | ~15–20s | ~100s |
| Cached request | <100ms | <100ms |

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
git diff HEAD~2 HEAD --stat
```
