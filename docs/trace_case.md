# Trace case: C-002@11

| Trường | Nội dung |
|---|---|
| Trial | seeded_regression C-002@11; report `E-seeded_regression-20261118-74d6` |
| Triệu chứng | Lab 8 báo `status resolved != denied`; ledger hoàn 20000 VND, nhãn đòi 0 VND |
| Bước sai đầu tiên | Event 3 `model_override`, payload `{"delay_days": 5}` |
| Vì sao đầu tiên | Event 1 handoff đúng claim/phạm vi readonly; event 2 lookup_order visible=true, DB delay_days=2; đến event 3 mới lấy 5 ngày từ ticket ghi đè DB |
| Failure mode | FM-03 ticket_trust |
| Hậu quả | Event 4 quote=20.000 VND, event 6 reply xác nhận hoàn; ledger có 1 dòng thay vì 0 |
| Đối chứng | fixed cùng claim@seed không có model_override; event 3 quote=0, reason=no_entitlement; denied, ledger 0 |
| Regression test | `tests/test_lab9_regressions.py::test_first_wrong_decision_ticket_overrides_db`: khẳng định event sai đầu tiên; RefundAmountCorrect fail trên seeded_regression và pass trên fixed |
| Chưa chắc chắn | Không kết luận về xác suất lỗi của LLM thật; trace dùng MockLLM. Approval host cho phép không đồng nghĩa đủ điều kiện chính sách |

Chạy lại từ `src/`:
```powershell
python -m lab9.trace_case --shape seeded_regression --claim C-002 --seed 11
python -m lab9.trace_case --shape fixed --claim C-002 --seed 11
python -m pytest -q -o addopts= tests/test_lab9_regressions.py
```

[Bằng chứng trace đầy đủ](../src/reports/trace_evidence.json), [taxonomy](failure_taxonomy.md).
