# 02 — Official Rules digest + Bẫy loại bài

Mục tiêu doc này: **không để bị loại vì lý do ngu ngốc.** Phần lớn bài dự thi chết ở Stage One, không phải vì code dở.

---

## 1. Eligibility — checklist cá nhân

- [ ] Trên tuổi thành niên tại nơi cư trú (Đài Loan: ≥20 tuổi) tại thời điểm nộp.
- [ ] **KHÔNG** cư trú tại: Ý, Quebec, Crimea, Cuba, Iran, Syria, Triều Tiên, Sudan, Belarus, Nga, và các quốc gia bị OFAC chỉ định.
  - ✅ **Việt Nam không nằm trong danh sách loại trừ.**
- [ ] Không thuộc diện bị US export controls / sanctions.
- [ ] Có Internet tính đến 03/08/2026.
- [ ] Không phải nhân viên/intern/contractor của Google, Devpost, hoặc các bên liên quan tổ chức cuộc thi (và người nhà cùng hộ khẩu của họ).
- [ ] Không làm cho cơ quan chính phủ (hoặc bất kỳ tổ chức nào tạo xung đột lợi ích thật/biểu kiến).
- [ ] Nếu nộp thay mặt công ty/employer: rules ràng buộc **cả bạn lẫn employer**; bạn phải đảm bảo employer biết và đồng ý, và hành động của bạn không vi phạm policy công ty.

## 2. Bẫy loại bài — đọc kỹ từng dòng

### 🔴 Bẫy #1 — "New Projects Only"
> Project phải được **tạo mới trong Submission Period** (03/08 → 31/08/2026).

- Được dùng framework, library, starter template, **AI coding assistant**.
- **Bắt buộc disclose** bất kỳ pre-existing code / work nào đưa vào project.
- ⚠️ **Hành động:** git repo phải có **commit đầu tiên ≥ 03/08/2026**. Đừng resurrect repo cũ. Nếu tái sử dụng module cũ của bạn → ghi rõ trong README mục "Pre-existing work disclosure".

### 🔴 Bẫy #2 — Thiếu 1 trong 3 thành phần bắt buộc
Gemini 3.5+ **AND** Google Agent Framework **AND** Google Cloud infra service. Thiếu bất kỳ cái nào = fail Stage One.
- ⚠️ **Hành động:** trong README làm hẳn 1 bảng "Mandatory Stack Compliance" chỉ thẳng file + dòng code dùng từng cái.

### 🔴 Bẫy #3 — Video >4 phút / không public / không tiếng Anh
- Chỉ 4 phút đầu được chấm.
- Phải **public** trên YouTube hoặc Vimeo (unlisted **không** được chấp nhận cho bonus content; với demo video rules ghi "publicly visible").
- Tiếng Anh hoặc **có phụ đề tiếng Anh**.
- ⚠️ **Hành động:** target 3:40. Bật caption. Kiểm tra bằng cửa sổ ẩn danh xem link có mở được không.

### 🔴 Bẫy #4 — Repo private mà quên share
Nếu private phải share cho **cả hai**: `testing@devpost.com` **và** `cloudhackathons@google.com`.
- ⚠️ **Khuyến nghị: để repo PUBLIC.** Tiêu chí Demo & Production Readiness ghi rõ "public GitHub repository". Public loại bỏ toàn bộ rủi ro này.

### 🔴 Bẫy #5 — Không có bằng chứng chạy trên Google Cloud trong video
Rules ghi rõ: "Must demonstrate the backend is running on Google Cloud".
- ⚠️ **Hành động:** quay màn hình Cloud Run dashboard + Cloud Logging live + URL `*.run.app` trên trình duyệt. Không được là ảnh tĩnh chèn vào.

### 🔴 Bẫy #6 — Demo bị dựng/cắt ghép
Rubric ghi: *"Does the video show an **unedited, live** execution of the agent performing its task"*.
- ⚠️ **Hành động:** ít nhất **một đoạn liền mạch không cắt** dài 60–90s cho thấy: trigger → agent chạy → log/DB/UI thay đổi thật.

### 🔴 Bẫy #7 — Thiếu Architecture Diagram hoặc Spin-up Instructions
Hai thứ này là **hạng mục nộp bắt buộc riêng**, không phải "nice to have".

### 🔴 Bẫy #8 — Vi phạm IP / third-party
- Submission phải là **original work**, do bạn sở hữu **hoàn toàn**, không bên thứ ba nào có quyền lợi.
- Dùng open source được, nhưng phải **tuân thủ license** và **phải tạo ra phần mềm mở rộng/nâng cấp** trên nền OSS đó, không chỉ wrap lại.
- Video **không được** chứa logo/slogan/trademark bên thứ ba gợi ý tài trợ.
  - ⚠️ Cẩn thận với logo Slack/Jira/Notion trong demo. Dùng ở mức "công cụ tích hợp" thì ổn, nhưng **đừng** làm nó trông như sponsor. Tránh nhạc có bản quyền.
- Không dùng dữ liệu thật của người khác. **Dùng synthetic data** cho mọi thứ nhạy cảm.

### 🔴 Bẫy #9 — Bonus content không ghi disclosure
Blog/video bonus **phải có câu** kiểu: *"This content was created for the purposes of entering the All Things Agentic Hackathon."* Thiếu câu này → mất 0.2 điểm.

### 🔴 Bẫy #10 — Nộp phút chót
Sau khi hết Submission Period **không được sửa gì**. Devpost hay nghẽn giờ chót.
- ⚠️ **Hành động:** nộp bản hoàn chỉnh **trước 29/08**, rồi vẫn được sửa draft đến hạn.

## 3. Điểm không nhất quán trong tài liệu gốc (cần biết)

| Vấn đề | Trang Devpost | Official Rules | Xử lý |
|---|---|---|---|
| Grand Prize tiền mặt | **$50,000** | **$40,000** | Official Rules thường thắng khi tranh chấp. Đừng lấy con số làm động lực chính. |
| Model | "Gemini 3.5 Flash" (mục What to Build) | "Gemini 3.5 or newer" | Yêu cầu thực tế là **3.5 trở lên**. Dùng Flash làm mặc định, Pro cho reasoning nặng — đúng cả rules lẫn cost tip. |
| Tên category trong rubric | Taskmaster / Collaborative Partner / Fortified Enterprise Fleet | Rubric mô tả chi tiết lại dùng tên **Continuous Action Engine / Evolving Knowledge Engine / Multi-Agent Nexus** | Đây là dấu vết template rubric cũ — **nhưng nó lộ ra sub-criteria thật**. Xem doc 03. Map: Continuous Action ≈ Taskmaster, Evolving Knowledge ≈ Collaborative Partner, Multi-Agent Nexus ≈ Fortified Fleet. |
| Hashtag | `#AllThingsAgenticHackathon` | có chỗ ghi `#AllThingsAgentic Hackathon` (có dấu cách) | Dùng **`#AllThingsAgenticHackathon`** liền, đúng như trang chính. |

## 4. Multiple submissions

Được nộp **nhiều bài**, nhưng mỗi bài phải **unique và khác nhau đáng kể** (BTC toàn quyền phán xét). Mỗi project chỉ ăn tối đa 1 giải.

> **Khuyến nghị:** với 21 ngày, **dồn toàn lực vào 1 bài xuất sắc**. Hai bài trung bình thua một bài xuất sắc ở mọi giải.

## 5. Testing & Access

- Phải cho phép Sponsor/Admin/Judges truy cập bản chạy được **miễn phí, không hạn chế**, cho tới hết Judging Period (01/10/2026).
- Nếu site private → **phải kèm login credentials** trong testing instructions.
- Judge **không bắt buộc** phải chạy thử; họ có thể chấm chỉ dựa trên **text description, hình ảnh, và video**.
  - 👉 Suy ra: **video + README là kênh truyền đạt chính**. Đầu tư vào đó ngang với đầu tư code.

## 6. Ngôn ngữ

Toàn bộ tài liệu nộp phải là **tiếng Anh** (hoặc kèm bản dịch tiếng Anh cho video, mô tả, testing instructions và mọi tài liệu khác).

> Docs nội bộ trong repo này viết tiếng Việt cho bạn dễ làm việc — nhưng **README.md, description, video, diagram nộp lên phải 100% tiếng Anh.**

## 7. Nộp bài — quy trình

1. Có tài khoản **Devpost**.
2. Xin credits qua form (hạn 28/08 12:00 PT), 1 code/entrant, duyệt trong ~72 giờ làm việc, **không đảm bảo được cấp**.
3. Vượt $150 credits → **bạn tự chịu chi phí**.
4. Tạo project đúng requirements.
5. Điền **đủ mọi trường bắt buộc** trên form "Enter a Submission".
6. Nếu là team: mọi thành viên phải được add vào Project trên Devpost; chọn 1 **Representative**.

## 8. Sau khi thắng

- Có thể được thông báo qua email; **không phản hồi trong 2 ngày → mất giải**, trao cho người kế tiếp.
- Phải ký & gửi lại Declaration of Eligibility / Liability / Publicity Release trong **2 ngày**.
- Required Forms phải trả lại trong **10 ngày làm việc**.
- Tiền trao trong vòng **60 ngày** sau khi nhận đủ form.
- Team → tiền trả cho **Representative**, người này tự chia cho team.
- ⚠️ **Hành động:** dùng email bạn check hằng ngày khi đăng ký Devpost. Bật thông báo.
