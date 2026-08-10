# 07 — Plan 21 ngày (10/08 → 31/08/2026)

> Hạn chót: **31/08/2026 17:00 PT = 01/09/2026 07:00 GMT+7**.
> Nguyên tắc: **nộp bản hoàn chỉnh ngày 29/08**, hai ngày cuối chỉ để polish.

---

## Nguyên tắc điều hành

1. **Ngày 1 phải có "walking skeleton" đã deploy lên Cloud Run.** Không phải feature — chỉ cần: HTTP trigger → Pub/Sub → worker → gọi Gemini → ghi Firestore → log. Deploy trước, làm đẹp sau. Rất nhiều team chết vì để deploy tới ngày cuối.
2. **Chặn cứng 4 ngày cuối cho video + docs.** 30% điểm nằm ở đó.
3. **Mỗi cơ chế ăn điểm phải kèm một cảnh demo.** Nếu không quay được → không đáng làm.
4. **Quay video từng phần dần trong lúc build**, đừng để dồn.
5. **Timebox tàn nhẫn.** Đến deadline của một feature mà chưa xong → cắt, không gia hạn.

---

## PHASE 0 — Khóa quyết định & dựng nền (10/08 – 12/08)

### Ngày 1 — 10/08 (hôm nay) 🔴 việc gấp
- [ ] **Đăng ký Devpost** + tạo project draft (chiếm chỗ, đặt tên)
- [ ] **Nộp form xin $150 credits** → https://forms.gle/riGhgDSHkHeMx8Ca6 *(duyệt mất tới 72h làm việc — làm NGAY)*
- [ ] Tạo Google Cloud project mới + bật billing + **đặt Budget Alert $20 / $50 / $100**
- [ ] Claim **GEAR badge** trên Google Developer Program (35 learning credits + lab miễn phí)
- [ ] **Chốt domain & Unlikely Hero** (dùng 5 câu hỏi ở doc 05 §Khuyến nghị cuối)
- [ ] Viết **1 câu định vị** (doc 04 §5) và dán lên tường
- [ ] `git init` — **commit đầu tiên hôm nay** (chứng minh "new project")
- [ ] Repo **public** ngay từ đầu

### Ngày 2 — 11/08
- [ ] 📺 **Webinar: Multi-Agent Orchestration Patterns của ADK** (08:30 hoặc 21:00 PT)
- [ ] Đọc docs: ADK quickstart, Vertex AI Agent Engine, Memory Bank, Model Armor — **chốt version/API surface thật**, đừng code theo trí nhớ
- [ ] Bật API: Vertex AI, Cloud Run, Pub/Sub, Firestore, Cloud Tasks, Scheduler, Secret Manager, Cloud Trace
- [ ] Viết `ARCHITECTURE.md` v0 (sơ đồ nháp) — **kiến trúc trước code**

### Ngày 3 — 12/08 ✅ **Milestone M1: Walking skeleton on Cloud Run**
- [ ] `POST /events` (Cloud Run) → publish Pub/Sub → worker consume → gọi Gemini Flash → ghi Firestore
- [ ] Secret Manager cho API key (**không hardcode, kể cả ngày 1**)
- [ ] Structured logging + correlation ID
- [ ] `deploy.sh` một lệnh
- [ ] 📸 **Chụp màn hình Cloud Run dashboard + URL `.run.app` ngay hôm nay** (tư liệu video)

> ❗ Nếu hết ngày 12/08 mà M1 chưa chạy → **giảm scope ngay**, chuyển sang ý tưởng C (Tender Hunter, doc 05).

---

## PHASE 1 — Lõi agent & orchestration (13/08 – 17/08)

### Ngày 4 — 13/08
- [ ] 📺 **Webinar: Long-Running Agent — crash recovery, human approval, idempotency trap** ⭐ *quan trọng nhất với bài này*
- [ ] Dựng **state machine** tường minh + schema checkpoint trong Firestore
- [ ] Định nghĩa **Registry schema** (doc 06 §③⑥)

### Ngày 5–6 — 14/08–15/08
- [ ] **Orchestrator (ADK)**: đọc state → tra Registry → chọn worker → gán idempotency key → checkpoint
- [ ] **2 worker đầu tiên** với **tool scope tách biệt, cưỡng chế** (worker A không import được tool của worker B)
- [ ] Structured output (JSON schema) cho mọi LLM call — không parse văn xuôi
- [ ] Retry + exponential backoff + **dead-letter topic**

### Ngày 7 — 16/08 ✅ **Milestone M2: Multi-agent end-to-end**
- [ ] Một sự kiện thật đi hết chuỗi: ingest → orchestrator → 2 worker → side-effect ghi vào DB
- [ ] 🎥 **Quay lần 1** (raw footage, chưa dựng): terminal log + Firestore cập nhật

### Ngày 8 — 17/08
- [ ] **Ingestion đa phương thức**: ảnh + PDF scan + voice note → Gemini Flash multimodal → structured event
- [ ] Cloud Storage + lifecycle rule 30 ngày
- [ ] Chuẩn bị **synthetic dataset** (đủ bẩn: ảnh nghiêng, chữ viết tay, voice lẫn 2 ngôn ngữ, PDF chất lượng thấp)

---

## PHASE 2 — Những thứ ăn điểm (18/08 – 23/08)

### Ngày 9 — 18/08 ✅ **Milestone M3: Idempotency + crash-resume**
- [ ] Idempotency key = `hash(run_id, step_id, canonical_payload)`
- [ ] Resume-from-checkpoint sau restart
- [ ] `scripts/demo_chaos.sh` — kill worker giữa chừng
- [ ] 🎥 **Quay cảnh demo #3**: kill → restart → resume → **chỉ 1 bản ghi trong DB**

### Ngày 10 — 19/08 ✅ **Milestone M4: Trust boundary**
- [ ] **Gemma** redactor (Cloud Run hoặc API) → tokenize PII trước khi vào Gemini *(bonus +0.2)*
- [ ] **Model Armor** trên mọi input không tin cậy
- [ ] Chuẩn bị **payload prompt-injection** trong PDF synthetic
- [ ] 🎥 **Quay cảnh demo #1**: injection bị chặn + audit log

### Ngày 11 — 20/08
- [ ] 📺 **Webinar: Self-Evolving Agent** ⭐
- [ ] **Watchdog/verifier agent**: bắt mâu thuẫn, cắt loop, escalate
- [ ] **Loop breaker**: giới hạn bước + ngân sách token + phát hiện lặp trạng thái
- [ ] 🎥 **Quay cảnh demo #2**: hallucination bị chặn trước khi gây side-effect

### Ngày 12 — 21/08 ✅ **Milestone M5: Action Gate**
- [ ] Policy engine: `auto_allow` / `require_approval` / `deny` theo rủi ro × độ tin cậy
- [ ] Human approval qua UI
- [ ] Compensating action (saga) khi bước sau fail
- [ ] 🎥 **Quay cảnh demo #4**: approval card + một hành động bị **deny** kèm lý do

### Ngày 13 — 22/08 ✅ **Milestone M6: Memory phân tầng**
- [ ] L0 session → L1 working (nén) → L2 episodic vector (serverless) → L3 **Memory Bank**
- [ ] Provenance trên mọi mẩu nhớ: `source_uri`, `observed_at`, `confidence`, `superseded_by`
- [ ] **Conflict resolution**: hai fact mâu thuẫn → nêu ra, không tự ghi đè
- [ ] Seed một **case chạy 3 tuần** (backdate timestamp) để demo trí nhớ dài hạn

### Ngày 14 — 23/08 ✅ **Milestone M7: Registry + self-evolution**
- [ ] Agent Registry: version, owner, capability schema, tool scope, `callable_by`, eval score
- [ ] **Eval set cố định** (20–30 case golden)
- [ ] Vòng: traces + user corrections → đề xuất instruction mới → chạy eval → **anti-gaming judge** → promote/reject
- [ ] 🎥 **Quay cảnh demo #5**: một lần promote thành công + một lần bị chặn vì gaming metric

---

## PHASE 3 — UX, Observability, Polish (24/08 – 26/08)

### Ngày 15 — 24/08 ✅ **Milestone M8: Glass-box UI**
- [ ] **Reasoning Trace view**: cây agent, mỗi node hiện input/output/cost/latency/policy decision
- [ ] Timeline nhiều tuần
- [ ] Inbox approval
- [ ] Click một side-effect → truy ngược toàn bộ chuỗi lý do

### Ngày 16 — 25/08
- [ ] **OpenTelemetry** → Cloud Trace, span cho mọi LLM/tool/agent hop/policy decision
- [ ] Audit log có thể export
- [ ] **Veo**: video digest 15s tóm tắt tuần *(bonus +0.2, và ăn Multimodal UX)*
- [ ] **Lyria** hoặc TTS: audio digest / cue theo mức khẩn *(bonus +0.2)*

### Ngày 17 — 26/08 ✅ **Milestone M9: Feature freeze** 🔒
- [ ] **NGỪNG THÊM FEATURE.** Từ đây chỉ sửa lỗi và làm tài liệu.
- [ ] Chạy end-to-end 3 lần liên tiếp không lỗi
- [ ] Sửa mọi crash trên happy path
- [ ] Dọn repo: xóa code chết, secret, TODO xấu hổ

---

## PHASE 4 — Submission kit (27/08 – 29/08)

### Ngày 18 — 27/08 — Tài liệu
- [ ] 📺 Webinar: Architecting Agent Memory *(nếu còn thời gian)*
- [ ] **README.md tiếng Anh** theo template ở doc 08: friction → what it does → proof on GCP → mandatory stack compliance → **spin-up instructions** → judging-criteria mapping → findings & learnings → pre-existing work disclosure
- [ ] **Architecture diagram sạch** (Excalidraw / draw.io / Mermaid) → export PNG + nhúng vào README
- [ ] **6 ADR** trong `docs/adr/`
- [ ] `docs/compliance.md`: synthetic data, PII handling, data residency, disclaimer
- [ ] Test spin-up instructions **trên máy sạch** (hoặc Cloud Shell) — nếu bạn không chạy được thì judge cũng không

### Ngày 19 — 28/08 — Video 🎬
- [ ] Viết script theo doc 08 §Video (target **3:40**)
- [ ] Quay: **một take liền mạch ≥60–90s** cho phần agent chạy thật
- [ ] Bắt buộc có trên màn hình: **Cloud Run dashboard**, **Cloud Logging live**, **URL `.run.app`**, **Firestore cập nhật realtime**
- [ ] Dựng, thêm **caption tiếng Anh**, upload YouTube **PUBLIC**
- [ ] 🔴 **Hạn chót xin credits là hôm nay 12:00 PT** — nếu chưa xin thì xin ngay
- [ ] Kiểm tra link video bằng cửa sổ ẩn danh

### Ngày 20 — 29/08 — ✅ **NỘP BÀI** + Bonus
- [ ] **Nộp bản hoàn chỉnh trên Devpost** (còn 2 ngày để sửa draft)
- [ ] Blog dev.to / Medium: "How I built X" + **câu disclosure bắt buộc** *(+0.2)*
- [ ] Post LinkedIn/X kèm **`#AllThingsAgenticHackathon`** *(+0.2)*
- [ ] Nếu repo private → share `testing@devpost.com` **và** `cloudhackathons@google.com` *(khuyến nghị: để public)*

---

## PHASE 5 — Đệm (30/08 – 31/08)

### Ngày 21–22 — 30/08–31/08
- [ ] Nhờ 2 người ngoài xem video + đọc README → hỏi "bạn hiểu nó làm gì không?"
- [ ] Sửa theo feedback (chỉ những gì rẻ)
- [ ] Kiểm tra lại **toàn bộ checklist doc 08**
- [ ] Giữ service sống tới khi nộp, ghi lại proof, rồi **cân nhắc tắt** để tiết kiệm credit
- [ ] 🚫 **Không refactor. Không thêm feature.**

---

## Ma trận cắt scope (khi chậm tiến độ)

Cắt theo thứ tự này — trên xuống dưới, giữ lại phần dưới cùng bằng mọi giá:

| Ưu tiên cắt | Hạng mục | Mất gì |
|---|---|---|
| Cắt đầu tiên | Lyria audio digest | −0.2 bonus |
| 2 | Veo video digest | −0.2 bonus, yếu Multimodal UX |
| 3 | Self-evolution loop (M7) | Mất twist mạnh — cân nhắc kỹ |
| 4 | Agent thứ 3–4 (giữ 2 worker) | Yếu "multi-agent xứng đáng" |
| 5 | Memory Bank L3 (giữ L0–L2) | Yếu "weeks of context" |
| **KHÔNG BAO GIỜ CẮT** | Idempotency + crash-resume | Lõi Architecture |
| **KHÔNG BAO GIỜ CẮT** | Trust boundary / guardrail demo | Cảnh demo mạnh nhất |
| **KHÔNG BAO GIỜ CẮT** | Video 4 phút + README + diagram | 30% điểm |
| **KHÔNG BAO GIỜ CẮT** | Proof chạy trên Google Cloud | Fail Stage One |

---

## Nhịp làm việc hằng ngày

```
Sáng   :  1 câu — hôm nay milestone nào? Nếu không có milestone → sai plan.
Trong  :  Code → deploy lên Cloud Run ngay → quay lại footage nếu có gì đáng quay.
Tối    :  Commit + push. Cập nhật CHANGELOG. Kiểm tra Cloud Billing.
Thứ 7  :  Chạy end-to-end đầy đủ 1 lần. Ghi lại thời gian và chi phí.
```

**Kiểm tra hằng ngày:** Cloud Billing hôm nay tiêu bao nhiêu? Nếu >$5/ngày → xem lại min-instances và max-instances ngay.
