# 08 — Submission Kit: Checklist, Video script, README template

> ⚠️ Mọi thứ trong doc này khi nộp phải **bằng tiếng Anh**.

---

## PHẦN 1 — Checklist nộp bài (in ra, tick tay)

### Stage One (pass/fail — thiếu 1 là trượt)

- [ ] Đã chọn **đúng 1 category** trên form Devpost
- [ ] Dùng **Gemini 3.5 hoặc mới hơn** qua Gemini API hoặc Vertex AI — *chỉ ra file + dòng*
- [ ] Dùng **≥1 Google Agent Framework** (ADK / GenAI SDK / Antigravity SDK / GenKit) — *chỉ ra file + dòng*
- [ ] Dùng **≥1 Google Cloud infra service** (Cloud Run / Cloud SQL / Firestore / GKE / Pub/Sub) — *chỉ ra file + dòng*
- [ ] **Text description** đủ 5 mục: features & functionality · technologies used · other data sources · **findings and learnings** · value proposition
- [ ] **Repo URL** hoạt động (public — hoặc private + đã share `testing@devpost.com` **và** `cloudhackathons@google.com`)
- [ ] **README.md có Spin-up Instructions** từng bước
- [ ] **Architecture Diagram** — file ảnh trong repo **và** nhúng vào README **và** xuất hiện trong video
- [ ] **Demo video** ≤4:00, **public** trên YouTube/Vimeo, tiếng Anh hoặc có phụ đề Anh
- [ ] Video có **bằng chứng backend chạy trên Google Cloud**
- [ ] Repo có **commit đầu ≥ 03/08/2026**
- [ ] Đã **disclose** mọi pre-existing code trong README
- [ ] Hosted URL (nếu có) + testing credentials (nếu private)

### Stage Two (chất lượng)

**Innovation & Utility (40%)**
- [ ] Friction cụ thể, có thật, của chính bạn — nêu rõ trong 20 giây đầu video
- [ ] Có số liệu định lượng ("X giờ/tuần → Y giây")
- [ ] Agent **quyết định**, không chỉ thực thi — có cảnh cho thấy nó chọn giữa nhiều đường
- [ ] Chạy nền / async / dài hạn — có bằng chứng
- [ ] "Unlikely Hero" (nếu Fortified track)
- [ ] Ít nhất **1 "twist"** cơ chế mà bài khác không có

**Architecture (30%)**
- [ ] Idempotency + crash-resume — **có demo**
- [ ] Loop breaker + hallucination containment — **có demo**
- [ ] Decoupling qua Pub/Sub / Cloud Tasks
- [ ] Tool scope tách biệt, least-privilege
- [ ] Secret Manager, không có key trong repo (`git log -p | grep -i "api_key"` để tự kiểm)
- [ ] Memory phân tầng + provenance
- [ ] OpenTelemetry traces
- [ ] **6 ADR** trong `docs/adr/`

**Demo & Production Readiness (30%)**
- [ ] Một take **liền mạch, không cắt** ≥60s cho phần agent chạy
- [ ] Cloud Run dashboard + Cloud Logging live + URL `.run.app` xuất hiện trên màn hình
- [ ] Thay đổi thật nhìn thấy được: DB row / UI update / file được tạo
- [ ] Spin-up instructions đã **test trên máy sạch**
- [ ] Diagram chuyên nghiệp
- [ ] README có bảng "How this maps to judging criteria"

### Stage Three (bonus, tối đa +1.0)

- [ ] **Blog/podcast/video** public về cách build *(+0.2)* — **có câu**: *"This content was created for the purposes of entering the All Things Agentic Hackathon."*
- [ ] **Social post** với **`#AllThingsAgenticHackathon`** *(+0.2)*
- [ ] **Gemma** tích hợp có chức năng thật *(+0.2)*
- [ ] **Veo** tích hợp có chức năng thật *(+0.2)*
- [ ] **Lyria** tích hợp có chức năng thật *(+0.2)*

---

## PHẦN 2 — Script video 4 phút (target 3:40)

> Nguyên tắc: **0 giây slide thừa.** Judge xem hàng trăm video. 15 giây đầu quyết định họ có tập trung không.

| Thời gian | Nội dung | Trên màn hình |
|---|---|---|
| **0:00–0:20** *(Hook — friction)* | "Every week, [Unlikely Hero] spends [X hours] doing [friction]. Miss one deadline and [hậu quả thật]. This is my [mẹ / chú tôi / chính tôi]." | Cảnh thật: chồng giấy tờ, ảnh chụp màn hình lịch rối, voice note. **Không phải slide chữ.** |
| **0:20–0:40** *(Value prop)* | "[Tên] is a fleet of agents that runs in the background for weeks on Google Cloud. It decides, it acts, it never does the same thing twice — and every action is auditable." | Timeline UI đang chạy, một hành động vừa hoàn tất |
| **0:40–1:10** *(Architecture)* | Giải thích diagram trong 30 giây: ingest → trust boundary → orchestrator → workers → action gate → state/memory → observability. Gọi tên: **Gemini 3.5, ADK, Cloud Run, Pub/Sub, Firestore, Memory Bank, Model Armor**. | Architecture diagram, highlight từng khối khi nhắc tới |
| **1:10–2:40** *(LIVE DEMO — một take, không cắt)* ⭐ | Đây là 90 giây quan trọng nhất. Nói ít, để hệ thống nói. | Xem kịch bản dưới |
| **2:40–3:00** *(Proof on Google Cloud)* | "This is running on Google Cloud right now." | **Cloud Run dashboard** (revision, traffic) → **Cloud Logging** stream live → URL `.run.app` trên trình duyệt → **Cloud Trace** hiện span của run vừa rồi |
| **3:00–3:25** *(The Twist)* | Cảnh khiến judge nhớ bạn. Chọn 1: guardrail chặn prompt injection **hoặc** anti-gaming judge chặn một bản self-improvement gian lận. | Audit log hiện lý do chặn |
| **3:25–3:40** *(Close)* | "Reproducible: one command to deploy. Repo, diagram, and ADRs are public. [X hours] a week, gone." | README + `deploy.sh` chạy + link repo |

### Kịch bản 90 giây live demo (một take)

```
1. Thả một input BẨN vào hệ thống — ảnh chụp nghiêng / PDF scan / voice note.
   → Cho thấy nó bẩn thật. Đây là điểm "messy unstructured data" của rubric.

2. Cắt sang terminal: log stream chạy.
   → orchestrator nhận event → tra Registry → delegate cho worker A
   → worker A trả structured output → watchdog verify

3. Cho thấy Firestore cập nhật REALTIME (mở console bên cạnh).

4. Agent chạm tới một hành động rủi ro → DỪNG → gửi approval card.
   → Bạn bấm duyệt trên UI. Nó tiếp tục.

5. ⚡ CHAOS: kill -9 worker NGAY GIỮA một bước.
   → Chờ. Nó restart. Resume từ checkpoint.
   → Zoom vào DB: CHỈ CÓ MỘT bản ghi. Không double.
   → Nói: "This is the idempotency trap. We survive it."

6. Click vào hành động vừa xảy ra → mở Reasoning Trace
   → truy ngược toàn bộ chuỗi: agent nào, nghĩ gì, tốn bao nhiêu, policy quyết ra sao.
```

> 🎯 Bước 5 là **cảnh ăn điểm Architecture cao nhất trong toàn bộ video**. Đừng cắt nó.

### Lưu ý kỹ thuật khi quay

- Font terminal to (18–20pt), theme sáng hoặc tương phản cao — video bị nén trên YouTube
- 1080p tối thiểu; zoom vào vùng quan trọng thay vì để judge tự tìm
- Micro rõ; nói chậm hơn bình thường 20% (judge có thể không phải người bản ngữ)
- **Bật caption tiếng Anh** trên YouTube (auto-caption rồi sửa tay)
- Không dùng nhạc có bản quyền
- Che/blur mọi thứ trông như dữ liệu thật; hiện chữ **"All data shown is synthetic"** trên màn hình

---

## PHẦN 3 — README.md template (tiếng Anh)

```markdown
# <Project Name>
> <One line: what friction it kills, for whom.>

**Category:** The Fortified Enterprise Fleet
**Live demo:** https://<...>.run.app · **Video (4 min):** https://youtu.be/<...>
**All data shown is synthetic.**

![Architecture](docs/architecture.png)

## 1. The Friction (why this exists)
<2–3 câu, cụ thể, cá nhân, có số liệu. Ai. Mất bao nhiêu giờ. Sai thì sao.>

## 2. What it does
<5–7 bullet. Mỗi bullet là một HÀNH ĐỘNG agent thực hiện, không phải feature trừu tượng.>

## 3. Proof it runs on Google Cloud
| Evidence | Link / Screenshot |
|---|---|
| Cloud Run service | ![](docs/proof/cloudrun.png) |
| Cloud Logging (live run) | ![](docs/proof/logs.png) |
| Cloud Trace (reasoning chain) | ![](docs/proof/trace.png) |
| Vertex AI / Gemini calls | ![](docs/proof/vertex.png) |

## 4. Mandatory Stack Compliance
| Requirement | How we meet it | Where |
|---|---|---|
| Gemini 3.5+ via Gemini API / Vertex AI | <model id> for planning & multimodal extraction | `agents/orchestrator/model.py:23` |
| Google Agent Framework | Google ADK — orchestrator + workers | `agents/orchestrator/agent.py:1` |
| Google Cloud infra | Cloud Run, Pub/Sub, Firestore, Cloud Storage, Secret Manager, Cloud Trace | `infra/` |
| Additional Google AI models (bonus) | Gemma (PII redaction), Veo (weekly digest), Lyria (audio digest) | `platform/guardrails/`, `web/digest/` |

## 5. Architecture
<Diagram + 1 đoạn cho mỗi lớp. Link tới docs/adr/ cho quyết định thiết kế.>

### Reliability mechanisms
- **Idempotency:** `hash(run_id, step_id, canonical_payload)` — `platform/actions/idempotency.py`
- **Crash-resume:** checkpoint-before-execute — thử: `scripts/demo_chaos.sh`
- **Loop breaker & hallucination containment:** `agents/watchdog/`
- **Action gate & human approval:** `platform/actions/gate.py`
- **Compensating actions (saga):** `platform/actions/saga.py`

## 6. Spin-up Instructions
### Prerequisites
### Deploy to Google Cloud (one command)
    ./deploy.sh
### Run locally
### Seed synthetic data
    python scripts/seed_synthetic_data.py
### Reproduce the demo
    ./scripts/demo_chaos.sh
<Từng bước, copy-paste chạy được. Ghi rõ biến môi trường cần thiết.>

## 7. How this maps to the judging criteria
| Criterion | Where to look |
|---|---|
| Innovation & Operational Utility (40%) | §1 friction · §2 actions · video 0:00–0:40 & 3:00–3:25 |
| Architectural Discipline (30%) | §5 · `docs/adr/` · video 0:40–1:10 & 2:00–2:40 |
| Demo & Production Readiness (30%) | §3 proof · §6 spin-up · video 1:10–3:00 |

## 8. Security, Privacy & Compliance
<PII redaction, Model Armor, least-privilege tool scopes, data residency, synthetic data, disclaimer.>
Xem `docs/compliance.md`.

## 9. Findings and Learnings
<Thật lòng. 4–6 bullet. Cái gì hỏng, cái gì bất ngờ, cái gì bạn làm khác nếu làm lại.
Đây là mục rules yêu cầu và nhiều team bỏ trống — viết tử tế sẽ nổi bật.>

## 10. Pre-existing Work Disclosure
<Liệt kê mọi thứ không được viết trong Submission Period. Nếu không có: "All code in this
repository was written during the submission period (Aug 3–31, 2026). No pre-existing
work was incorporated." Kèm câu về AI coding assistants nếu có dùng.>

## 11. What we'd build next
```

---

## PHẦN 4 — Bonus content

### Blog (dev.to hoặc Medium) — outline
1. **Hook**: friction thật, kể như một câu chuyện
2. Vì sao chatbot không giải quyết được — cần agent chạy nền
3. Kiến trúc: diagram + 3 quyết định khó nhất (lấy từ ADR)
4. **"The idempotency trap"** — kể chuyện lần đầu bạn bị double-execute (kỹ sư rất thích phần này)
5. Cách chặn prompt injection từ tài liệu người dùng upload
6. Self-evolution + vì sao cần anti-gaming judge (Goodhart's law)
7. Chi phí thật trên GCP (con số cụ thể — rất được đọc)
8. Link repo + video

**Cuối bài, bắt buộc:**
> *"I created this content for the purposes of entering the All Things Agentic Hackathon."*

### Social post (LinkedIn / X)
```
I spent 3 weeks building an agent fleet for [Unlikely Hero] —
people who lose [X hours] a week to [friction].

It runs for weeks in the background on Google Cloud.
It survives crashes without doing anything twice.
It blocked a prompt injection hidden inside a scanned PDF — on camera.

Built with Gemini 3.5, Google ADK, Cloud Run, Pub/Sub, Firestore and Memory Bank.

Demo (4 min): <link>
Repo + architecture + ADRs: <link>

#AllThingsAgenticHackathon
```

> Đăng **cả LinkedIn và X**, đính kèm 30–60s clip cảnh crash-resume.
