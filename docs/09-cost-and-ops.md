# 09 — Cost control & Ops runbook

> Mục tiêu: hoàn thành cả hackathon trong **$150 credits**, lý tưởng là dưới **$40**.

---

## 1. Ngày đầu tiên — thiết lập phòng thủ

```bash
# 1. Project riêng cho hackathon (dễ xóa sạch sau này)
gcloud projects create <PROJECT_ID>
gcloud config set project <PROJECT_ID>

# 2. Bật đúng những API cần
gcloud services enable \
  run.googleapis.com \
  aiplatform.googleapis.com \
  pubsub.googleapis.com \
  firestore.googleapis.com \
  cloudtasks.googleapis.com \
  cloudscheduler.googleapis.com \
  secretmanager.googleapis.com \
  cloudtrace.googleapis.com \
  storage.googleapis.com
```

**Budget alerts (làm qua Console → Billing → Budgets & alerts):**
- Ngưỡng cảnh báo: **$20 / $50 / $100 / $140**
- Gửi email tới địa chỉ bạn check hằng ngày

---

## 2. Cấu hình Cloud Run chống đốt tiền

```bash
gcloud run deploy <SERVICE> \
  --min-instances=0 \          # scale to zero — KHÔNG BAO GIỜ để >0
  --max-instances=3 \          # chặn spike; hackathon không cần hơn
  --cpu=1 --memory=512Mi \     # bắt đầu nhỏ, tăng khi thật sự cần
  --concurrency=10 \
  --timeout=900 \              # worker dài hạn cần timeout cao
  --no-allow-unauthenticated   # bảo vệ endpoint
```

**Nếu cần public URL cho judge:** dùng `--allow-unauthenticated` **nhưng bắt buộc thêm API key middleware** trong app. Traffic bot quét `.run.app` là có thật và nó đốt credit.

**Cloud Run Jobs** cho worker chạy dài (không phải service): trả tiền theo thời gian chạy job, không giữ instance.

---

## 3. Chiến lược model (chi phí giảm 10–50×)

| Việc | Model | Vì sao |
|---|---|---|
| Phân loại / định tuyến | **Gemma** | rẻ nhất; chạy Cloud Run CPU được |
| Redact PII | **Gemma** | dữ liệu không rời biên |
| Trích xuất ảnh/PDF/voice | **Gemini Flash** | multimodal native, rẻ |
| Lập kế hoạch, quyết định | **Gemini Flash** | mặc định cho MỌI thứ |
| Reasoning cuối phức tạp | **Gemini Pro** | chỉ khi Flash thất bại |
| Anti-gaming judge | **Gemini Pro** | cần model mạnh |

**Quy tắc:** mặc định Flash. Chỉ escalate lên Pro khi có **điều kiện tường minh trong code** (ví dụ: `confidence < 0.7` hoặc `conflict_detected`). Ghi lại số lần escalate — đây là một con số hay để đưa vào blog và README.

### Cắt token
- [ ] **Context compression**: đừng nhét cả history. Tóm tắt L1 mỗi N bước.
- [ ] **Structured output** thay vì văn xuôi → ít token ra hơn, không cần retry parse.
- [ ] **Prompt caching** nếu SDK hỗ trợ (system prompt dài dùng lại nhiều lần).
- [ ] **Ngân sách token cứng mỗi run** — vừa chống loop vừa chống cháy ví. Bắt buộc có.
- [ ] Cache kết quả trích xuất theo hash file — đừng OCR lại cùng một PDF 20 lần khi test.

---

## 4. Storage & Data

```
Cloud Storage : lifecycle rule xóa sau 30 ngày cho bucket raw/
Firestore     : free tier rất rộng — đủ cho hackathon
Vector search : dùng serverless (Firestore vector / Vertex Vector Search)
                KHÔNG dựng cluster always-on
Logs          : đặt retention ngắn (30 ngày), tránh log payload lớn
```

⚠️ **Đừng log full prompt/response ở mức INFO** trong vòng lặp — log volume là chi phí ẩn phổ biến nhất.

---

## 5. Thói quen hằng ngày

```bash
# Xem chi phí hôm nay
# Console → Billing → Reports → group by service, filter: today
```

- Mỗi tối: check billing. **>$5/ngày là tín hiệu đỏ** — điều tra ngay.
- Mỗi tối: `gcloud run services list` → có service nào bạn quên tắt không?
- Trước khi đi ngủ: đảm bảo không có Cloud Scheduler job chạy mỗi phút.

---

## 6. Thời điểm demo

1. Bật hết service, chạy warm-up để tránh cold start làm hỏng video
2. Quay đầy đủ **tất cả** proof: Cloud Run dashboard, Logging, Trace, Vertex AI, URL `.run.app`
3. Chụp screenshot độ phân giải cao cho README
4. **Sau khi quay xong** → giảm về min-instances=0, tắt Scheduler

---

## 7. Sau khi nộp bài

Rules yêu cầu project phải **truy cập được cho judge tới hết Judging Period (01/10/2026)**, nhưng đề bài cũng nói rõ app **không cần live** — chỉ cần proof.

**Cách cân bằng:**
- Giữ **UI đọc-only** live (rẻ, scale-to-zero) với dữ liệu synthetic đã seed → judge vẫn click được
- Tắt các worker nặng và Scheduler
- Trong README ghi rõ: *"Background workers are disabled to control cost; full execution is shown in the demo video and reproducible with `./deploy.sh`."* — điều này **được phép** và đúng tinh thần cost tips của BTC
- Sau 01/10/2026: `gcloud projects delete <PROJECT_ID>`

---

## 8. Bảng ngân sách ước tính

| Hạng mục | Ước tính 21 ngày |
|---|---|
| Gemini Flash (dev + test, vài nghìn call) | $5–15 |
| Gemini Pro (dùng chọn lọc) | $3–10 |
| Gemma (Cloud Run CPU hoặc API) | $0–8 |
| Cloud Run (scale-to-zero) | $0–5 |
| Firestore / Storage / Pub/Sub | $0–3 |
| Veo / Lyria (vài lần sinh) | $2–10 |
| Vector search serverless | $0–5 |
| **Tổng** | **~$10–56** |

→ $150 credits là **thừa** nếu bạn kỷ luật. Rủi ro lớn nhất không phải giá đơn vị, mà là **một vòng lặp agent chạy hoang trong đêm**. Ngân sách token cứng + max-instances cap + budget alert là ba lớp phòng thủ bắt buộc.

---

## 9. Ba lớp phòng thủ (bắt buộc có trước khi chạy agent tự động lần đầu)

1. **Trong code**: `MAX_STEPS`, `MAX_TOKENS_PER_RUN`, `MAX_TOOL_CALLS` — vượt là abort + ghi log.
2. **Trong hạ tầng**: `--max-instances=3`, Pub/Sub dead-letter sau 5 lần retry.
3. **Trong billing**: budget alert, và **quota override** cho Vertex AI nếu Console cho phép.

> Đây không chỉ là chống cháy ví — nó **chính là** "loop breaker" mà rubric Architecture đang tìm. Một mũi tên hai đích.
