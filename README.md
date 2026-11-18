# K5 · Day 9 · Lab — Evaluation & Failure Analysis (LogiX-VN)

Bài làm Cấn Xuân Nghĩa: xem [hướng dẫn chạy và nộp](HUONG_DAN_NOP.md),
[eval card](docs/eval_card.md), [mô tả PR](PR_DESCRIPTION.md) và
[log kiểm tra](src/reports/verification.log).
Chạy lại toàn bộ: `python scripts/verify_submission.py`, sau đó
`python scripts/build_submission_docs.py` (dùng Python trong môi trường đã cài requirements).

> Nối tiếp Lab 8. Lab 8 trả lời "agent có chạy không"; Lab 9 trả lời **"làm sao biết bản mới tốt hơn — và chặn được bản tệ trước khi merge"**.
> Không cần API key: MockLLM + judge replay. **Không Langfuse / OTel** (observability học ở Day 14).

## Bạn sẽ làm gì (**bài cá nhân** · giờ trên lớp và hạn nộp theo ca làm bài, xem LMS của ca)
Giờ trong bảng là của ca 13:30–17:00; ca khác dời các mốc tương ứng.

| M | Giờ | Việc | Lệnh kiểm tra |
|---|---|---|---|
| M0 | 13:30 | Fork repo này, chép `src/` của repo gốc Day 8 vào, cài đặt và sinh eval set | `python -m lab9.smoke` và `python -m lab9.evalset --build` |
| M1 | 13:45 | Taxonomy ≥5 failure mode từ trace; gắn `failure_modes` cho eval set | `python -m lab9.evalset --check` |
| M2 | 14:30 | Judge-the-judge: cài `kappa`, P/R, Rogan-Gladen; audit ≥5 bất đồng | `python -m lab9.judge --csv data/eval/judge_tone_public.csv --audit 5` |
| M3 | 15:15 | Trajectory assertion: `ApprovalBypass`, `RefundAmountCorrect` + 1 metric cho FM-08 | `python -m pytest -q -m student -o addopts= -k "lab9 and not advanced"` |
| M4 | 16:00 | Paired bootstrap + CI gate: chặn `seeded_regression`, cho qua `fixed` | `python -m lab9.gate ...` (exit 1 / exit 0) |
| — | 16:45 | Eval card + PRD v1.1; mở PR trong bản fork, CI xanh thì merge vào `main` (Core 60đ nên xong trên lớp) | xem `SUBMISSION.md` |
| M5 | sau 17:00 | **Advanced.** Eval set v2: adversarial pack + `fm_map.yaml`; slice gate (`money_movement`, `adversarial`) | `python -m lab9.evalset --v2 --build` |
| M6 | sau 17:00 | **Advanced.** Nhiễu: A/A trên 2 bộ seed, `pass@k` / `pass^k`, ngưỡng `pass_hat_5` | `python -m lab9.mutation --aa 66,77,88,99,110 ...` |
| M7 | sau 17:00 | **Expert.** Gate chống gian lận eval: `integrity_check` + ratchet; scorecard đột biến | `python -m lab9.traps` và `python -m lab9.mutation ...` |

## Cài đặt (M0): fork repo này, chép code gốc Day 8 vào

**Bài cá nhân.** Mỗi bạn làm trên bản fork của riêng mình, không làm chung trên repo nhóm Lab 8: ai cũng phải tự đi hết quy trình evaluation.

Repo này **không chạy độc lập**: nó chỉ có `src/lab9/`, docs và workflow. Code agent, dữ liệu và `requirements.txt` lấy từ **repo gốc Day 8** ([`K5-Day8-From-Workflows-to-Agents`](https://github.com/VinUni-AI20k/K5-Day8-From-Workflows-to-Agents)). Hai thư mục `src/` không trùng file nào, nên chép thẳng được.

**Dùng code gốc Day 8, không cần bài Lab 8 của nhóm.** M0–M4 (baseline, gate, `fixed`, `seeded_regression`) đều chạy trên shape `swarm`, tức `lab8/shapes/swarm_reference.py` do giảng viên cung cấp, không dùng `workflow`/`single`/`orchestrator` của nhóm. Lấy code gốc thì mọi người chạy cùng một agent, ra cùng trace, và không ai lỡ mang theo `src/lab8/` đã sửa.

**Lab 8 bị khóa, trace cố định.** Không sửa file nào trong `src/lab8/` (trừ 10 điểm). Trace không commit sẵn: `lab9.eval` chạy lại agent bằng MockLLM trên 14 item × 5 seed cố định, nên chạy lần nào cũng ra cùng một trace. Việc của bạn là eval và phân tích dựa trên trace đó: taxonomy, judge calibration, grader, bootstrap gate.

**1. Trên GitHub.** Bấm **Fork** repo này về tài khoản của bạn và đặt tên theo mẫu
`K5-L3A-DAY09-HoVaTen-MSSV-EvaluationandFailureAnalysis`.
Sau đó vào tab **Actions** của bản fork, bấm bật workflow: GitHub tắt sẵn workflow trên repo fork, không bật thì job `eval-gate` không chạy.

**2. Trên máy** (macOS / Linux):
```bash
# Clone bản fork của bạn và repo gốc Day 8 vào cùng một thư mục
git clone https://github.com/<github-cua-ban>/K5-L3A-DAY09-HoVaTen-MSSV-EvaluationandFailureAnalysis lab9
git clone https://github.com/VinUni-AI20k/K5-Day8-From-Workflows-to-Agents day8-goc

# Tạo nhánh làm bài, chép src/ của Day 8 vào src/ của bản fork.
# Chỉ chép src/: KHÔNG chép README, .gitignore, .github của Day 8.
cd lab9
git switch -c starter/d09
cp -R ../day8-goc/src/. src/
git add -A && git commit -m "chore: add day8 source"

# Cài và kiểm tra (Python 3.11–3.13). Với uv: `uv venv && source .venv/bin/activate` trước
cd src
uv pip install -r requirements.txt -r requirements-lab9.txt   # không dùng uv: python -m pip install ...
python -m lab9.smoke                    # M0 PASS
python -m lab9.evalset --build          # sinh eval_set_v1.jsonl + labels_v1.json (nhãn TÁCH khỏi item)
cd .. && git add -A && git commit -m "chore: build eval set v1"
```

Windows (PowerShell), cùng các bước trên:
```powershell
git clone https://github.com/<github-cua-ban>/K5-L3A-DAY09-HoVaTen-MSSV-EvaluationandFailureAnalysis lab9
git clone https://github.com/VinUni-AI20k/K5-Day8-From-Workflows-to-Agents day8-goc
cd lab9
git switch -c starter/d09
Copy-Item -Recurse -Force ..\day8-goc\src\* src\
git add -A; git commit -m "chore: add day8 source"
cd src
python -m venv .venv; .\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt -r requirements-lab9.txt
python -m lab9.smoke
python -m lab9.evalset --build
cd ..; git add -A; git commit -m "chore: build eval set v1"
```

Kiểm tra nhanh sau bước 2: `src/` có cả `lab8/` và `lab9/`, và `python -m lab9.smoke` in `M0 PASS`. Từ đây không sửa file nào trong `src/lab8/`; lỡ sửa thì `git restore src/lab8`.

**Baseline cho CI (M4).** Job `eval-gate` đọc `src/reports/baseline_v1.json` trên nhánh, nên file này phải được commit. Sinh sau khi đã hoàn thành M1–M3 trên nhánh làm bài (`-f` để chắc chắn không bị `.gitignore` bỏ qua):
```bash
cd src
python -m lab9.eval --shape swarm --spec config/metric_spec.yaml --out reports/baseline_v1.json
git add -f reports/baseline_v1.json && git commit -m "chore: add eval baseline v1"
```
Workflow chạy khi mở PR (hoặc chạy tay ở tab Actions), không chạy khi push thẳng lên `main`. Mở PR **trong bản fork của bạn** (`starter/d09` → `main`); GitHub hay chọn sẵn repo gốc làm đích, nhớ đổi "base repository" về bản fork.

Ở M0, cả hai lệnh trả exit 0. Các item mới có `failure_modes` rỗng. Sau khi gắn mã lỗi từ taxonomy ở M1, chạy `python -m lab9.evalset --check` và kiểm tra kết quả có 0 lỗi.

**Commit report trước khi merge.** `.gitignore` bỏ qua `src/reports/`, nên `git add -A` không đưa report lên repo. Người chấm mở link repo chỉ thấy nhánh `main`, nên sau M4 (và M5–M7 nếu làm) commit mọi report sinh bằng script:
```bash
cd src
python -m lab9.eval --shape fixed && python -m lab9.eval --shape seeded_regression
git add -f reports/*.json && git commit -m "chore: add eval reports"
```

Job `eval-gate` cần các bài tập đã hoàn thành và baseline M4. Job chạy test học viên, kiểm tra eval set, rồi dùng cùng metric spec và baseline để chấm `swarm` của PR và xác nhận `fixed` qua gate, `seeded_regression` bị chặn ở `pass_rate`.

## Advanced / Expert (M5–M7): làm tiếp tới hạn nộp

Core (M0–M4, 60đ) chứng minh gate chặn được một regression **rõ ràng**. Thực tế khó hơn: regression chỉ nằm ở một slice nhỏ, agent chập chờn 1/5 lần, và người viết PR (hoặc chính agent) có thể "làm đẹp" report thay vì sửa lỗi. M5–M7 tập đúng ba tình huống đó. Giảng viên chấm bằng **variant và trap ẩn** không có trong repo, nên khớp cứng tên variant công khai sẽ không được điểm.

```bash
cd src
# M5 — eval set v2: điền config/fm_map.yaml (cơ chế tấn công -> mã FM của bạn), rồi build + check
python -m lab9.evalset --v2 --build          # mỗi FM bị tấn công cần >= 3 item
# Điền TODO trong config/metric_spec_v2.yaml (slices, pass_hat_5, metric FM-08) và slice_check trong gate.py
python -m lab9.eval --shape swarm --spec config/metric_spec_v2.yaml --out reports/baseline_v2.json

# M6 — nhiễu: cài stats.pass_at_k / pass_hat_k; chọn ngưỡng NGOÀI dải nhiễu A/A
python -m lab9.mutation --spec config/metric_spec_v2.yaml --aa 66,77,88,99,110

# M5–M7 — scorecard: mọi variant công khai qua graders + spec + gate CỦA BẠN
python -m lab9.mutation --spec config/metric_spec_v2.yaml --baseline reports/baseline_v2.json
#   exit 0 chỉ khi 3/3 regression bị chặn và 0 báo nhầm (fixed, honest_refactor phải merge)

# M7 — trap: report đã bị "làm đẹp"; lệnh traps tự chạy gate trên từng file
python -m lab9.eval --shape slice_regression --spec config/metric_spec_v2.yaml --out reports/eval_slice_regression.json
python -m lab9.traps --pr reports/eval_slice_regression.json --baseline reports/baseline_v2.json --spec config/metric_spec_v2.yaml
#   exit 0 chỉ khi gate chặn mọi trap; exit 1 = có trap lọt (tên in ở dòng cuối)
python -m pytest -q -m student -o addopts= -k advanced     # vector công khai; bộ chấm dùng vector ẩn
```

| Variant / trap | Thực tế tương ứng | Gate đúng phải |
|---|---|---|
| `honest_refactor` | đổi lời văn, thêm tool call, cùng kết quả | merge (không báo nhầm) |
| `slice_regression` | lỗi cộng điều khoản chỉ ở claim có hoàn tiền, seed lẻ; trung bình vẫn trên sàn | block qua slice `money_movement` |
| `flaky_regression` | lỗi làm tròn 1/5 seed | block qua `pass_hat_5` |
| `evaluator_errors_as_nan` | grader crash, giá trị thành None/NaN rồi rơi khỏi trung bình | block (integrity) |
| `dropped_failing_rows`, `cherry_picked_seeds` | bỏ dòng fail / chọn seed đẹp | block (integrity: số dòng, tập (item, seed)) |
| `loosened_spec` | hạ ngưỡng, bỏ slice trong cùng PR | block (ratchet với `--base-spec`) |

Lưu ý: một bug chỉ xuất hiện ở 1/3 seed (`rare`) **không** phát hiện ổn định được với 5 seed; nêu điều này trong eval card như một giới hạn về cỡ mẫu, đừng hạ ngưỡng cho tới khi gate "bắt được" nó.

## Công nghệ (kiểm tra 11/2026)
- **pydantic-evals 2.68** — harness chính: `Dataset` / `Case` / `Evaluator`, chạy offline, không cần OTel (ta không dùng span evaluator).
- **scipy.stats.bootstrap(paired=True)** — CI cho hiệu hai phiên bản trên cùng item.
- Judge calibration theo thực hành hiện hành: nhãn nhị phân PASS/FAIL, κ ≥ 0.6, P ≥ 0.8, R ≥ 0.7, κ không xác định ⇒ FAIL, hiệu chỉnh tỉ lệ lỗi bằng Rogan-Gladen.
- Bonus (không bắt buộc): port 3 grader sang **Inspect AI** hoặc **DeepEval** và so kết quả.

## Bản đồ file
```
src/lab9/evalset.py   eval set v1 + provenance + check        (TODO M1: failure_modes)
src/lab9/graders.py   pydantic-evals Evaluators               (TODO M3: 2 grader)
src/lab9/stats.py     confusion, P/R, kappa, RG, bootstrap    (TODO M2, M4)
src/lab9/trace_case.py trace → bước sai đầu tiên cho 1 claim@seed (docs/trace_case.md)
src/lab9/judge.py     calibrate judge từ CSV (replay)
src/lab9/eval.py      chạy 1 shape → reports/eval_<shape>.json có run_id
src/lab9/gate.py      PR vs baseline theo metric_spec → exit 0/1
src/lab9/variants.py  fixed / seeded_regression (+ honest_refactor, slice_, flaky_regression cho v2)
src/lab9/mutation.py  scorecard: variant công khai qua gate của bạn; --aa = nhiễu A/A   (M5–M7)
src/lab9/traps.py     sinh report đã bị làm đẹp để thử integrity_check                  (M7)
src/config/metric_spec_v2.yaml, fm_map.yaml, data/eval/adversarial_v2.json             (TODO M5, M6)
src/config/metric_spec.yaml   ngưỡng (ratchet: cùng eval-set version chỉ được chặt hơn)
```
Quy tắc: không sửa file `lab8/`; không sửa tay `reports/`; không đặt nhãn inline trong item.
