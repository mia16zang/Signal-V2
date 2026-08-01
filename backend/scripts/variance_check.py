"""Run the same query N times and report what does not hold still.

The product's pitch is that it reads evidence rather than guessing. That claim
is only as good as the answer's stability: if the same question returns a
different verdict on Tuesday, the briefing is a sample from a distribution and
the interface has been presenting it as a fact.

Usage:
    python scripts/variance_check.py                 # 3 default queries, N=5
    python scripts/variance_check.py -n 3 "topic"    # one topic, N=3

Writes fixtures/variance/<slug>/run-<n>.json and report.md, plus a combined
fixtures/variance/report.md.
"""

import argparse
import asyncio
import json
import os
import re
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Every run must actually run. A cache hit would report perfect stability by
# returning the same stored object, which is the opposite of what is measured.
os.environ["CACHE_ENABLED"] = "false"

from app.services.analysis_service import AnalysisService  # noqa: E402

# The default topic plus two landing-page chips, so the numbers are not tuned
# to one query's idiosyncrasies.
DEFAULT_QUERIES = [
    "Developer tools for edge functions",
    "AI note-taking for clinicians",
    "Carbon accounting for SMBs",
]

# Fields where any variation changes the answer rather than the wording.
DECISION_FIELDS = (
    "synthesis.build_recommendation.decision",
    "report.verdict.decision",
    "intelligence.market.market_maturity.stage",
    "report.market.market_maturity.value",
)

# Numbers on a bounded 0-100 scale, where a ratio is misleading (50 -> 75 is a
# 1.5x ratio but only 25 points) and the absolute spread is what matters.
BOUNDED = re.compile(
    r"(market_pulse|confidence|opportunity_score|competition_score|momentum"
    r"|\.score$|_score$|strength|severity|importance|potential|impact)"
)

# Measured timings and timestamps vary by definition; they are not findings.
IGNORED = re.compile(r"(_time$|generated_at|^meta\.cached$|total_time)")

SPREAD_STABLE = 0      # identical
SPREAD_DRIFTING = 10   # <= 10 points on a bounded scale is the same answer
RATIO_DRIFTING = 1.5   # unbounded numbers: within 1.5x is the same answer


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def leaves(node, path=""):
    """Every scalar in the payload, keyed by dotted path.

    List *items* are deliberately not walked positionally -- a list whose order
    changed would report every index as unstable when the content is the same.
    Lists are compared separately, by set overlap.
    """
    if isinstance(node, dict):
        for k, v in node.items():
            yield from leaves(v, f"{path}.{k}" if path else k)
    elif isinstance(node, list):
        return
    else:
        yield path, node


def insight_lists(payload):
    """{list_key: [label, ...]} for every ranked list in the report."""
    out = {}
    for key, container in (payload.get("report", {}).get("lists") or {}).items():
        out[key] = [i["label"] for i in container.get("items", [])]
    return out


def classify(path, values):
    """stable | drifting | unstable, plus the numbers behind the call."""
    distinct = []
    for v in values:
        if v not in distinct:
            distinct.append(v)

    if len(distinct) == 1:
        return "stable", {}

    if path in DECISION_FIELDS:
        return "unstable", {"distinct": distinct}

    numeric = [v for v in values if isinstance(v, (int, float))
               and not isinstance(v, bool)]

    if len(numeric) == len(values) and numeric:
        lo, hi = min(numeric), max(numeric)
        spread = hi - lo
        ratio = (hi / lo) if lo else float("inf")
        stats = {"min": lo, "max": hi, "spread": round(spread, 2),
                 "ratio": round(ratio, 2) if ratio != float("inf") else None}

        if BOUNDED.search(path):
            return ("drifting" if spread <= SPREAD_DRIFTING else "unstable"), stats
        return ("drifting" if ratio <= RATIO_DRIFTING else "unstable"), stats

    # Free prose. A reworded sentence is drifting; a different claim is
    # unstable, and no automated rule can tell those apart, so the distinct
    # values are printed for a human to judge and the default is the
    # conservative one.
    return "drifting", {"distinct": [str(d)[:110] for d in distinct]}


def compare(runs):
    paths = {}
    for run in runs:
        for path, value in leaves(run):
            if IGNORED.search(path):
                continue
            paths.setdefault(path, []).append(value)

    verdicts = {}
    for path, values in paths.items():
        if len(values) != len(runs):          # field absent from some runs
            verdicts[path] = ("unstable", {"note": f"present in {len(values)}/{len(runs)} runs"})
            continue
        verdicts[path] = classify(path, values)
    return verdicts


_STOP = {"the", "a", "an", "of", "for", "and", "in", "to", "with", "on", "high",
         "low", "strong", "clear", "growing", "increasing"}

SAME_ITEM = 0.5   # token overlap at which two labels are the same finding


def _tokens(label):
    return {w for w in re.findall(r"[a-z]+", label.lower())
            if len(w) > 2 and w not in _STOP}


def _same(a, b):
    """Do two labels name the same finding?

    Exact string equality is the wrong test. The model rewrites its phrasing
    every run -- "High Market Growth and Investment" one run, "Explosive Market
    Growth" the next -- so an exact-match metric reports 0% recurrence on lists
    whose content is substantially stable. That would overstate the instability
    badly, which is the opposite of the point of this script.
    """
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return a.strip().lower() == b.strip().lower()
    return len(ta & tb) / len(ta | tb) >= SAME_ITEM


def _cluster(all_labels):
    """Group labels that name the same finding. Greedy, order-independent."""
    clusters = []
    for label in all_labels:
        for cluster in clusters:
            if _same(label, cluster[0]):
                cluster.append(label)
                break
        else:
            clusters.append([label])
    return clusters


def list_overlap(runs):
    """How much of each ranked list recurs, by exact match and by meaning."""
    out = {}
    per_run = [insight_lists(r) for r in runs]
    n = len(runs)

    for key in per_run[0]:
        by_run = [p.get(key, []) for p in per_run]
        sets = [set(labels) for labels in by_run]
        union = set().union(*sets)
        exact_common = set.intersection(*sets) if sets else set()

        # Cluster every label seen anywhere, then count in how many distinct
        # runs each cluster appears.
        clusters = _cluster([lab for labels in by_run for lab in labels])
        runs_per_cluster = []
        for cluster in clusters:
            present = sum(
                1 for labels in by_run
                if any(any(_same(lab, member) for member in cluster) for lab in labels)
            )
            runs_per_cluster.append(present)

        in_all = sum(1 for c in runs_per_cluster if c == n)
        in_majority = sum(1 for c in runs_per_cluster if c >= (n + 1) // 2)

        out[key] = {
            "exact_in_every_run": len(exact_common),
            "union": len(union),
            "distinct_findings": len(clusters),
            "findings_in_every_run": in_all,
            "findings_in_majority": in_majority,
            "fraction": round(in_all / len(clusters), 2) if clusters else 0.0,
            "majority_fraction": round(in_majority / len(clusters), 2) if clusters else 0.0,
            "sizes": [len(s) for s in sets],
        }
    return out


def get(payload, path, default=None):
    node = payload
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            return default
        node = node[part]
    return node


def report_for(query, runs, timings):
    verdicts = compare(runs)
    overlap = list_overlap(runs)

    unstable = sorted(p for p, (v, _) in verdicts.items() if v == "unstable")
    drifting = sorted(p for p, (v, _) in verdicts.items() if v == "drifting")
    stable = [p for p, (v, _) in verdicts.items() if v == "stable"]

    lines = [f"## {query}", ""]
    lines.append(f"{len(runs)} runs. {len(stable)} stable, {len(drifting)} drifting, "
                 f"{len(unstable)} unstable, of {len(verdicts)} leaf fields.")
    lines.append("")

    # ---- the four questions the session hinges on ----
    decisions = [get(r, "synthesis.build_recommendation.decision") for r in runs]
    summaries = [(get(r, "synthesis.executive_summary") or "")[:80] for r in runs]
    pulses = [get(r, "synthesis.market_pulse") for r in runs]
    pulses = [p for p in pulses if isinstance(p, (int, float))]

    # A run whose synthesis came back empty is not a different opinion, it is a
    # failure. `normalise_synthesis` fills the decision with "Monitor" when
    # there is nothing to fill it from, so a total parse failure is served as a
    # considered verdict. Separating the two is the difference between "the
    # model is inconsistent" and "the product silently serves blank briefings".
    empty = [i + 1 for i, r in enumerate(runs)
             if not (get(r, "synthesis.executive_summary") or "").strip()]
    real = [d for i, d in enumerate(decisions) if (i + 1) not in empty]

    flipped = len(set(real)) > 1
    pulse_spread = (max(pulses) - min(pulses)) if pulses else 0

    ratios = []
    for path, (verdict, stats) in verdicts.items():
        if stats.get("ratio") and stats["ratio"] > 2:
            ratios.append((path, stats["min"], stats["max"], stats["ratio"]))
    ratios.sort(key=lambda r: -r[3])

    lines += [
        "### The four questions",
        "",
        f"**1. Does the verdict flip?** {'YES' if flipped else 'No'} — "
        f"decisions: {decisions}",
        "",
        (f"> {len(empty)} of {len(runs)} runs (#{', #'.join(map(str, empty))}) "
         f"returned an **empty synthesis** and were served as `Monitor` with "
         f"confidence 0 — that is the fallback default, not a judgement. Those "
         f"runs are excluded from the flip test above."
         if empty else "All runs produced a real synthesis."),
        "",
        f"**2. Does market_pulse vary by more than 15 points?** "
        f"{'YES' if pulse_spread > 15 else 'No'} — values {pulses}, "
        f"spread {pulse_spread}",
        "",
        "**3. Insight-list recurrence across all runs:**",
        "",
        "Counted two ways. *Exact* is identical label text. *Findings* clusters "
        "labels that name the same thing in different words, which is the fairer "
        "measure -- the model rephrases every run.",
        "",
        "| list | distinct findings | in all runs | in most runs | exact matches |",
        "|---|---|---|---|---|",
    ]
    for key, o in sorted(overlap.items(), key=lambda kv: kv[1]["fraction"]):
        lines.append(
            f"| {key} | {o['distinct_findings']} | {o['findings_in_every_run']} "
            f"({o['fraction']:.0%}) | {o['findings_in_majority']} "
            f"({o['majority_fraction']:.0%}) | {o['exact_in_every_run']} |"
        )

    mean_fraction = statistics.mean([o["fraction"] for o in overlap.values()]) if overlap else 0
    mean_majority = statistics.mean([o["majority_fraction"] for o in overlap.values()]) if overlap else 0
    lines += ["",
              f"Mean recurrence in **all** {len(runs)} runs: **{mean_fraction:.0%}**",
              f"Mean recurrence in **most** runs: **{mean_majority:.0%}**", ""]

    lines += ["**4. Fields with a max/min ratio above 2:**", ""]
    if ratios:
        lines += ["| field | min | max | ratio |", "|---|---|---|---|"]
        lines += [f"| `{p}` | {lo} | {hi} | {r}x |" for p, lo, hi, r in ratios[:25]]
    else:
        lines.append("None.")
    lines.append("")

    lines += ["### Executive summary, first 80 chars per run", ""]
    lines += [f"{i}. {s}" for i, s in enumerate(summaries, 1)]
    lines.append("")

    if unstable:
        lines += ["### Unstable fields", ""]
        for path in unstable[:40]:
            _, stats = verdicts[path]
            lines.append(f"- `{path}` — {json.dumps(stats)[:200]}")
        if len(unstable) > 40:
            lines.append(f"- ...and {len(unstable) - 40} more")
        lines.append("")

    lines += ["### Timing", "",
              f"per-run total: {[round(t, 1) for t in timings]}",
              f"median: **{statistics.median(timings):.1f}s**", ""]

    return "\n".join(lines), {
        "query": query, "flipped": flipped, "pulse_spread": pulse_spread,
        "mean_recurrence": mean_fraction, "ratios_over_2": len(ratios),
        "unstable": len(unstable), "median_time": statistics.median(timings),
        "decisions": decisions, "empty_runs": len(empty),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("queries", nargs="*", default=None)
    ap.add_argument("-n", "--runs", type=int, default=5)
    ap.add_argument("--from-fixtures", action="store_true",
                    help="re-analyse saved runs instead of calling the pipeline")
    args = ap.parse_args()

    queries = args.queries or DEFAULT_QUERIES
    service = AnalysisService()
    summaries, sections = [], []

    for query in queries:
        folder = os.path.join("fixtures", "variance", slug(query))
        os.makedirs(folder, exist_ok=True)
        runs, timings = [], []

        for n in range(1, args.runs + 1):
            path = os.path.join(folder, f"run-{n}.json")

            if args.from_fixtures:
                with open(path, encoding="utf-8") as f:
                    payload = json.load(f)
                runs.append(payload)
                timings.append(payload.get("meta", {}).get("total_time", 0))
                continue

            print(f"\n=== {query} — run {n}/{args.runs} ===", flush=True)
            started = time.time()
            payload = asyncio.run(service.analyze(query))
            timings.append(time.time() - started)
            runs.append(payload)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)

        section, summary = report_for(query, runs, timings)
        with open(os.path.join(folder, "report.md"), "w", encoding="utf-8") as f:
            f.write(section)
        sections.append(section)
        summaries.append(summary)

    header = ["# Variance report", "",
              f"{args.runs} runs per query, cache disabled, run sequentially.", "",
              "| query | verdict flips | empty runs | pulse spread | findings recurring in all runs | ratios >2x | unstable fields | median |",
              "|---|---|---|---|---|---|---|---|"]
    for s in summaries:
        header.append(
            f"| {s['query']} | {'**YES**' if s['flipped'] else 'no'} | "
            f"{s['empty_runs']} | {s['pulse_spread']} | {s['mean_recurrence']:.0%} | "
            f"{s['ratios_over_2']} | {s['unstable']} | {s['median_time']:.1f}s |"
        )

    all_times = [s["median_time"] for s in summaries]
    header += ["", f"Median of per-query medians: **{statistics.median(all_times):.1f}s**", ""]

    if any(s["flipped"] for s in summaries):
        header += ["> **The verdict flips between identical runs.** "
                   "This is a product-level finding, not a rendering bug.", ""]

    blank = sum(s["empty_runs"] for s in summaries)
    if blank:
        total = len(summaries) * len(summaries[0]["decisions"])
        header += [f"> **{blank} of {total} runs returned an empty briefing** and were "
                   f"served as a `Monitor` verdict with confidence 0. `Monitor` is the "
                   f"fallback default in `normalise_synthesis`, so a total parse failure "
                   f"is presented to the reader as a considered recommendation, with the "
                   f"full evidence list still rendered beneath it.", ""]

    out = "\n".join(header) + "\n" + "\n".join(sections)
    with open(os.path.join("fixtures", "variance", "report.md"), "w", encoding="utf-8") as f:
        f.write(out)

    print("\n" + "=" * 60)
    print("\n".join(header))
    print("wrote fixtures/variance/report.md")


if __name__ == "__main__":
    main()
