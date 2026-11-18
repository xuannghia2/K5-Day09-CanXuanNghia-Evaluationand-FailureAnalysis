# Judge audit

FAIL là lớp dương: nhiệm vụ judge là phát hiện lỗi.

| Tiêu chí | n | κ | Precision | Recall | TP/FP/FN/TN | Quyết định |
|---|---:|---:|---:|---:|---|---|
| tone | 100 | 0.757 | 0.857 | 0.8 | 24/4/6/66 | Dùng cho tone, đạt floors |
| helpful | 100 | 0.375 | 1.0 | 0.3 | 9/0/21/70 | Loại khỏi gate |

Floors: κ ≥ 0,6; P ≥ 0,8; R ≥ 0,7. κ không xác định làm calibration FAIL.

Rogan–Gladen tone: observed=0.28 → corrected=0.3; helpful: 0.09 → 0.3. Đây là ước lượng tỷ lệ lỗi tổng thể, không thay nhãn từng case.

| Case | Reply | Human / Judge | Kết luận audit | Sửa rubric |
|---|---|---|---|---|
| H-008 | Em đã hoàn tiền cho anh rồi nha, anh check giúp em. | FAIL / PASS | Đồng ý human: xưng hô suồng sã, trộn tiếng Anh. | FAIL khi dùng anh/em/nha và câu mệnh lệnh thân mật không phù hợp. |
| H-017 | Dạ, bạn ơi LogiX đã hoàn 25.000đ cho đơn O-606 rồi nha. | FAIL / PASS | Đồng ý human: mở đầu lịch sự chưa đủ bù 'bạn ơi', 'rồi nha'. | Chấm toàn câu; từ 'Dạ' không tự động cho PASS. |
| H-029 | Dạ, vui lòng chờ. Hệ thống đang xử lý, không cần nhắn thêm. | FAIL / PASS | Đồng ý human: 'không cần nhắn thêm' mang tính gạt khách. | FAIL khi hạn chế khách liên hệ dù có 'Dạ'. |
| H-042 | Dạ, đơn O-808 đã hoàn 120.000đ. Tiền về trong 3–5 ngày ạ. | PASS / FAIL | Đồng ý human: ngắn nhưng lịch sự, có thông tin thời gian. | Không yêu cầu lời xin lỗi hoặc lời cảm ơn trong mọi câu. |
| H-051 | Dạ, LogiX đã refund 90.000đ cho đơn O-202 ạ. | PASS / FAIL | Đồng ý human: dùng thuật ngữ refund chưa đủ để coi giọng điệu bất lịch sự. | Tách chất lượng bản địa hóa khỏi tiêu chí tone; không phạt từ tiếng Anh đơn lẻ. |
| H-070 | Dạ, LogiX đã hoàn 90.000đ cho đơn O-909 ạ 😂😂 | FAIL / PASS | Đồng ý human: emoji cười lặp lại không phù hợp giao dịch tiền. | Bổ sung ví dụ emoji không chuyên nghiệp. |

Helpful bỏ sót 21/30 lỗi dù precision=1.0: recall=0.3 và κ=0.375 đều dưới floors. Không dùng làm gate; yêu cầu judge đối chiếu đúng yêu cầu, kết quả host, số tiền và bước tiếp theo, rồi hiệu chuẩn lại bằng nhãn người mới.

Tone chỉ đủ điều kiện dùng cho tiêu chí giọng điệu; chưa đưa thành metric blocking trong gate hiện tại vì eval không có nhãn tone mới cho từng trial. Tiền và approval luôn chấm bằng code.

Các sửa rubric là đề xuất từ audit, chưa có bằng chứng cải thiện trên held-out. CSV replay công khai không thay thế một tập nhãn người mới.

Nguồn: [judge_calibration.json](../src/reports/judge_calibration.json), [log chạy](../src/reports/verification.log).
