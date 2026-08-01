"""Acceptance checks for the payload spec.

Runs against a captured response rather than the network, so it is cheap to
re-run and so a failure is always about the payload rather than about whether
DuckDuckGo answered today.

    python check_payload.py fixtures/after.json
"""

import json
import re
import sys

from app.payload.normalise import MIN_REPORTABLE_CONFIDENCE, _normalise_text
from difflib import SequenceMatcher

PASS, FAIL = "[PASS]", "[FAIL]"
failures = []


def check(name, ok, detail=""):
    print(f"  {PASS if ok else FAIL} {name}" + (f" -- {detail}" if detail and not ok else ""))
    if not ok:
        failures.append(name)


def walk(node, path=""):
    if isinstance(node, dict):
        for k, v in node.items():
            yield from walk(v, f"{path}.{k}" if path else k)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from walk(v, f"{path}[{i}]")
    else:
        yield path, node


def main(path):
    d = json.load(open(path, encoding="utf-8"))
    report = d["report"]
    lists = report["lists"]
    items = [i for l in lists.values() for i in l["items"]]

    print(f"\nAcceptance checks — {path}\n")

    # 1 -------------------------------------------------------------- precision
    #
    # The two-significant-figure rule applies to *derived* figures -- a market
    # size inferred from scraped headlines, an averaged rate. It deliberately
    # does not apply to exact counts: 481 comments is a measurement, and
    # rounding it to 480 would add error to a number that had none. Same
    # reasoning the spec uses to exempt timings.
    exempt = re.compile(r"(_time$|^meta\.|latency|elapsed)")
    loose = []
    for key, value in walk(report):
        if isinstance(value, float) and not isinstance(value, bool) and not exempt.search(key):
            digits = len(str(value).replace("-", "").replace(".", "").lstrip("0").rstrip("0"))
            if digits > 2:
                loose.append(f"{key}={value}")
    check("no derived float carries more than two significant figures", not loose,
          "; ".join(loose[:5]))

    ints = [f"{k}={v}" for k, v in walk(report)
            if isinstance(v, float) and v == int(v) and not exempt.search(k)]
    check("exact counts are serialised as ints, not floats", not ints,
          "; ".join(ints[:5]))

    # 2 ------------------------------------------------- low-confidence estimate
    size = report["market"]["market_size"]
    if size["confidence"] is not None and size["confidence"] < MIN_REPORTABLE_CONFIDENCE:
        check("weakly supported market size is suppressed",
              size["value"] is None and "estimable" in size["display"].lower(),
              json.dumps(size)[:120])
    else:
        print(f"  [n/a ] market size suppression — confidence is "
              f"{size['confidence']}, at or above the {MIN_REPORTABLE_CONFIDENCE} "
              f"threshold, so the rule correctly does not fire")

    # 3 ------------------------------------------------------- null is not zero
    bad_zero = [
        f"{group}.{key}"
        for group, entries in report["signals"].items()
        for key, value in entries.items()
        if isinstance(value, dict) and "collected" in value
        and not value["collected"] and (value["value"] is not None or value["display"] != "—")
    ]
    check("every uncollected signal is null with an em-dash", not bad_zero,
          "; ".join(bad_zero))
    check("signals_unavailable is populated and matches",
          sorted(d["signals_unavailable"]) == sorted(
              f"{g}.{k}" for g, e in report["signals"].items()
              for k, v in e.items()
              if isinstance(v, dict) and "collected" in v and not v["collected"]))

    # 4 --------------------------------------------------------- headline dedupe
    values = [(k, v["value"]) for k, v in report["headline"].items() if v["value"]]
    dupes = [
        f"{a} ~ {b}"
        for i, (a, av) in enumerate(values)
        for b, bv in values[i + 1:]
        if SequenceMatcher(None, _normalise_text(av), _normalise_text(bv)).ratio() > 0.9
    ]
    check("no two surviving headline fields are near-identical", not dupes,
          "; ".join(dupes))

    # 5 ------------------------------------------------------------ label length
    long_labels = [i["label"] for i in items if len(i["label"].split()) > 10]
    check("every insight label is 10 words or fewer", not long_labels,
          f"{len(long_labels)} over, e.g. {long_labels[:1]}")

    # 6 ---------------------------------------------------------- evidence links
    uncited = [i["id"] for i in items if not i["evidence_ids"]]
    check("every insight cites at least one evidence id", not uncited,
          f"{len(uncited)}/{len(items)} uncited: {uncited[:6]}")

    valid = {e["id"] for e in d["evidence"]}
    dangling = [x for i in items for x in i["evidence_ids"] if x not in valid]
    check("no insight cites an id that does not exist", not dangling,
          str(dangling[:5]))

    # 7 ---------------------------------------------------------------- scoring
    bands = {90: "high", 75: "moderate", 50: "low"}
    off = [i["score"] for i in items if i["score"] not in bands]
    check("every score is 90, 75 or 50", not off, str(sorted(set(off))))
    check("every score_band matches its score",
          all(i["score_band"] == bands.get(i["score"]) for i in items))

    # 8 ------------------------------------------------------------------ sorting
    unsorted = [
        l["key"] for l in lists.values()
        if [(-i["score"], -len(i["evidence_ids"])) for i in l["items"]]
        != sorted((-i["score"], -len(i["evidence_ids"])) for i in l["items"])
    ]
    check("every list is sorted by score then evidence count", not unsorted,
          str(unsorted))
    check("every list carries a sort_basis",
          all(l.get("sort_basis") for l in lists.values()))
    check("ranks are 1..n in order",
          all([i["rank"] for i in l["items"]] == list(range(1, len(l["items"]) + 1))
              for l in lists.values()))

    # 9 ------------------------------------------------------- metric definitions
    defs = d["metric_definitions"]
    check("metric_definitions is present", bool(defs), str(len(defs)))
    self_referential = [m["key"] for m in defs
                        if m["label"].lower() in m["definition"].lower()]
    check("no definition restates its own label", not self_referential,
          str(self_referential))

    # 10 ---------------------------------------------------------- evidence counts
    summary = d["evidence_summary"]
    used = len([e for e in d["evidence"] if e["used_in_prompt"]])
    check("evidence_summary.used matches the evidence list",
          summary["used"] == used, f"{summary['used']} vs {used}")
    check("collected == used + excluded",
          summary["collected"] == summary["used"] + summary["excluded"])

    # 11 ------------------------------------------------------------ source names
    check("every evidence item has a display_name",
          all(e.get("display_name") for e in d["evidence"]))
    leaked = [
        key for key, value in walk(d)
        if isinstance(value, str)
        and re.search(r"\b(ddgs|google_trends)\b", value)
        and not key.endswith("source_key")
        and not key.endswith(".source")
    ]
    check("no library name leaks outside source_key", not leaked,
          "; ".join(leaked[:5]))

    # 12 -------------------------------------------------------- opportunity score
    check("opportunity_score is not a top-level field",
          "opportunity_score" not in d)
    check("sizing_language_density replaces it in the report",
          "sizing_language_density" in report["signals"]["market_opportunity"])

    print()
    if failures:
        print(f"{len(failures)} FAILED: {', '.join(failures)}")
    else:
        print("all checks passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "fixtures/after.json"))
