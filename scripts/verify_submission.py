"""Run from repo root with its venv Python; all reports are generated, never edited."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
os.chdir(SRC)
os.environ["PYTHONUTF8"] = "1"
sys.stdout.reconfigure(encoding="utf-8")
REPORTS = Path("reports")
REPORTS.mkdir(exist_ok=True)


def main():
    results = []
    with (REPORTS / "verification.log").open("w", encoding="utf-8") as log:
        def run(module, *args, expected=0):
            command = [sys.executable, "-m", module, *args]
            print("RUN", " ".join(command[2:]), flush=True)
            if module == "lab9.eval" and "--reuse-existing" in sys.argv and "--out" in args:
                path = Path(args[args.index("--out") + 1])
                if path.is_file():
                    from lab9.eval import load_spec
                    from lab9.evalset import sha12
                    from lab9.gate import integrity_check
                    sp = load_spec(Path(args[args.index("--spec") + 1]) if "--spec" in args else Path("config/metric_spec.yaml"))
                    rep = json.loads(path.read_text(encoding="utf-8"))
                    if (rep["shape"] == args[args.index("--shape") + 1]
                            and rep["manifest"]["eval_set_sha"] == sha12(Path(sp["eval_set"]))
                            and rep["manifest"]["seeds"] == sp["seeds"]
                            and not integrity_check(rep, rep, sp)):
                        message = f"Reused script-generated report {path}: {rep['run_id']} (coverage/integrity validated)\n"
                        print(message, end="", flush=True)
                        log.write(message)
                        log.flush()
                        results.append({"command": command[2:], "exit": 0, "expected": expected, "reused": True})
                        return
            result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", timeout=240)
            output = result.stdout + result.stderr
            print(output, end="", flush=True)
            log.write(f"$ python -m {' '.join(command[2:])}\n{output}\nexit={result.returncode}; expected={expected}\n\n")
            log.flush()
            results.append({"command": command[2:], "exit": result.returncode, "expected": expected})
            if result.returncode != expected:
                raise RuntimeError(f"unexpected exit for {module}: {result.returncode}, expected {expected}")

        run("lab9.smoke")
        run("lab9.evalset", "--build", "--check")
        run("lab9.evalset", "--v2", "--build")
        run("pytest", "-q", "-o", "addopts=", "tests/test_lab9_stats.py", "tests/test_lab9_graders.py",
            "tests/test_lab9_advanced.py", "tests/test_lab9_evalset.py", "tests/test_lab9_regressions.py",
            "tests/test_swarm_reference.py")
        run("lab9.judge", "--csv", "data/eval/judge_tone_public.csv", "--audit", "10")
        run("lab9.judge", "--csv", "data/eval/judge_helpful_public.csv", "--audit", "5", expected=1)
        for name in ("swarm", "fixed", "seeded_regression"):
            path = f"reports/{'baseline_v1' if name == 'swarm' else 'eval_' + name}.json"
            run("lab9.eval", "--shape", name, "--out", path)
            run("lab9.gate", "--pr", path, "--baseline", "reports/baseline_v1.json",
                "--base-spec", "config/metric_spec.yaml", expected=int(name == "seeded_regression"))
        run("lab9.ci_check", "--pr", "reports/baseline_v1.json", "--baseline", "reports/baseline_v1.json")
        run("lab9.mutation", "--detect")
        spec = "config/metric_spec_v2.yaml"
        for name in ("swarm", "fixed", "honest_refactor", "seeded_regression", "slice_regression", "flaky_regression"):
            path = f"reports/{'baseline_v2' if name == 'swarm' else 'eval_v2_' + name}.json"
            run("lab9.eval", "--shape", name, "--spec", spec, "--out", path)
            run("lab9.gate", "--pr", path, "--baseline", "reports/baseline_v2.json", "--spec", spec,
                "--base-spec", spec, expected=int(name.endswith("regression")))
        run("lab9.mutation", "--spec", spec, "--aa", "66,77,88,99,110")
        run("lab9.mutation", "--spec", spec, "--baseline", "reports/baseline_v2.json")
        run("lab9.traps", "--pr", "reports/eval_v2_slice_regression.json", "--baseline", "reports/baseline_v2.json", "--spec", spec)
        for name in ("evaluator_errors_as_nan", "dropped_failing_rows", "cherry_picked_seeds", "loosened_spec"):
            args = ["--pr", f"reports/traps/{name}.json", "--baseline", "reports/baseline_v2.json",
                    "--spec", f"reports/traps/{name}.spec.yaml" if name == "loosened_spec" else spec]
            if name == "loosened_spec":
                args += ["--base-spec", spec]
            run("lab9.gate", *args, expected=1)

    (REPORTS / "verification.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    collect_evidence()
    print("ALL CHECKS PASSED", flush=True)


def collect_evidence():
    from lab8.shapes import SHAPES
    from lab9.trace_case import investigate
    from lab9.variant_agent import make_shape
    from lab9.judge import calibrate
    evidence = {}
    cases = [
        ("FM-01", "leaky_trace", "C-001"), ("FM-02", "ignore_denied", "C-007"),
        ("FM-03", "ticket_trust", "C-002"), ("FM-04", "sum_parts", "C-014"),
        ("FM-05", "pre_deducted", "C-013"), ("FM-06", "stale_clause", "C-006"),
        ("FM-07", "sibling_refund", "C-010"), ("FM-08", "misreport", "C-008"),
    ]
    for fm, bug, claim in cases:
        name = f"evidence_{bug}"
        SHAPES[name] = make_shape(name, {"no_override", bug})
        evidence[fm] = {"bug": bug, "claim": claim, "seed": 11, **investigate(name, claim, 11)}
    evidence["FM-09"] = {"claim": "C-005", "seed": 11, "control": True, **investigate("fixed", "C-005", 11)}
    evidence["trace_case"] = {"bad": investigate("seeded_regression", "C-002", 11),
                              "fixed": investigate("fixed", "C-002", 11)}
    (REPORTS / "trace_evidence.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    judges = {name: calibrate(Path(f"data/eval/judge_{name}_public.csv")) for name in ("tone", "helpful")}
    (REPORTS / "judge_calibration.json").write_text(json.dumps(judges, ensure_ascii=False, indent=2), encoding="utf-8")
    hashes = {p.relative_to(SRC).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted((SRC / "lab8").rglob("*.py"))}
    (REPORTS / "source_integrity.json").write_text(json.dumps(hashes, indent=2), encoding="utf-8")
    print("Wrote trace, judge and source evidence", flush=True)


if __name__ == "__main__":
    if "--evidence-only" in sys.argv:
        collect_evidence()
    else:
        main()
