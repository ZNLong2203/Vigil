# All Things Agentic Hackathon — Bộ tài liệu chiến lược

> ⚠️ Đây là **workspace nội bộ** (tiếng Việt). Repo dự thi thật là repo **khác**, và mọi thứ trong đó phải bằng **tiếng Anh**.

**Deadline: 01/09/2026 07:00 GMT+7** · Còn **21 ngày** tính từ 10/08/2026.

---

## Đọc theo thứ tự này

| Doc | Nội dung | Khi nào đọc |
|---|---|---|
| [01 — Brief](docs/01-brief.md) | Toàn bộ yêu cầu chính thức, đã cấu trúc lại: mốc thời gian, stack bắt buộc, 3 track, GEAP, danh mục nộp, giải thưởng | Đọc 1 lần, tra cứu về sau |
| [02 — Rules & Traps](docs/02-rules-and-traps.md) | Eligibility + **10 bẫy loại bài** + các điểm không nhất quán trong tài liệu gốc | **Đọc kỹ ngay hôm nay** |
| [03 — Judging Rubric](docs/03-judging-rubric.md) | Giải mã rubric, **sub-criteria bị lộ trong Official Rules**, cách đạt 6/6 | ⭐ **Quan trọng nhất** |
| [04 — Tracks & Positioning](docs/04-tracks-and-positioning.md) | Chọn track nào, chiến lược "xếp làn" để đủ tư cách 4 giải cùng lúc | Trước khi chốt ý tưởng |
| [05 — Idea Shortlist](docs/05-idea-shortlist.md) | 6 ý tưởng đã chấm điểm + khuyến nghị + cách tự chọn domain | Hôm nay — cần quyết |
| [06 — Architecture Blueprint](docs/06-architecture-blueprint.md) | Kiến trúc tham chiếu domain-agnostic, 7 cơ chế ăn điểm, mỗi cơ chế = 1 cảnh demo | Ngày 2–3 |
| [07 — Build Plan 21 ngày](docs/07-build-plan-21d.md) | Kế hoạch theo ngày, 9 milestone, ma trận cắt scope | Mở mỗi sáng |
| [08 — Submission Kit](docs/08-submission-kit.md) | Checklist nộp bài, **script video 4 phút**, template README tiếng Anh, bonus content | Từ ngày 17 |
| [09 — Cost & Ops](docs/09-cost-and-ops.md) | Giữ chi phí <$50, 3 lớp phòng thủ chống agent chạy hoang | Ngày 1 |
| [**10 — LOCKED SPEC: Vigil**](docs/10-locked-spec.md) | 🔒 Spec đã chốt: đội 5 agent, scope cắt cho solo, 5 cảnh demo, định nghĩa "xong" từng milestone | ⭐ **Đọc trước khi code** |

---

## TL;DR chiến lược

**Đề bài thật sự muốn gì:** agent **chạy nền, bất đồng bộ, nhiều bước, tự quyết định** — không phải chatbot có tool.

**Cách ăn điểm cao:**

1. **Track khuyến nghị: Fortified Enterprise Fleet** — ít bài nộp nhất (rào cản cao), rubric của nó thưởng đúng thứ Grand Prize cần, và tự động đủ tư cách giải *Best Architectural Design*.
2. **Nhưng build cho một "Unlikely Hero"** — người dùng **ngoài** vai trò doanh nghiệp. Official Rules nói thẳng judge tìm điều này. Đây là cách khác biệt hóa rẻ nhất giữa ~1080 người tham gia.
3. **Friction phải là của chính bạn** (mandate "BYOF"). Không điền được câu *"Mỗi tuần tôi mất ___ giờ làm ___"* bằng sự thật → chưa nên code.
4. **Ba cảnh demo quyết định thắng thua:**
   - `kill -9` worker giữa chừng → resume → **chỉ 1 bản ghi trong DB** (idempotency trap)
   - Prompt injection giấu trong PDF scan → guardrail chặn → audit log
   - Agent tự đề xuất cải tiến chính nó → **anti-gaming judge bắt được nó lách metric** → reject
5. **Bonus +1.0 là ~17% điểm cuối, tốn ~1 ngày công**: blog (+0.2) + social có hashtag (+0.2) + Gemma/Veo/Lyria (+0.6). Rất nhiều team sẽ bỏ qua.
6. **Chặn cứng 4 ngày cuối cho video + docs** — 30% điểm nằm ở thứ không phải code, và judge **không bắt buộc phải chạy code của bạn**.

**Bốn làn giải nhắm cùng lúc với một bài:** Track Prize ($20k) · Individual/Hobbyist ($10k × 2) · Best Architectural Design ($5k × 2) · Best Multimodal UX ($5k × 2). Xem [doc 04](docs/04-tracks-and-positioning.md).

---

## 🔴 Việc cần làm HÔM NAY (10/08)

- [ ] Nộp form xin **$150 Google Cloud credits** → https://forms.gle/riGhgDSHkHeMx8Ca6 *(duyệt mất tới 72h; hạn cuối 28/08 12:00 PT)*
- [ ] Đăng ký **Devpost** + tạo project draft
- [ ] Tạo **Google Cloud project** + bật billing + **Budget alerts** ($20/$50/$100)
- [ ] Claim **GEAR badge** (Google Developer Program) — 35 learning credits miễn phí
- [ ] **Chốt domain + Unlikely Hero** ([doc 05](docs/05-idea-shortlist.md))
- [ ] `git init` + **commit đầu tiên hôm nay** (rules: "New Projects Only", phải sau 03/08/2026)
- [ ] Đặt lịch xem webinar **11/08** (multi-agent patterns) và **13/08** (long-running agent — quan trọng nhất)

---

## Trạng thái quyết định — 🔒 ĐÃ CHỐT 10/08

| Quyết định | Trạng thái | Ghi chú |
|---|---|---|
| Track | ✅ **Fortified Enterprise Fleet** | Ít đối thủ nhất; đủ tư cách luôn giải Best Architectural Design |
| Domain / Unlikely Hero | ✅ **Người chăm sóc người thân tại nhà** | Friction thật, dữ liệu bẩn & đa phương thức, chu kỳ nhiều tuần |
| Tư cách nộp | ✅ **Cá nhân solo** | Đủ điều kiện làn Individual/Hobbyist ($10k × 2 suất) |
| Tên sản phẩm | ✅ **Vigil** | *"An agent fleet that keeps watch, so you don't have to."* |
| Spec | ✅ [docs/10-locked-spec.md](docs/10-locked-spec.md) | 5 agent, 3 view, 5 cảnh demo, scope đã cắt cho solo |
| Repo dự thi (public) | ⬜ chưa tạo | Tạo hôm nay, commit đầu tiên ≥ 03/08/2026 |
| GCP project + credits | ⬜ chưa làm | 🔴 Ưu tiên số 1 hôm nay |

**Khung "enterprise" của Vigil:** care network = 4 "phòng ban" (Family · Clinical · Benefits · Audit), mỗi phòng ban có ranh giới dữ liệu riêng được **Agent Identity cưỡng chế**, cùng dùng chung một **Agent Registry**. Đây là cách thỏa mãn yêu cầu enterprise của track **mà vẫn giữ được câu chuyện con người** — xem [doc 10 §2](docs/10-locked-spec.md).
