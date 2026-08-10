# 04 — Chọn track & Chiến lược "xếp làn" giải thưởng

---

## 1. Toán học của giải thưởng

Mỗi project **chỉ nhận tối đa 1 giải**. Nhưng bạn được chấm cho **nhiều làn cùng lúc**:

```
                      ┌─ Grand Prize ($50k/$40k) ── điểm cao nhất TOÀN CUỘC
                      │
Bài của bạn ──────────┼─ Track Prize ($20k) ─────── điểm cao nhất TRONG TRACK
                      │
                      ├─ Individual/Hobbyist ($10k × 2) ── mọi cá nhân/team
                      │
                      ├─ Best Architectural Design ($5k × 2)
                      │
                      ├─ Best Multimodal UX ($5k × 2)
                      │
                      └─ Honorable Mention ($2k × 5)
```

**13 vị trí có giải / ~1080 participants** (số team ít hơn nhiều so với số người). Xác suất không tệ như bạn nghĩ.

### Suy luận quan trọng

- **Individual/Hobbyist có 2 suất và bạn tự động nằm trong đó** nếu không nộp thay mặt công ty đã incorporated. Đây là làn có odds tốt nhất cho cá nhân/team nhỏ.
- **Startup Excellence ($20k)** yêu cầu tổ chức **đã incorporated** + email doanh nghiệp. Nếu bạn có công ty → làn này ít đối thủ hơn nhiều so với track prize. **Nếu có pháp nhân, cân nhắc nộp qua đó.**
- **Best Architectural Design (2 suất)** và **Best Multimodal UX (2 suất)** là "giải an ủi hạng sang". Thiết kế bài để **đủ tư cách cho cả hai** gần như miễn phí: kiến trúc tốt bạn phải làm rồi (30% điểm), còn multimodal chỉ cần ngay từ đầu chọn input/output đa phương thức.

> 🎯 **Chiến lược:** build 1 bài, nhưng cố ý **đứng chân trong 4 làn**: Track Prize + Individual/Hobbyist + Best Architecture + Best Multimodal UX. Không tốn thêm scope đáng kể nếu quyết định từ ngày 1.

---

## 2. So sánh 3 track

| | Taskmaster | Collaborative Partner | Fortified Enterprise Fleet |
|---|---|---|---|
| **Độ khó build** | Thấp–Trung | Trung | **Cao** |
| **Dự đoán số bài nộp** | **Rất nhiều** (dễ nhất, ví dụ rõ nhất) | Nhiều | **Ít nhất** (rào cản kỹ thuật cao) |
| **Odds thắng track** | Thấp (đông) | Trung | **Cao nhất** |
| **Đường tới Grand Prize** | Cần twist rất mạnh | Trung bình | **Tốt** — rubric Grand Prize thưởng độ phức tạp |
| **Rủi ro** | Bị chìm giữa 300 bài "agent tự động hóa email" | Dễ tụt về "chatbot có memory" = fail đề bài | Ôm đồm, làm không xong, demo hời hợt |
| **Hợp với "Best Architecture"** | Trung | Thấp | **Cao** |
| **Hợp với "Best Multimodal UX"** | Trung | **Cao** | Trung |

### Khuyến nghị

> **Fortified Enterprise Fleet** — với điều kiện bạn build cho một **"Unlikely Hero"**, không phải cho một enterprise chung chung.

**Lý do:**
1. **Ít cạnh tranh nhất.** Track này đòi Agent Registry + Runtime + Memory Bank + Identity + Gateway + Model Armor + Observability. Phần lớn người tham gia sẽ né. Ít bài nộp = odds $20k cao hơn hẳn.
2. **Rubric của track này thưởng đúng thứ Grand Prize cần**: multi-agent xứng đáng, delegation thông minh, routing chịu lỗi, state dài hạn, observability.
3. **Nó tự động khiến bạn đủ tư cách "Best Architectural Design"** — thêm 2 suất $5k.
4. **Sub-criteria của nó nói thẳng "Unlikely Hero"** — nghĩa là BTC *muốn* thấy hạ tầng cấp doanh nghiệp phục vụ người ngoài doanh nghiệp. Đây là khoảng trống định vị hoàn hảo: **kỹ thuật enterprise + câu chuyện con người**.
5. Track "mở cho tất cả mọi người" — nói rõ trong đề bài, không cần bạn là startup.

**Rủi ro và cách chặn:** track này dễ khiến bạn build 7 component nửa vời. Chống bằng cách: chọn **4 component làm thật sâu** (Runtime + Memory Bank + Model Armor + Observability), 3 cái còn lại (Registry, Identity, Gateway) làm **đủ để demo được và có thật**, không giả lập.

### Khi nào KHÔNG chọn Fortified Fleet

- Bạn solo và chỉ có <10 ngày thực làm → chọn **Taskmaster** với một friction cá nhân rất sắc + twist mạnh (crash-resume + idempotency). Dễ hoàn thiện, dễ demo đẹp.
- Bạn mạnh về frontend/UX và muốn nhắm **Best Multimodal UX** → **Collaborative Partner** với input đa phương thức (voice + ảnh + tài liệu) và memory tiến hóa.

---

## 3. Nếu chọn Fortified Enterprise Fleet — bắt buộc phải chứng minh 3 điều

Đề bài viết rõ, đây là checklist demo:

| Yêu cầu | Bạn phải cho judge thấy gì |
|---|---|
| "agents are **cataloged** for cross-department use" | Một **Agent Registry** thật: list agent, version, owner, capability schema, ai được gọi. Demo: một agent **khám phá** ra agent khác qua registry rồi gọi nó. |
| "safely maintain context across **weeks** of asynchronous operations" | Memory Bank + timeline. Demo: tua nhanh một case chạy 3 tuần, agent nhớ quyết định từ tuần 1 và **viện dẫn nó** ở tuần 3, có provenance. |
| "interact with **production data** without violating compliance, data sovereignty, or security policies" | PII redaction / tokenization trước khi vào model; policy engine chặn một hành động vi phạm **ngay trên camera**; audit log ghi lại việc chặn đó; data residency được khai báo. |

> 💡 **Cảnh quay đắt giá nhất trong video của bạn:** một prompt injection (hoặc một tool poisoning) đi vào hệ thống qua email/tài liệu, **Model Armor / guardrail chặn nó**, agent ghi audit log, và tiếp tục làm việc bình thường. Rất ít bài sẽ demo được cảnh này. Nó chứng minh cùng lúc: security, observability, và "production-minded".

---

## 4. Bốn "làn" — checklist đủ tư cách

### Làn A — Track Prize ($20k)
- [ ] Chọn đúng category trên form
- [ ] Đáp ứng **đủ cả 3 yêu cầu đặc thù** của Fortified Fleet ở bảng trên
- [ ] Sub-criteria: multi-agent xứng đáng, delegation thông minh, Unlikely Hero

### Làn B — Individual/Hobbyist ($10k × 2)
- [ ] **Không** nộp thay mặt tổ chức incorporated (trừ khi bạn nhắm Startup Excellence thay thế)
- [ ] Story cá nhân mạnh trong video — làn này thưởng "best team/solo build"

### Làn C — Best Architectural Design ($5k × 2)
- [ ] Architecture diagram cấp production (không phải 3 hộp và 2 mũi tên)
- [ ] Có **ADR** (Architecture Decision Records) trong repo — 5–8 quyết định, mỗi cái nêu lựa chọn thay thế và lý do bác bỏ. Cực kỳ hiếm ở hackathon, cực kỳ ăn điểm.
- [ ] Demo được failure mode: kill worker → resume; worker loop → bị cắt; hallucination → bị verifier chặn
- [ ] OpenTelemetry trace hiển thị được

### Làn D — Best Multimodal UX ($5k × 2)
- [ ] Input đa phương thức có ý nghĩa: **ảnh chụp giấy tờ / voice note / PDF scan / video** — không phải chỉ text
- [ ] Output đa phương thức: trace view trực quan, timeline, và (nếu dùng Veo) video digest
- [ ] Gemini xử lý multimodal **native** (đây chính là lợi thế của Gemini — hãy khoe nó)
- [ ] UX phải cho thấy *agent đang nghĩ gì* — "glass box", không phải black box

---

## 5. Định vị một câu (viết ra và dán lên tường)

> **"____ (Unlikely Hero) mất ____ giờ mỗi tuần cho ____ (friction cụ thể). ____ (tên sản phẩm) là một đội agent chạy nền nhiều tuần trên Google Cloud, tự quyết định và hành động, có audit đầy đủ và không bao giờ làm hai lần cùng một việc."**

Nếu bạn không điền được câu này bằng sự thật của chính mình → chưa đủ điều kiện để bắt đầu code.
