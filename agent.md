# AGENT CONTEXT & SPECIFICATION - NEU EVENTS

## 1. TỔNG QUAN DỰ ÁN
* **Tên dự án**: NEU Events - Cổng Quản lý và Tổ chức Sự kiện Đại học Kinh tế Quốc dân.
* **Mục tiêu**: Xây dựng hệ thống toàn diện hỗ trợ sinh viên khám phá, đăng ký, điểm danh và đánh giá sự kiện; hỗ trợ ban tổ chức quản lý người tham gia và điều hành sự kiện; hỗ trợ nhà trường kiểm duyệt và thống kê hoạt động.
* **Môi trường & Vị trí**: `d:\PYTHON\NEU Events`
* **Nhận diện thương hiệu**:
  * Tông màu chủ đạo: Xanh thương hiệu NEU (`#0F4C81`, `#004B87`), xanh nhạt (`#EBF3FC`), nền xám sáng (`#F8FAFC`).
  * Font chữ: Inter, Roboto, hoặc Sans-Serif hiện đại.
  * Thiết kế: Chuẩn Desktop & Responsive, giao diện thẻ (card-based), bảng dữ liệu rõ ràng.

---

## 2. TÀI NGUYÊN GIAO DIỆN CÓ SẴN (UI MOCKUPS)
Các file giao diện mẫu chuẩn xác được lưu trực tiếp trong thư mục gốc:
* `Đăng nhập.png`: Giao diện xác thực sinh viên/cán bộ.
* `Danh sách sự kiện.jpg`: Cổng khám phá sự kiện, tìm kiếm, lọc đa tiêu chí.
* `Chi tiết sự kiện.jpg`: Trang chi tiết sự kiện, timeline, tải cẩm nang PDF và nút đăng ký.
* `Sự kiện đã đăng ký.jpg`: Bảng theo dõi lịch tham gia, quản lý vé và trạng thái tham dự.
* `Điểm danh.jpg`: Không gian điểm danh 2 chiều (Sinh viên tự điểm danh qua mã PIN/QR; Ban tổ chức theo dõi real-time).
* `Quản lý sự kiện.jpg`: Bàn làm việc ban tổ chức: tạo/sửa/hủy sự kiện, quản lý danh sách đăng ký.
* `Báo cáo – thống kê.jpg`: Dashboard KPI, biểu đồ cột kép và biểu đồ tròn cơ cấu sự kiện.

---

## 3. KIẾN TRÚC CÔNG NGHỆ (TECH STACK)
* **Backend**: Python 3.10+ / **Django 5.x** (khuyến nghị cho hệ thống RBAC, ORM và quản trị) hoặc **FastAPI**.
* **Frontend**: Tailwind CSS + HTML5 Templates / Alpine.js (hoặc React/Vite).
* **Database**: SQLite (phát triển local) / PostgreSQL (production).
* **Charts & Analytics**: Chart.js / ApexCharts cho biểu đồ thống kê.
* **Check-in & QR**: `qrcode` (Python backend) và `html5-qrcode` (trình duyệt).

---

## 4. HỆ THỐNG PHÂN QUYỀN (RBAC)
1. **Sinh viên (`STUDENT`)**:
   * Đăng nhập bằng MSSV / Email NEU.
   * Xem danh sách sự kiện, tìm kiếm, lọc.
   * Đăng ký tham gia sự kiện (nhận mã vé dạng `NEU-AI-0123`), hủy đăng ký trước hạn.
   * Tự điểm danh trong khung giờ mở qua mã PIN hoặc quét QR.
   * Xem lịch sử tham gia và gửi đánh giá (chỉ mở cho sự kiện đã tham dự).
2. **Ban tổ chức (`ORGANIZER`)**:
   * Tạo sự kiện mới gửi kiểm duyệt, chỉnh sửa sự kiện của đơn vị.
   * Xem và xuất danh sách sinh viên đăng ký (Excel/CSV), gửi thông báo.
   * Mở/đóng phiên điểm danh, cấp mã PIN/QR, xác nhận điểm danh thủ công.
   * Xem báo cáo và đánh giá sự kiện của đơn vị mình.
3. **Đơn vị quản lý (`MANAGER`)**:
   * Phòng CTCT & QLSV, Ban Giám hiệu, Đoàn Trường.
   * Kiểm duyệt hồ sơ sự kiện (Phê duyệt hoặc Từ chối kèm lý do).
   * Theo dõi toàn bộ sự kiện toàn trường, xem dashboard báo cáo - thống kê tổng thể.

---

## 5. ĐẶC TẢ 9 PHÂN HỆ TRANG CHỨC NĂNG

### 5.1. Trang đăng nhập (`/login`)
* **Giao diện**: Chia 2 cột (Ảnh khuôn viên NEU bên trái, form đăng nhập bên phải).
* **Trường dữ liệu**: MSSV hoặc Email (`@st.neu.edu.vn`, `@neu.edu.vn`), Mật khẩu, Checkbox "Ghi nhớ đăng nhập".
* **Luồng xử lý**: Xác thực và điều hướng người dùng theo vai trò.

### 5.2. Trang danh sách sự kiện (`/events`)
* **Thành phần**:
  * Hero banner: Sự kiện nổi bật trong tháng + nút "Khám phá ngay".
  * Bộ lọc: Từ khóa tìm kiếm, Thời gian (Tháng/Học kỳ), Địa điểm, Loại sự kiện (Học thuật, Nghề nghiệp, Hội thảo, Cộng đồng, Văn hóa).
  * Tab trạng thái: *Tất cả*, *Sắp diễn ra*, *Đang diễn ra*, *Đã kết thúc*, *Đã hủy*.
  * Lưới sự kiện: Thẻ ảnh, badge ngày tháng, tiến độ số chỗ (`320/500`), nút "Xem chi tiết".

### 5.3. Trang chi tiết sự kiện (`/events/<id>`)
* **Thành phần**:
  * Tiêu đề, tag phân loại, ảnh cover, nút chia sẻ.
  * Giới thiệu sự kiện, khối số liệu nổi bật.
  * Lịch trình chi tiết (Timeline từng khung giờ và địa điểm con).
  * Chuẩn bị trước khi tham gia & file đính kèm (Cẩm nang PDF).
  * Card đăng ký: Số chỗ còn lại, hạn chót, nút "Đăng ký tham gia" (xử lý transaction an toàn, chống vượt quá số chỗ).
  * Thông tin đơn vị tổ chức và hotline.

### 5.4. Trang sự kiện đã đăng ký (`/my-events`)
* **Thành phần**:
  * 4 Khối thống kê: Tổng đăng ký, Sắp/đang diễn ra, Đã tham dự, Vắng mặt.
  * Banner sự kiện hôm nay đang diễn ra kèm nút "Điểm danh ngay".
  * Bảng lịch tham gia: Cột Tên sự kiện, Thời gian, Trạng thái đăng ký, Trạng thái tham dự.
  * Thao tác: "Điểm danh", "Xem vé", "Hủy đăng ký" (trước hạn), "Đánh giá", "Xem thông báo".

### 5.5. Trang điểm danh (`/checkin`)
* **Phân vùng Sinh viên**:
  * Thông tin sinh viên, mã đăng ký.
  * Nhập mã điểm danh phiên (VD: `AI1210`) hoặc nút quét QR camera.
  * Khung giờ điểm danh hợp lệ và thông báo kết quả tức thì.
* **Phân vùng Ban tổ chức**:
  * Bộ đếm live: Đã đăng ký | Đã tham dự | Chưa điểm danh.
  * Hiển thị mã phiên kích thước lớn kèm QR chiếu màn hình; nút "Đóng phiên".
  * Danh sách sinh viên live, nút "Xác nhận thủ công", nút "Xuất danh sách".

### 5.6. Trang quản lý sự kiện (`/organizer/events`)
* **Thành phần**:
  * Bảng danh sách sự kiện của đơn vị kèm trạng thái duyệt.
  * Form Tạo mới / Chỉnh sửa sự kiện: Tên, thể loại, ngày giờ, địa điểm, số chỗ tối đa, hạn đăng ký, mô tả, upload poster.
  * Quản lý người đăng ký: Xem danh sách, tìm kiếm, xuất file Excel, gửi thông báo email.
  * Chức năng hủy sự kiện kèm nhập lý do gửi đến người đăng ký.

### 5.7. Trang kiểm duyệt (`/moderation`)
* **Thành phần**:
  * Danh sách hồ sơ sự kiện chờ duyệt gửi từ các đơn vị.
  * Cảnh báo xung đột phòng/hội trường nếu trùng lịch.
  * Chi tiết nội dung hồ sơ sự kiện, kịch bản, poster.
  * Nút "Phê duyệt" hoặc "Từ chối / Yêu cầu sửa đổi" kèm lý do.

### 5.8. Trang đánh giá (`/feedback`)
* **Thành phần**:
  * Điều kiện: Chỉ mở cho sự kiện có trạng thái `Đã tham dự`.
  * Form đánh giá sinh viên: Chấm điểm 1-5 sao, tiêu chí cụ thể (nội dung, tổ chức, diễn giả, địa điểm), nhận xét tự luận, tùy chọn ẩn danh.
  * Trang xem đánh giá cho BTC/Quản lý: Điểm trung bình, phân bố sao, danh sách nhận xét.

### 5.9. Trang báo cáo – thống kê (`/analytics`)
* **Thành phần**:
  * Bộ lọc theo khoảng thời gian, đơn vị tổ chức, loại sự kiện. Nút "Xuất báo cáo".
  * 4 KPI cards: Số sự kiện, Lượt đăng ký, Lượt tham dự, Tỷ lệ tham dự %.
  * Biểu đồ cột đôi: Đăng ký vs Tham dự theo tuần.
  * Biểu đồ tròn Donut: Cơ cấu sự kiện theo thể loại.
  * Bảng hiệu quả chi tiết từng sự kiện.

---

## 6. SƠ ĐỒ THỰC THỂ CƠ SỞ DỮ LIỆU (DATABASE SCHEMA)
* `User`: `id, username, full_name, email, password, role, department, phone, created_at`
* `EventCategory`: `id, name, slug`
* `Event`: `id, title, category_id, organizer_id, description, location, event_date, start_time, end_time, max_seats, registration_deadline, cover_image, status, cancel_reason`
* `Registration`: `id, user_id, event_id, ticket_code, status, registered_at`
* `AttendanceSession`: `id, event_id, session_pin, qr_token, valid_from, valid_to, is_active`
* `AttendanceRecord`: `id, session_id, registration_id, checked_in_at, checkin_method, status`
* `Feedback`: `id, event_id, user_id, rating_stars, comment, is_anonymous, created_at`
* `ApprovalLog`: `id, event_id, manager_id, action, note, created_at`

---

## 7. QUY TẮC PHÁT TRIỂN DÀNH CHO AGENT
1. **Bảo toàn thiết kế**: Mọi component, màu sắc, font chữ, layout phải bám sát theo các file ảnh wireframe trong thư mục.
2. **Toàn vẹn dữ liệu**:
   * Khi sinh viên đăng ký, kiểm tra số chỗ còn lại (`registered_count < max_seats`) bằng atomic transaction để tránh race-condition / overbooking.
   * Điểm danh chỉ hợp lệ khi phiên đang mở (`is_active = True`) và trong khung giờ `valid_from <= now <= valid_to`.
   * Đánh giá chỉ cho phép khi trạng thái tham dự là `ATTENDED`.
3. **Mã nguồn sạch & Tài liệu**:
   * Tuân thủ PEP 8 cho Python backend.
   * Giữ cấu trúc thư mục rõ ràng: `apps/`, `templates/`, `static/`, `media/`.
