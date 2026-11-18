"""Package sources and generated evidence; omit local runtime and temporary files."""
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT.parent / "Day09-CanXuanNghia-HoanThien.zip"
required = ["docs/failure_taxonomy.md", "docs/judge_audit.md", "docs/trace_case.md", "docs/eval_card.md",
            "docs/PRD_v1.1.md", "PR_DESCRIPTION.md", "HUONG_DAN_NOP.md", "src/reports/verification.json"]
for name in required:
    if not (ROOT / name).is_file():
        raise RuntimeError(f"Missing {name}; run verification and documentation scripts first")
checks = json.loads((ROOT / "src/reports/verification.json").read_text(encoding="utf-8"))
assert checks and all(x["exit"] == x["expected"] for x in checks)
excluded = {".venv", ".git", "__pycache__", ".pytest_cache", "traces", "node_modules", "student_drop"}
with ZipFile(DEST, "w", ZIP_DEFLATED) as archive:
    for path in sorted(ROOT.rglob("*")):
        relative = path.relative_to(ROOT)
        if not path.is_file() or any(p in excluded for p in relative.parts):
            continue
        if relative.as_posix().startswith("src/eval/instructor/") or path.suffix in {".pyc", ".sqlite"}:
            continue
        archive.write(path, ROOT.name + "/" + relative.as_posix())
with ZipFile(DEST) as archive:
    assert archive.testzip() is None
print(f"Created {DEST} ({DEST.stat().st_size:,} bytes)")
