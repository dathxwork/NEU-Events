# NEU Events - Cổng Quản lý và Tổ chức Sự kiện Đại học Kinh tế Quốc dân

Hệ thống web toàn diện phục vụ công tác tổ chức, quản lý, kiểm duyệt và tham gia sự kiện dành cho sinh viên, các đơn vị ban tổ chức và ban quản lý Đại học Kinh tế Quốc dân (NEU).

---

## 👥 1. Tài khoản Trải nghiệm Hệ thống (Đăng nhập ngay)

Bộ dữ liệu mẫu đã được tinh gọn chuẩn hóa gồm **đúng 5 tài khoản** đại diện cho 3 vai trò thực tế. **Tất cả các tài khoản đều sử dụng chung mật khẩu mặc định là `123`**:

| Phân quyền (Role)               | Mã đăng nhập / Email | Mật khẩu  | Đơn vị / Họ tên đại diện          | Mục đích kiểm thử chính                                                              |
| :------------------------------ | :------------------- | :-------: | :-------------------------------- | :----------------------------------------------------------------------------------- |
| **Đơn vị Quản lý (`MANAGER`)**  | `quanly@neu.edu.vn`  | **`123`** | Phòng Quản lý Đào tạo & Sự kiện   | Kiểm duyệt phê duyệt sự kiện (`/moderation`), Báo cáo KPI toàn trường (`/analytics`) |
| **Ban tổ chức 1 (`ORGANIZER`)** | `vieclam@neu.edu.vn` | **`123`** | TT Tư vấn hướng nghiệp & Việc làm | Quản lý Ngày hội việc làm, mở phiên điểm danh, xuất CSV, xem feedback                |
| **Ban tổ chức 2 (`ORGANIZER`)** | `fit@neu.edu.vn`     | **`123`** | Khoa Công nghệ thông tin          | Đăng ký sự kiện mới (trạng thái PENDING), kiểm tra cô lập dữ liệu BTC                |
| **Sinh viên 1 (`STUDENT`)**     | `11244035`           | **`123`** | Nguyễn Thị Thu (`11244035@st.neu.edu.vn` - Khoa CNTT) | Xem vé điện tử, tự quét QR điểm danh, gửi đánh giá sự kiện đã tham gia |
| **Sinh viên 2 (`STUDENT`)**     | `11240123`           | **`123`** | Nguyễn Minh Anh (`11240123@st.neu.edu.vn` - Khoa Marketing) | Đăng ký sự kiện mới, gửi đánh giá sự kiện kỹ năng viết CV              |

> 💡 **Mẹo**: Ngay tại trang Đăng nhập (`/login`), hệ thống có sẵn bảng widget **"Tài khoản trải nghiệm mẫu"** với nút **Chọn** 1-click để tự động điền tài khoản và mật khẩu mà không cần gõ thủ công.

---

## 🛡️ 2. Ma trận Phân quyền Chuẩn Nghiệp vụ Thực tế

Hệ thống phân tách triệt để quyền hạn giữa 3 nhóm đối tượng, không chồng chéo:

| Phân hệ chức năng           | Đường dẫn (URL)     |                    Sinh viên (`STUDENT`)                    |               Ban tổ chức (`ORGANIZER`)               |            Đơn vị Quản lý (`MANAGER`)            |
| :-------------------------- | :------------------ | :---------------------------------------------------------: | :---------------------------------------------------: | :----------------------------------------------: |
| **Cổng Khám phá sự kiện**   | `/events`           |                   Xem & Đăng ký tham gia                    |              Xem sự kiện (không đăng ký)              |           Xem sự kiện (không đăng ký)            |
| **Chi tiết sự kiện**        | `/events/<id>`      |                  Đăng ký / Xem vé điện tử                   |       Nút Quản lý & Điểm danh (nếu là của mình)       |       Nút Phê duyệt (nếu sự kiện PENDING)        |
| **Sự kiện đã đăng ký & Vé** | `/my-events`        |            **Toàn quyền** (Lịch trình, mã QR vé)            |                   ❌ Chặn truy cập                    |                 ❌ Chặn truy cập                 |
| **Quản lý sự kiện BTC**     | `/organizer/events` |                      ❌ Chặn truy cập                       |  **Tạo mới, chỉnh sửa, hủy sự kiện của đơn vị mình**  |      ❌ Chặn truy cập (Dùng `/moderation`)       |
| **Điểm danh hội trường**    | `/checkin`          | **Chỉ tự quét QR bằng camera** (không can thiệp người khác) | **Mở phiên, chiếu QR, điểm danh thủ công, xuất CSV**  |                 ❌ Chặn truy cập                 |
| **Đánh giá sự kiện**        | `/feedback`         |          **Gửi đánh giá** (chỉ sự kiện đã tham dự)          | **Xem thống kê & nhận xét** (sự kiện của đơn vị mình) |       ❌ Chặn truy cập (Xem tại Analytics)       |
| **Kiểm duyệt sự kiện**      | `/moderation`       |                      ❌ Chặn truy cập                       |                   ❌ Chặn truy cập                    | **Toàn quyền Phê duyệt / Từ chối hồ sơ sự kiện** |
| **Báo cáo – Thống kê**      | `/analytics`        |                      ❌ Chặn truy cập                       |                Thống kê số liệu đơn vị                |    **Báo cáo toàn diện KPI vĩ mô cấp trường**    |

---

## 🎯 3. Bộ Dữ liệu Mẫu Tiêu biểu (4 Sự kiện Trọng tâm)

1. **`NEU-JOB-2026` — Ngày hội việc làm NEU 2026**:
   - _Đơn vị tổ chức_: `vieclam@neu.edu.vn` (Trung tâm Hướng nghiệp & Việc làm).
   - _Trạng thái_: `APPROVED` (Đã duyệt, diễn ra hôm nay, đang mở phiên điểm danh).
   - _Dữ liệu sẵn sàng_: Sinh viên `11244035` đã có vé `NEU-JOB-0112` ở trạng thái chưa điểm danh.
   - _Mục đích test_: Sinh viên test quét QR điểm danh; BTC test chiếu QR, điểm danh thủ công, xuất file CSV.

2. **`NEU-AI-2026` — Hội thảo Ứng dụng AI & Công nghệ số**:
   - _Đơn vị tổ chức_: `fit@neu.edu.vn` (Khoa Công nghệ thông tin).
   - _Trạng thái_: `PENDING` (Chờ duyệt).
   - _Mục đích test_: Đơn vị Quản lý (`quanly@neu.edu.vn`) vào `/moderation` thực hiện Phê duyệt hoặc Từ chối kèm lý do phản hồi cho BTC.

3. **`NEU-SKILL-2026` — Tọa đàm Kỹ năng Viết CV & Phỏng vấn**:
   - _Đơn vị tổ chức_: `vieclam@neu.edu.vn` (Trung tâm Hướng nghiệp & Việc làm).
   - _Trạng thái_: `COMPLETED` (Đã diễn ra tuần trước).
   - _Dữ liệu sẵn sàng_: Sinh viên `11244035` và `11240123` đã tham dự (`ATTENDED`). Sinh viên Thu đã gửi 1 nhận xét 5 sao.
   - _Mục đích test_: Sinh viên Minh Anh vào gửi đánh giá mới; BTC Việc làm vào xem biểu đồ sao & nhận xét; BTC Khoa Công nghệ thông tin vào `/feedback` sẽ **không thấy** sự kiện này (đảm bảo cô lập dữ liệu).

4. **`NEU-HACK-2026` — Cuộc thi Sáng tạo Công nghệ NEU Hackathon 2026**:
   - _Đơn vị tổ chức_: `fit@neu.edu.vn` (Khoa Công nghệ thông tin).
   - _Trạng thái_: `APPROVED` (Đang mở đăng ký cho sinh viên).
   - _Mục đích test_: Sinh viên bấm đăng ký nhận vé; BTC Việc làm không thể chỉnh sửa hay hủy sự kiện này.

---

## 🚀 4. Hướng dẫn Khởi chạy Dự án

### Yêu cầu môi trường

- Python 3.10 trở lên

### Các lệnh thực hiện:

1. **Cài đặt thư viện phụ thuộc:**

   ```bash
   pip install -r requirements.txt
   ```

2. **Khởi tạo dữ liệu mẫu chuẩn (5 tài khoản & 4 sự kiện):**

   ```bash
   python data_seeder.py
   ```

3. **Khởi chạy ứng dụng Web Flask:**

   ```bash
   python app.py
   ```

4. **Mở trình duyệt:**
   Truy cập: [http://127.0.0.1:5000](http://127.0.0.1:5000)

5. **Chạy kiểm thử tự động (Unit Tests):**
   ```bash
   python -m unittest test_app.py
   ```

---

## 🧪 5. Kịch bản Kiểm thử Nhanh 5 Phút (Theo từng Vai trò)

### Kịch bản 1: Sinh viên (`11244035` / `123`)

1. Đăng nhập với MSSV `11244035`, mật khẩu `123`.
2. Vào **Sự kiện đã đăng ký** (`/my-events`): Thấy vé sự kiện "Ngày hội việc làm NEU 2026".
3. Vào **Điểm danh** (`/checkin`): Giao diện chỉ có camera quét QR Code, không có nút xác nhận cho người khác hay xuất file. Thử quét mã PIN `JOB2026` -> Nhận thông báo điểm danh thành công.
4. Vào **Đánh giá** (`/feedback`): Xem lịch sử đánh giá đã gửi và gửi đánh giá cho các sự kiện đã tham dự.

### Kịch bản 2: Ban tổ chức Việc làm (`vieclam@neu.edu.vn` / `123`)

1. Đăng nhập `vieclam@neu.edu.vn`, mật khẩu `123`.
2. Vào **Quản lý sự kiện** (`/organizer/events`): Chỉ thấy 2 sự kiện của Trung tâm Việc làm (`NEU-JOB-2026` và `NEU-SKILL-2026`), hoàn toàn không thấy sự kiện của Khoa Công nghệ thông tin.
3. Thử tạo mới sự kiện hoặc chỉnh sửa sự kiện của mình -> Thành công.
4. Vào **Điểm danh** (`/checkin`): Thấy màn chiếu mã QR, danh sách sinh viên trực tiếp, nút điểm danh thủ công và nút xuất CSV.
5. Vào **Đánh giá sự kiện** (`/feedback`): Xem điểm đánh giá 5 sao và nhận xét chi tiết của sinh viên cho sự kiện Kỹ năng viết CV.

### Kịch bản 3: Ban tổ chức Khoa Công nghệ thông tin (`fit@neu.edu.vn` / `123`)

1. Đăng nhập `fit@neu.edu.vn`, mật khẩu `123`.
2. Vào **Quản lý sự kiện**: Thấy sự kiện `NEU-AI-2026` đang ở trạng thái `Chờ duyệt (PENDING)`.
3. Kiểm tra cô lập dữ liệu: Thử truy cập sự kiện của BTC Việc làm -> Hệ thống cảnh báo từ chối truy cập ngay lập tức.

### Kịch bản 4: Đơn vị Quản lý Nhà trường (`quanly@neu.edu.vn` / `123`)

1. Đăng nhập `quanly@neu.edu.vn`, mật khẩu `123`.
2. Quan sát Menu: Không có mục "Đã đăng ký", không có mục "Điểm danh" hay "Đánh giá".
3. Vào **Kiểm duyệt** (`/moderation`): Thấy hồ sơ `NEU-AI-2026` do Khoa Công nghệ thông tin gửi lên. Bấm nút **Phê duyệt** -> Sự kiện ngay lập tức chuyển sang trạng thái `Đã duyệt` và xuất bản công khai.
4. Vào **Báo cáo – Thống kê** (`/analytics`): Theo dõi các biểu đồ KPI toàn trường.

---

## 📁 6. Cấu trúc Thư mục

```text
NEU-Events/
├── instance/
│   └── neu_events.db           # SQLite database
├── templates/                  # Giao diện Jinja2 HTML Templates (Tailwind CSS)
│   ├── base.html               # Khung sườn chung, phân tách thanh điều hướng 3 vai trò
│   ├── login.html              # Trang đăng nhập với thẻ demo credentials 1-click
│   ├── events.html             # Cổng khám phá & tìm kiếm sự kiện
│   ├── event_detail.html       # Chi tiết chương trình & form đăng ký tham gia
│   ├── my_events.html          # Lịch trình vé điện tử cá nhân (Sinh viên)
│   ├── checkin.html            # Điểm danh 2 chiều (QR Scanner cho SV, Màn chiếu cho BTC)
│   ├── organizer_events.html   # Quản lý hồ sơ & tạo mới sự kiện (Ban tổ chức)
│   ├── moderation.html         # Kiểm duyệt & phê duyệt hồ sơ sự kiện (Đơn vị Quản lý)
│   ├── feedback.html           # Khảo sát & xem phản hồi sau sự kiện
│   └── analytics.html          # Báo cáo KPI & biểu đồ thống kê
├── app.py                      # Flask Application Controller & Route RBAC
├── models.py                   # SQLAlchemy ORM Models
├── data_seeder.py              # Script nạp bộ 5 tài khoản & 4 sự kiện mẫu chuẩn
├── test_app.py                 # Bộ kiểm thử tự động 17 test cases
├── requirements.txt            # Danh sách thư viện phụ thuộc Python
└── README.md                   # Tài liệu hướng dẫn sử dụng và thông tin tài khoản
```
