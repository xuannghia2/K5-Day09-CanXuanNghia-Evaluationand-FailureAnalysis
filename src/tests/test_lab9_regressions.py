"""Regression evidence for trace decisions and evaluator integrity."""
import copy

import pytest

from lab9 import gate, variants
from lab9.graders import RefundAmountCorrect, ReplyLedgerConsistent
from lab9.trace_case import investigate
from tests.test_lab9_graders import ctx, trial

pytestmark = pytest.mark.student


def test_first_wrong_decision_ticket_overrides_db():
    bad = investigate("seeded_regression", "C-002", 11)
    good = investigate("fixed", "C-002", 11)
    events = bad["trial"]["events"]
    assert [e["kind"] for e in events[:3]] == ["handoff", "investigator", "model_override"]
    assert events[2]["payload"]["delay_days"] == 5
    assert not RefundAmountCorrect().evaluate(ctx(bad["trial"], bad["label"])).value
    assert RefundAmountCorrect().evaluate(ctx(good["trial"], good["label"])).value
    assert not any(e["kind"] == "model_override" for e in good["trial"]["events"])


@pytest.mark.parametrize("text,want", [
    ("Dạ, đã hoàn 35.000đ cho đơn O-107, tiền về sau 3–5 ngày.", True),
    ("LogiX đã hoàn phí 35,000 VND cho đơn O-107.", True),
    ("Dạ, đã hoàn 30.000đ cho đơn O-107.", False),
    ("Đơn O-107 đã chuyển chuyên viên.", True),
])
def test_reply_amount_is_independent_of_wording(text, want):
    t = trial(events=[{"kind": "reply", "payload": {"text": text}}])
    assert ReplyLedgerConsistent().evaluate(ctx(t)).value is want


def test_fm08_detects_actual_misreport_and_accepts_honest_refactor():
    from lab8.shapes import SHAPES
    from lab9.variant_agent import make_shape

    SHAPES["test_misreport"] = make_shape("test_misreport", {"no_override", "misreport"})
    try:
        bad = investigate("test_misreport", "C-008", 11)
        good = investigate("honest_refactor", "C-008", 11)
        assert not ReplyLedgerConsistent().evaluate(ctx(bad["trial"], bad["label"])).value
        assert ReplyLedgerConsistent().evaluate(ctx(good["trial"], good["label"])).value
    finally:
        SHAPES.pop("test_misreport", None)


def test_duplicate_rows_evaluator_crash_and_changed_slice_cannot_hide():
    rows = [{"item_id": f"E-{i}", "seed": s, "pass_rate": True, "slices": ["money_movement"]}
            for i in range(2) for s in (11, 22)]
    base = {"manifest": {"items": 2, "seeds": [11, 22], "eval_set_sha": "x"},
            "rows": rows, "metrics": {"pass_rate": 1.0}, "evaluator_failures": []}
    spec = {"metrics": [{"id": "pass_rate", "blocking": True, "threshold": {"min": .8}}]}
    assert gate.integrity_check(base, base, spec) == []
    duplicate = copy.deepcopy(base)
    duplicate["rows"][-1] = copy.deepcopy(duplicate["rows"][0])
    crash = copy.deepcopy(base)
    crash["evaluator_failures"] = ["grader failed on an otherwise green row"]
    relabel = copy.deepcopy(base)
    relabel["rows"][0]["slices"] = []
    for report in (duplicate, crash, relabel):
        assert gate.check(report, base, spec)[0] == ["integrity"]
