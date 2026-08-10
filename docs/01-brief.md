# 01 — Brief chính thức (đã cấu trúc lại)

> Nguồn: trang Devpost `allthingsagentichackathon.devpost.com` + Official Rules.
> Doc này là **bản ghi trung thực** yêu cầu. Phần phân tích/chiến lược nằm ở doc 03–06.

---

## 1. Thông tin cuộc thi

| Mục | Giá trị |
|---|---|
| Tên | **All Things Agentic Hackathon** |
| Sponsor | Google LLC |
| Administrator | Devpost, Inc. |
| Hình thức | Online, Public, toàn cầu |
| Tổng giải | **$180,000** tiền mặt + Google Cloud credits |
| Số người tham gia (tại thời điểm ghi nhận) | ~1,080 |
| Chủ đề | Enterprise / Machine Learning + AI / Productivity |

## 2. Mốc thời gian (BẮT BUỘC nhớ)

| Mốc | Thời điểm |
|---|---|
| Bắt đầu | 03/08/2026, 09:00 PT |
| **Hạn nộp bài** | **31/08/2026, 17:00 PT** = **01/09/2026, 07:00 GMT+7** |
| **Hạn xin $150 credits** | **28/08/2026, 12:00 PT** (hoặc hết suất — xin NGAY) |
| Judging | 01/09/2026 → 01/10/2026 |
| Công bố winner | ~08/10/2026, 10:00 PT |

**Webinar (nên xem — đây là tín hiệu về thứ ban giám khảo coi trọng):**

| Ngày | Chủ đề | Vì sao quan trọng |
|---|---|---|
| 11/08 | Architecting Multi-Agent Teams: 3 orchestration patterns của ADK | Map thẳng vào tiêu chí Architecture 30% |
| 13/08 | Build a Long-Running Agent: crash recovery, human approval, **idempotency trap** | Đây là lõi của "next-gen agent" mà đề bài muốn |
| 20/08 | Build a **Self-Evolving Agent**: tự viết lại instruction, và bắt nó *gaming the metric* | Gợi ý mạnh về "Innovation twist" |
| 27/08 | Architecting Agent Memory: session state, vector search, managed cloud memory | Map vào Memory Bank / Collaborative Partner |

## 3. Đề bài

> Build **and deploy** a next-generation, autonomous AI Agent leveraging **Gemini 3.5 (hoặc mới hơn)** that operates **beyond standard chat loops**. The system can run **asynchronously in the background**, handle the heavy lifting of **complex workflows**, or dynamically **manipulate data pipelines and representations**.

Ba từ khóa cốt lõi: **asynchronous / background**, **multi-step autonomous action**, **beyond chat**.

## 4. Tech stack BẮT BUỘC (cả 3 track)

1. **Gemini 3.5 hoặc mới hơn**, truy cập qua **Gemini API** hoặc **Vertex AI**.
2. **Ít nhất 1 Google Agent Framework**: Google **ADK** / **GenAI SDK** / **Antigravity SDK** / **GenKit**.
3. **Ít nhất 1 Google Cloud infra service**: Cloud Run, Cloud SQL, Firestore, GKE, Pub/Sub, …

> ⚠️ Thiếu 1 trong 3 → trượt Stage One (pass/fail). Không thương lượng.

**Note về deploy & chi phí:** App **không cần live tại thời điểm chấm**. Chỉ cần **bằng chứng rõ ràng** đã build & deploy trên Google Cloud (video demo + repo). → Demo xong thì tắt service.

## 5. Ba track (chọn đúng 1)

### 5.1. The Taskmaster
- **Focus:** event-driven workflow + autonomous routing. Hệ thống như một "smart coordinator": phát hiện thay đổi → quyết định việc kế tiếp → gọi nhiều app khác nhau → hoàn thành từ đầu tới cuối, **không cần người dẫn từng bước**.
- **Mandate ngầm:** *"Bring Your Own Friction" (BYOF)* — giải quyết một nỗi đau **có thật, cụ thể, của chính bạn**.
- **Ví dụ đề bài đưa ra:**
  - "Automated Product Manager": đọc meeting transcript → trích action items → tạo Jira tasks → post summary lên Slack.
  - "Freelance Pipeline": theo dõi inbox → check calendar → soạn proposal từ portfolio cũ → lưu chờ duyệt.

### 5.2. The Collaborative Partner
- **Focus:** stateful multi-turn dialogue + real-time RAG + **persistent memory**. Agent phải **hỏi lại để làm rõ**, dẫn dắt từng bước, và có **cơ chế bắt feedback rõ ràng** để thích nghi với cách nghĩ riêng của user.
- **Ví dụ:**
  - Trợ lý đọc hiểu văn bản pháp lý dày: quiz người dùng, học xem họ yếu khái niệm nào, điều chỉnh cách giải thích lần sau.
  - Trợ lý UI/UX cho người không biết design: ý tưởng mơ hồ → wireframe, học brand preference từ các lần bạn sửa.

### 5.3. The Fortified Enterprise Fleet
- **Focus:** corporate agent discovery, multi-agent orchestration ở quy mô, long-term state persistence, runtime observability, security posture enforcement.
- Phải chứng minh: tổ chức **khám phá** được agent của bạn, **audit** được reasoning, **tin** được cách xử lý dữ liệu, và **scale** an toàn.
- **Mở cho tất cả mọi người** — không giới hạn startup/enterprise.
- **Ví dụ:** "Enterprise Supply Chain Orchestrator" — procurement manager tìm agent trong internal Agent Registry để chạy chu kỳ onboarding vendor kéo dài **nhiều tuần**: monitor delivery webhooks, nhớ dữ liệu đàm phán qua Memory Bank, query ERP inventory riêng tư qua Agent Identity, phối hợp với logistics sub-agent qua Agent Gateway, lọc toàn bộ email ngoài qua Model Armor.

## 6. Gemini Enterprise Agent Platform (GEAP) — recommended cho track 3

| Nhóm | Component | Vai trò |
|---|---|---|
| Discovery & Lifecycle | **Agent Registry** | Repo trung tâm để publish / versioning / discover agent đã được duyệt |
| Core Execution & State | **Agent Runtime** | Chạy nền, long-running, async |
| Core Execution & State | **Memory Bank** | Context bền vững, xuyên session, dài hạn |
| Security & Governance | **Agent Identity** | Zero-trust access control |
| Security & Governance | **Agent Gateway** | Routing thống nhất + policy enforcement |
| Security & Governance | **Model Armor** | Guardrail inline: chặn prompt injection, tool poisoning, PII leak |
| Telemetry | **Agent Observability** | Audit log chuẩn OpenTelemetry + trace toàn bộ chuỗi reasoning |

> **GEAP ≠ GEAR.** GEAR (Gemini Enterprise Agent **Ready**) là chương trình học miễn phí (35 learning credits/tháng, lab sandbox, ADK training, skill badge) — vào Google Developer Program claim badge GEAR. GEAP là **platform** thực tế.

## 7. Danh mục nộp bài (What to Submit)

| # | Hạng mục | Bắt buộc | Ghi chú |
|---|---|---|---|
| 1 | **Category** — chọn 1 trong 3 track | ✅ | BTC có quyền chuyển track của bạn |
| 2 | **URL hosted project** | Khuyến khích mạnh | Web UI / Chrome Extension / mobile app. Nếu private → cung cấp login credentials |
| 3 | **Text description** | ✅ | Features & functionality, technologies used, other data sources, **findings & learnings** |
| 4 | **URL code repo** (GitHub/GitLab/Bitbucket) | ✅ | Nếu private → share cho `testing@devpost.com` **và** `cloudhackathons@google.com` |
| 5 | **Spin-up Instructions trong README.md** | ✅ | Hướng dẫn từng bước chạy local hoặc deploy lên cloud → chứng minh reproducible |
| 6 | **Architecture Diagram** | ✅ | Thể hiện rõ Gemini ↔ backend ↔ database ↔ frontend |
| 7 | **Demo video ~4 phút** | ✅ | YouTube/Vimeo, **public**, tiếng Anh hoặc có phụ đề Anh. >4 phút chỉ chấm 4 phút đầu |

**Demo video phải có:**
- Tổng quan ngắn về vấn đề đang giải
- Value proposition
- Demo app đang chạy thật
- **Bằng chứng backend chạy trên Google Cloud**: Google Cloud Console, Cloud Run dashboard, Vertex AI logs, URL `.run.app`, …

## 8. Bonus Points (Stage Three) — tối đa +1.0

| Bonus | Điểm | Điều kiện |
|---|---|---|
| Publish content (blog/podcast/video) về cách build project | **+0.2** | Public (không unlisted), trên medium.com / dev.to / YouTube… **Phải ghi rõ** nội dung được tạo để dự thi hackathon này |
| Social media post | **+0.2** | X / LinkedIn / Instagram / Facebook. Với X & LinkedIn: **bắt buộc hashtag `#AllThingsAgenticHackathon`** |
| Tích hợp thêm Google AI model (Gemma, Veo, Lyria…) | **+0.2 mỗi model, tối đa +0.6** | "Successfully integrate" |

→ Điểm cuối cùng thang **1–6** (5 điểm rubric + tối đa 1 điểm bonus).

## 9. Giải thưởng

| Giải | Số lượng | Tiền mặt | Credits | Điều kiện |
|---|---|---|---|---|
| **Grand Prize** | 1 | $50,000 *(rules ghi $40,000 — xem doc 02)* | $5,000 | Điểm cao nhất toàn cuộc |
| The Taskmaster | 1 | $20,000 | $2,000 | Cao nhất trong track |
| The Collaborative Partner | 1 | $20,000 | $2,000 | Cao nhất trong track |
| The Fortified Enterprise Fleet | 1 | $20,000 | $2,000 | Cao nhất trong track |
| Startup Excellence | 1 | $20,000 | $5,000 | Phải nộp thay mặt **tổ chức đã incorporated** + email doanh nghiệp |
| **Individual/Hobbyist (Best Team/Solo Build)** | **2** | $10,000 | $1,000 | Mọi cá nhân/team đủ điều kiện |
| **Best Architectural Design** | **2** | $5,000 | $1,000 | Top theo tiêu chí Architecture |
| **Best Multimodal UX** | **2** | $5,000 | $1,000 | Top theo tiêu chí Multimodal UX |
| Honorable Mentions | 5 | $2,000 | $500 | Runner-up |

> **Mỗi project chỉ nhận tối đa 1 giải.** (Xem doc 04 để biết cách chọn "làn" có odds tốt nhất.)

## 10. Tiêu chí chấm (tóm tắt — chi tiết ở doc 03)

| Tiêu chí | Trọng số |
|---|---|
| Innovation & Operational Utility | **40%** |
| Architectural Discipline & Tech Stack | **30%** |
| Demo & Production Readiness | **30%** |

Chấm 3 stage: **Stage One** pass/fail (đủ hồ sơ + đúng yêu cầu) → **Stage Two** chấm 1–5 theo rubric → **Stage Three** cộng bonus.

## 11. Pro tips giữ chi phí ~0 (BTC đưa ra)

- Dùng **Gemini Flash trước**; chỉ dùng Pro cho reasoning cuối cùng phức tạp.
- **Scale to zero**: min instances = 0 trên Cloud Run.
- Bắt đầu RAM/CPU tối thiểu + **đặt max instance cap** cứng.
- Dùng **serverless vector search**, tránh DB cluster always-on.
- Storage nhẹ: chỉ lưu state cần thiết, nén long-term memory, dọn artifact tạm.
- Bật **budget alerts** trong Cloud Console.
- **Bảo vệ endpoint** Cloud Run bằng API key / auth để traffic lạ không đốt credit.
- **Tắt hết sau khi quay demo**, xóa resource không dùng.

## 12. Tài nguyên

- Free trial: https://cloud.google.com/free
- Credit form ($150): https://forms.gle/riGhgDSHkHeMx8Ca6 — **hạn 28/08/2026 12:00 PT**
- ADK Python: https://github.com/google/adk-python
- Gemini API & AI Studio, Genkit, Antigravity SDK, Cloud Run, Firestore
- GEAP: Platform overview / Documentation home / Agent Runtime / Memory Bank / Announcement blog
- Devpost Discord + Discussion Forum + FAQs + Official Rules
