# 03 — Giải mã Rubric: cách đạt điểm tối đa

> Đây là doc quan trọng nhất. **Đừng build theo trực giác — build theo rubric.**

---

## 1. Cấu trúc chấm

```
Stage One   → PASS/FAIL   (đủ hồ sơ, đúng track, đúng stack bắt buộc)
Stage Two   → 1..5 điểm   (3 tiêu chí có trọng số, trung bình hóa)
Stage Three → +0..1.0     (bonus contributions)
──────────────────────────────────────────
Final       → thang 1..6
```

Tie-break: so điểm **theo thứ tự tiêu chí** (Innovation trước → Architecture → Demo), vẫn hòa thì judges bỏ phiếu.

> 🔑 **Hệ quả chiến thuật:** Innovation & Operational Utility vừa nặng nhất (40%) vừa là tiêu chí phá hòa đầu tiên. Nếu phải hy sinh, **đừng bao giờ hy sinh Innovation**.

Judging có thể dùng **expert panel, peer review, hoặc AI-driven analysis** — hoặc kết hợp.
> 🔑 **Hệ quả:** README và text description của bạn có thể bị **một model đọc và chấm**. Viết sao cho vừa thuyết phục người vừa dễ parse: heading rõ, bảng, bullet, mapping thẳng tới tiêu chí.

---

## 2. Tiêu chí 1 — Innovation & Operational Utility (40%)

**Câu hỏi gốc:** *Does the system eliminate real-world friction? Is the "Twist" present? We are looking for high-value, autonomous execution over simple chat queries.*

### Sub-criteria bị lộ trong Official Rules

Rules mô tả rubric bằng tên category **cũ**. Đây là vàng — nó cho biết judge thực sự soi gì:

| Tên trong rubric | Map sang track | Judge hỏi gì |
|---|---|---|
| **The Continuous Action Engine** | ≈ **Taskmaster** | Agent có **chặn và hoàn tất** một workflow nền nhiều bước **không cần can thiệp của con người** không? Team có dùng đúng mandate **"Bring Your Own Friction" (BYOF)** để giải một vấn đề **cá nhân, độc nhất** không? |
| **The Evolving Knowledge Engine** | ≈ **Collaborative Partner** | Agent có **tổng hợp / biến đổi (mutate)** dữ liệu, hay chỉ **đọc** nó? Team có nạp **dữ liệu phi cấu trúc lạ, bẩn, phức tạp** không? |
| **The Multi-Agent Nexus** | ≈ **Fortified Enterprise Fleet** | Task có **đủ phức tạp để xứng đáng** dùng multi-agent không? Hệ thống có **ủy thác thông minh** cho sub-agent chuyên biệt không? Có build cho một **"Unlikely Hero" ngoài các vai trò doanh nghiệp tiêu chuẩn** không? |

### 3 khái niệm phải hiểu và phải "diễn" được trong bài

**① "The Twist"** — điểm bẻ ngoặt khiến judge phải ngồi thẳng lưng. Không phải feature; là một **cơ chế** mà 95% bài còn lại không có. Ví dụ twist mạnh:
- Agent **tự viết lại instruction của chính nó** rồi phải vượt qua eval gate mới được promote (và bạn *demo cả lúc nó gian lận metric và bị bắt*).
- Agent **từ chối hành động** và leo thang lên người, kèm lý do có trace — chứng minh nó biết giới hạn.
- Agent chạy **nhiều tuần**, bị kill giữa chừng, **resume đúng chỗ, không double-execute** (idempotency).
- Agent xử lý dữ liệu **nó chưa từng thấy schema**, tự suy ra schema, rồi tự viết lại pipeline.

**② "BYOF — Bring Your Own Friction"** — nỗi đau phải là của **chính bạn**, cụ thể, kể được thành câu chuyện. Judge chán "AI assistant for enterprise productivity". Judge nhớ "tôi mất 6 tiếng mỗi tuần làm X, đây là thứ đã giết nó".
> ✍️ Viết được câu này chưa? *"Mỗi ____, tôi phải ____ mất ____ giờ, vì ____. Agent này làm nó trong ____ giây, và tôi có log chứng minh."*

**③ "Unlikely Hero"** — người dùng **ngoài** các vai trò doanh nghiệp tiêu chuẩn (không phải PM/dev/sales/marketer). Ví dụ: điều dưỡng chăm sóc tại nhà, chủ tiệm thuốc, giáo viên chủ nhiệm, trọng tài giải trẻ, thợ cả công trường, cán bộ hợp tác xã, người chăm sóc người khuyết tật, nhà báo độc lập, quản lý ban nhạc.
> Đây là **con đường khác biệt hóa rẻ nhất và mạnh nhất**. 1080 người tham gia; phần lớn sẽ làm agent cho dev/PM/sales. Chọn Unlikely Hero là bạn tự tách khỏi đám đông.

### Chấm mình (1–5)

| Điểm | Trông như thế nào |
|---|---|
| 1 | Chatbot có tool. Người vẫn phải dẫn từng bước. |
| 2 | Workflow tự động nhưng linear, hardcode, chạy 1 lần. |
| 3 | Multi-step autonomous, có tool thật, side-effect thật, nhưng vấn đề generic. |
| 4 | Autonomous + friction cụ thể có thật + có ít nhất 1 cơ chế "twist" thật. |
| **5** | Trên đó + **Unlikely Hero** + agent chạy nền **nhiều ngày/tuần** + demo cho thấy nó **quyết định** chứ không chỉ **thực thi** + có bằng chứng định lượng (X giờ → Y giây). |

---

## 3. Tiêu chí 2 — Architectural Discipline & Tech Stack (30%)

**Câu hỏi gốc:** *We are evaluating your engineering decisions, not just your ability to call an API. How well did your team decouple systems, manage state, and design robust, failure-tolerant agentic systems?*

### Sub-criteria bị lộ

| Track | Judge soi |
|---|---|
| Continuous Action (Taskmaster) | Kiến trúc **robust**. Có **modular hóa sạch, dễ maintain** không? Hệ thống **quản lý state** ra sao? Tool có được **isolate và scope đúng vì lý do bảo mật** không? |
| Evolving Knowledge (Collaborative) | **Data architecture**: schema design thông minh, chiến lược **vector embedding** hiệu quả. Quản lý **context window khổng lồ** hiệu quả tới đâu? |
| Multi-Agent Nexus (Fortified) | **Separation of concerns giữa các agent phải rõ và được cưỡng chế**. Routing giữa agent có **chịu lỗi** không — hệ thống **recover thế nào nếu một worker agent bị loop hoặc trả về hallucination**? |

### Checklist kiến trúc để ăn 5 điểm

Đây là danh sách "nếu có thì judge tick" — không cần đủ hết, nhưng càng nhiều càng cao:

**State & Durability**
- [ ] State machine tường minh (không phải "agent tự nhớ trong prompt"). Persist ở Firestore/Cloud SQL.
- [ ] **Idempotency keys** cho mọi side-effect ngoài (chính webinar 13/08 gọi đây là "the idempotency trap" — agent resume rồi đặt 2 cái laptop).
- [ ] **Resume-after-crash**: kill process giữa chừng, khởi động lại, chạy tiếp đúng chỗ. **Demo cái này trong video.**
- [ ] **Checkpoint / event-sourced log** thay vì mutable blob.

**Decoupling**
- [ ] Pub/Sub hoặc Cloud Tasks giữa các stage — không phải một hàm `main()` gọi tuần tự.
- [ ] Worker chạy tách khỏi API tier (Cloud Run job / service riêng).
- [ ] Tool layer tách khỏi agent layer; tool là interface có schema, test được độc lập.

**Failure tolerance**
- [ ] Retry có backoff + **dead-letter queue**.
- [ ] **Loop breaker**: giới hạn số bước / ngân sách token / phát hiện lặp trạng thái.
- [ ] **Hallucination containment**: verifier agent hoặc schema validation (structured output) chặn output rác trước khi nó gây side-effect.
- [ ] **Circuit breaker** khi tool ngoài chết.
- [ ] **Compensating action** khi bước sau fail (saga pattern).

**Security**
- [ ] Secret Manager — **không** hardcode key. (Judge sẽ mở repo của bạn.)
- [ ] Tool được scope theo quyền tối thiểu; agent A không chạm được tool của agent B.
- [ ] Service account riêng cho từng service, Workload Identity.
- [ ] Guardrail chống prompt injection ở mọi điểm nhập dữ liệu **không tin cậy** (email, web, file người dùng upload).
- [ ] Xử lý/redact PII trước khi vào model.

**Memory & Data**
- [ ] Phân tầng memory rõ ràng: session state → working memory → long-term (vector) → semantic profile.
- [ ] Chiến lược nén/summarize memory dài hạn (đừng nhét cả history vào context).
- [ ] Vector search **serverless** (đúng cả cost tip của BTC).
- [ ] Có **provenance** — mỗi mẩu nhớ biết nó đến từ đâu, khi nào, độ tin cậy bao nhiêu.

**Observability**
- [ ] OpenTelemetry traces cho toàn bộ chuỗi reasoning.
- [ ] Structured logging, correlation ID xuyên suốt agent.
- [ ] Một **UI/trace view** cho thấy agent *nghĩ gì* ở mỗi bước → cực ăn điểm khi demo.

> 🔑 Có **2 giải "Best Architectural Design" x $5,000**. Tiêu chí này vừa là 30% điểm chính vừa là một làn giải riêng. Đầu tư ở đây có ROI kép.

---

## 4. Tiêu chí 3 — Demo & Production Readiness (30%)

**Câu hỏi gốc:** *The clarity of the technical documentation and the undeniable proof of execution in the video pitch.*

Ba thứ được nêu đích danh:

1. **The Proof of Action** — video phải cho thấy **unedited, live execution** của agent đang làm việc, thể hiện qua **terminal logs, database updates, hoặc UI changes**.
2. **The Documentation** — public GitHub repo phải có **architecture diagram sạch** + **setup instructions tái lập được**.
3. **Proof of Google Cloud deployment** hiện diện **trong video**.

### Vì sao đây là tiêu chí dễ ăn nhất nhưng nhiều người mất điểm

30% điểm nằm ở thứ **không phải code**. Rất nhiều team dành 100% thời gian cho code và quay video lúc 3 giờ sáng ngày cuối. Bạn thì **chặn cứng 4 ngày cuối cho video + docs**.

### Chấm mình (1–5)

| Điểm | Trông như thế nào |
|---|---|
| 1 | Video screencast lộn xộn, không có repo/diagram tử tế. |
| 2 | Có demo nhưng toàn slide, không thấy hệ thống chạy. |
| 3 | Demo chạy được, README ổn, diagram sơ sài. |
| 4 | Video rõ vấn đề → kiến trúc → demo live, có cảnh Cloud Console, README reproduce được. |
| **5** | Trên đó + **một take liền mạch không cắt** cho thấy trigger → log stream → DB thay đổi → UI cập nhật; diagram chuyên nghiệp; README có one-command deploy; có bảng map thẳng vào từng tiêu chí chấm. |

---

## 5. Bảng "Điểm mục tiêu"

| Tiêu chí | Trọng số | Mục tiêu | Đòn bẩy chính |
|---|---|---|---|
| Innovation & Operational Utility | 40% | **5** | Unlikely Hero + BYOF thật + 1 twist cơ chế + chạy nền dài hạn |
| Architectural Discipline | 30% | **5** | Idempotency + crash-resume + loop breaker + hallucination containment + OTel trace |
| Demo & Production Readiness | 30% | **5** | 1 take live không cắt + Cloud Console on-screen + README reproduce + diagram đẹp |
| Bonus | — | **+1.0** | Blog (0.2) + social (0.2) + 3 model phụ Gemma/Veo/Lyria (0.6) |
| | | **= 6.0 / 6.0** | |

**Bonus +1.0 là con đường rẻ nhất trên đời.** Nó đáng ~17% điểm cuối cùng và tốn khoảng 1 ngày công. Rất nhiều team sẽ bỏ qua.

Cách lấy trọn 0.6 model bonus mà **không** làm loãng sản phẩm — tích hợp phải "successful", nghĩa là có chức năng thật:
- **Gemma** (self-host trên Cloud Run GPU hoặc dùng qua API): dùng làm **classifier/router rẻ** hoặc **local PII redactor** trước khi gửi lên Gemini → vừa là bonus vừa là điểm kiến trúc (cost + privacy tiering).
- **Veo**: agent tự sinh **video tóm tắt tình huống** cho người dùng cuối (ví dụ: video 15s recap những gì agent đã làm tuần này). Rất hợp giải **Best Multimodal UX**.
- **Lyria**: sinh audio/nhạc nền cho digest, hoặc audio cue phân biệt mức độ khẩn cấp trong notification. Cần khéo để không thành gimmick — gắn nó vào accessibility (ví dụ người dùng khiếm thị / đang lái xe).

> ⚠️ Đừng nhét 3 model chỉ để lấy điểm nếu nó phá mạch sản phẩm. Nhưng nếu gắn được vào đúng chỗ, mỗi cái +0.2 — rẻ hơn bất kỳ feature nào khác.

---

## 6. Nguyên tắc "viết cho judge"

Judge có thể không chạy code của bạn. Vậy hãy:

1. **README mở đầu bằng 3 dòng**: friction là gì, agent làm gì, bằng chứng nó chạy trên GCP (kèm ảnh chụp Cloud Run).
2. Có section **"How this maps to the judging criteria"** trong README — bảng 3 dòng, mỗi dòng trỏ tới file/dòng code cụ thể. Judge lười; đừng bắt họ đi tìm.
3. Có section **"Mandatory stack compliance"** — Gemini 3.5+ ở đâu, ADK ở đâu, GCP service nào.
4. Có section **"What we'd do with more time"** + **"Findings and learnings"** (rules yêu cầu learnings trong text description — nhiều người quên).
5. Mọi claim đều kèm bằng chứng: screenshot, log, trace ID, link.
