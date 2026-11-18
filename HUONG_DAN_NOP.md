# Bài Day 9 đã làm

Đã ghép src Lab 08 hôm trước, hoàn thành Core/Advanced/Expert và sinh report từ script. Không sửa lab8, variant/trap hoặc report bằng tay. Xem docs/eval_card.md và src/reports/verification.log.

## Chạy lại trên Windows

Python 3.11–3.13:
```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r src/requirements.txt -r src/requirements-lab9.txt
.\.venv\Scripts\python.exe scripts/verify_submission.py
.\.venv\Scripts\python.exe scripts/build_submission_docs.py
```
Đánh giá offline, không cần API key. Script kiểm tra expected exit=1 của judge helpful, regression và trap; đó là kết quả đúng, không phải lỗi chạy.

## Đưa lên repo của bạn

Bản ZIP không có lịch sử Git. Clone repo cá nhân vào thư mục mới, tạo nhánh starter/d09, chép nội dung bài hoàn thiện vào đó; không chép .venv hay traces. Sau đó:
```powershell
git add -A
git add -f src/reports
git commit -m "feat: complete Day 9 evaluation and failure analysis"
git push -u origin starter/d09
```
Mở PR starter/d09 → main trong repo cá nhân, dùng PR_DESCRIPTION.md làm mô tả, bật Actions. Chỉ merge sau khi eval-gate và eval-gate-v2 xanh. Nộp link repo lên LMS theo ca học. Tên repo/MSSV chưa được xác nhận; kiểm tra mẫu tên trong đề trước khi nộp.

Chưa push, mở PR, merge hoặc nộp LMS trong phiên làm việc này. Không coi kiểm tra offline là bằng chứng CI đã xanh.
