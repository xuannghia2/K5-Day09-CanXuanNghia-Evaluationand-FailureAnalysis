"""CI gate: compare a PR eval report with the main-branch baseline using the metric spec.

    python -m lab9.gate --pr reports/eval_workflow.json --baseline reports/baseline_v1.json

exit 0 = merge, exit 1 = blocked. Safety metrics: max 0, no averaging away.
Capability metrics: meet the floor AND the paired CI of (PR - main) is not entirely below 0.
Thresholds may only get stricter on the same eval-set version (ratchet).
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path

from lab8.console import utf8_stdio
from lab9 import stats
from lab9.eval import SPEC, aggregate, load_spec, per_item
from lab9.graders import GRADERS


def integrity_check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> list[str]:
    """M7 (Expert): refuse to compare reports that cannot be trusted. Return a list of problems
    (empty = trustworthy). A gate that passes a broken report is worse than no gate.
    Must catch at least:
      - any metric value in pr["metrics"] that is NaN or inf
      - len(pr["rows"]) != manifest items x len(manifest seeds)   (dropped / duplicated rows)
      - the (item_id, seed) set of PR differs from the baseline's (cherry-picked seeds/items)
      - pr["evaluator_failures"] non-empty, or a row whose value for a graded spec metric is
        None (a crashed grader silently scores as "missing" and drops out of the mean)
      - base_spec given and a threshold in spec is LOOSER than in base_spec for the same
        eval-set version (ratchet: max may not rise, min may not fall, a blocking metric may
        not become non-blocking, a metric may not disappear; the same for spec["slices"],
        including dropping no_significant_drop)
      - an item's slice tags in PR rows differ from the baseline's (relabelling an item out of a
        slice hides its regression from the slice gate)"""
    problems = []
    for label, report in (("PR", pr), ("baseline", base)):
        rows = report.get("rows", [])
        manifest = report.get("manifest", {})
        seeds = manifest.get("seeds", [])
        pairs = [(r.get("item_id"), r.get("seed")) for r in rows]
        items = {p[0] for p in pairs}
        if (not rows or len(rows) != manifest.get("items", 0) * len(seeds)
                or len(items) != manifest.get("items") or len(set(seeds)) != len(seeds)):
            problems.append(f"{label}: incomplete manifest item × seed coverage")
        if len(set(pairs)) != len(pairs):
            problems.append(f"{label}: duplicate (item_id, seed) rows")
        if set(pairs) != {(i, s) for i in items for s in seeds}:
            problems.append(f"{label}: incomplete Cartesian item × seed grid")
        if report.get("evaluator_failures"):
            problems.append(f"{label}: evaluator_failures is non-empty")
        for mid, value in report.get("metrics", {}).items():
            if value is not None and (not isinstance(value, (int, float)) or not math.isfinite(value)):
                problems.append(f"{label}: invalid aggregate {mid}")
        for m in spec["metrics"]:
            mid = m["id"]
            value = report.get("metrics", {}).get(mid)
            if value is None and m.get("blocking"):
                problems.append(f"{label}: missing blocking metric {mid}")
            # Graded row values must never silently disappear from the mean.
            if mid in GRADERS or any(mid in r for r in rows):
                for r in rows:
                    value = r.get(mid)
                    if not isinstance(value, (bool, int, float)) or not math.isfinite(value) or value not in (0, 1):
                        problems.append(f"{label}: missing/invalid row metric {mid}")
                        break
        if all(isinstance(r.get("cost"), (int, float)) and math.isfinite(r["cost"]) and r["cost"] >= 0
               for r in rows) and rows:
            ids = [m["id"] for m in spec["metrics"] if m["id"] in GRADERS]
            if all(r.get(mid) in (True, False, 0, 1) for r in rows for mid in ids):
                computed = aggregate(rows, ids, k_values=spec.get("pass_k", []))
                for mid, value in report.get("metrics", {}).items():
                    if mid in computed and value is not None and computed[mid] is not None:
                        if not isinstance(value, (int, float)) or not math.isclose(value, computed[mid], abs_tol=0.0001):
                            problems.append(f"{label}: aggregate {mid} disagrees with rows")
        elif any("cost" in r for r in rows):
            problems.append(f"{label}: invalid cost")
    pr_pairs = Counter((r.get("item_id"), r.get("seed")) for r in pr.get("rows", []))
    base_pairs = Counter((r.get("item_id"), r.get("seed")) for r in base.get("rows", []))
    if pr_pairs != base_pairs:
        problems.append("PR item/seed coverage differs from baseline")
    for field in ("items", "seeds"):
        a, b = pr.get("manifest", {}).get(field), base.get("manifest", {}).get(field)
        differs = set(a) != set(b) if field == "seeds" and a is not None and b is not None else a != b
        if differs:
            problems.append(f"PR manifest {field} differs from baseline")
    tags = {(r["item_id"], r["seed"]): set(r.get("slices") or []) for r in base.get("rows", [])}
    for row in pr.get("rows", []):
        key = row.get("item_id"), row.get("seed")
        if key in tags and set(row.get("slices") or []) != tags[key]:
            problems.append(f"PR slice tags changed for {key}")
    if base_spec and spec.get("eval_set_version") == base_spec.get("eval_set_version"):
        def ratchet(old_entries, new_entries, key, threshold):
            new_by_id = {key(x): x for x in new_entries}
            for old in old_entries:
                identity = key(old)
                new = new_by_id.get(identity)
                if new is None:
                    problems.append(f"ratchet: removed {identity}")
                    continue
                if old.get("blocking") and not new.get("blocking"):
                    problems.append(f"ratchet: disabled {identity}")
                old_th, new_th = threshold(old), threshold(new)
                for bound in ("min", "max", "max_increase"):
                    if bound in old_th and (bound not in new_th or
                        (new_th[bound] < old_th[bound] if bound == "min" else new_th[bound] > old_th[bound])):
                        problems.append(f"ratchet: loosened {identity}/{bound}")
                if old_th.get("no_significant_drop") and not new_th.get("no_significant_drop"):
                    problems.append(f"ratchet: removed no_significant_drop for {identity}")
        ratchet(base_spec.get("metrics", []), spec.get("metrics", []), lambda m: m["id"],
                lambda m: m.get("threshold", {}))
        ratchet(base_spec.get("slices", []), spec.get("slices", []), lambda m: (m["name"], m["metric"]),
                lambda m: m)
    return list(dict.fromkeys(problems))


def slice_check(pr: dict, base: dict, spec: dict) -> tuple[list[str], list[str]]:
    """M5 (Advanced): an average can hide a regression on a small, important slice.
    For each entry of spec["slices"] ({"name", "metric", "min"?, "no_significant_drop"?, "blocking"}):
      - value = mean of per_item(pr, metric, slice_name=name)
      - fail if below "min", or if no_significant_drop and the paired CI over the slice's items
        lies entirely below 0
    Return (blocked ids like "slice:money_movement/pass_rate", report lines)."""
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for entry in spec.get("slices", []):
        name, mid = entry["name"], entry["metric"]
        identity = f"slice:{name}/{mid}"
        a, b = per_item(pr, mid, name), per_item(base, mid, name)
        value = sum(a.values()) / len(a) if a else None
        failed = not a or set(a) != set(b)
        note = ""
        if value is not None:
            failed |= "min" in entry and value < entry["min"]
            failed |= "max" in entry and value > entry["max"]
        if not failed and entry.get("no_significant_drop"):
            keys = sorted(a)
            delta, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027),
                confidence=bs.get("confidence", 0.95))
            note = f"Δ {delta:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
            failed |= hi < 0
        if failed and entry.get("blocking"):
            blocked.append(identity)
        lines.append(f"  {identity} {value} {note} {'BLOCK' if failed and entry.get('blocking') else 'warn' if failed else 'ok'}")
    return blocked, lines


def check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> tuple[list[str], list[str]]:
    if pr["manifest"]["eval_set_sha"] != base["manifest"]["eval_set_sha"]:
        return ["eval_set_sha"], ["  EVAL SET differs from the baseline's: re-run the baseline on the same eval set"]
    problems = integrity_check(pr, base, spec, base_spec)
    if problems:
        return ["integrity"], [f"  INTEGRITY {p}" for p in problems]
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for m in spec["metrics"]:
        mid, th, val = m["id"], m.get("threshold", {}), pr["metrics"].get(m["id"])
        verdict, note = "ok", ""
        if val is None:
            verdict = "missing"
        elif "max" in th and val > th["max"]:
            verdict = "fail"
        elif "min" in th and val < th["min"]:
            verdict = "fail"
        elif "max_increase" in th and base["metrics"].get(mid) is not None:
            if val > base["metrics"][mid] * (1 + th["max_increase"]):
                verdict = "fail"
        if th.get("no_significant_drop") and val is not None:
            a, b = per_item(pr, mid), per_item(base, mid)
            keys = sorted(set(a) & set(b))
            d, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                                               n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027),
                                               confidence=bs.get("confidence", 0.95))
            note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
            if hi < 0:
                verdict = "fail"
        if verdict != "ok" and m.get("blocking"):
            blocked.append(mid)
        label = {"ok": "ok", "missing": "MISSING"}.get(verdict, "BLOCK" if m.get("blocking") else "warn")
        lines.append(f"  {mid:<22} {val!s:<8} {json.dumps(th):<40} {note:<28} {label}")
    if spec.get("slices"):
        sb, sl = slice_check(pr, base, spec)
        blocked += sb
        lines += sl
    return blocked, lines


def main(argv: list[str] | None = None) -> int:
    utf8_stdio()
    ap = argparse.ArgumentParser(prog="lab9.gate")
    ap.add_argument("--pr", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--spec", default=str(SPEC))
    ap.add_argument("--base-spec", help="metric spec on main, for the ratchet check (M7)")
    args = ap.parse_args(argv)
    pr = json.loads(Path(args.pr).read_text(encoding="utf-8"))
    base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    base_spec = load_spec(Path(args.base_spec)) if args.base_spec else None
    blocked, lines = check(pr, base, load_spec(Path(args.spec)), base_spec)
    print(f"gate: PR {pr['run_id']} vs main {base['run_id']} · eval set {pr['manifest']['eval_set_sha']}")
    print("\n".join(lines))
    if blocked:
        print(f"exit 1 — blocked: {', '.join(blocked)}")
        return 1
    print("exit 0 — merge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
