"""
Compact Data Seeder for NEU Events Management System
Populates the database with a clean, focused, and realistic sample dataset:
- Exactly 5 Accounts (Manager, 2 Organizers, 2 Students) - All default password '123'
- Exactly 4 Core Events strictly matching real-world date and time (using date.today() and today.year):
  1. NEU-JOB (APPROVED, Today, full-day check-in active) - Organized by Career Center
  2. NEU-AI (PENDING approval, 7 days later) - Organized by IT & Digital Economics Institute
  3. NEU-SKILL (COMPLETED, 3 days ago, attended with reviews) - Organized by Career Center
  4. NEU-HACK (APPROVED, 14 days later, registration open) - Organized by IT & Digital Economics Institute
"""
from datetime import datetime, date, time, timedelta
import json
from models import db, User, EventCategory, Event, Registration, AttendanceSession, AttendanceRecord, Feedback, ApprovalLog

def seed_database(app):
    with app.app_context():
        print("Recreating database schema...")
        db.drop_all()
        db.create_all()

        print("1. Creating 5 Core Users (Default password: '123')...")

        # 1.1 Manager (Đơn vị Quản lý / Nhà trường)
        manager = User(
            username='quanly@neu.edu.vn',
            email='quanly@neu.edu.vn',
            full_name='Đơn vị Quản lý',
            role='MANAGER',
            department='Phòng Quản lý Đào tạo & Sự kiện Nhà trường',
            phone='024 3628 0280',
            avatar_initials='QL'
        )
        manager.set_password('123')

        # 1.2 Organizer 1 (Trung tâm Hướng nghiệp & Việc làm)
        org_career = User(
            username='vieclam@neu.edu.vn',
            email='vieclam@neu.edu.vn',
            full_name='TT Hướng nghiệp & Việc làm',
            role='ORGANIZER',
            department='Trung tâm Tư vấn hướng nghiệp & Việc làm NEU',
            phone='024 3628 0280 • 6032',
            avatar_initials='VL'
        )
        org_career.set_password('123')

        # 1.3 Organizer 2 (Khoa Công nghệ thông tin)
        org_it = User(
            username='fit@neu.edu.vn',
            email='fit@neu.edu.vn',
            full_name='Khoa Công nghệ thông tin',
            role='ORGANIZER',
            department='Khoa Công nghệ thông tin',
            phone='024 3628 0280 • 8011',
            avatar_initials='FIT'
        )
        org_it.set_password('123')

        # 1.4 Student 1 (Nguyễn Thị Thu - Khoa Công nghệ thông tin)
        student_thu = User(
            username='11244035',
            email='11244035@st.neu.edu.vn',
            full_name='Nguyễn Thị Thu',
            role='STUDENT',
            department='Khoa Công nghệ thông tin',
            student_id='11244035',
            phone='0987123456',
            avatar_initials='TT'
        )
        student_thu.set_password('123')

        # 1.5 Student 2 (Nguyễn Minh Anh - Khoa Marketing)
        student_anh = User(
            username='11240123',
            email='11240123@st.neu.edu.vn',
            full_name='Nguyễn Minh Anh',
            role='STUDENT',
            department='Khoa Marketing',
            student_id='11240123',
            phone='0912345678',
            avatar_initials='MA'
        )
        student_anh.set_password('123')

        db.session.add_all([manager, org_career, org_it, student_thu, student_anh])
        db.session.commit()

        print("2. Creating Event Categories...")
        cat_career = EventCategory(name='Nghề nghiệp', color_class='blue')
        cat_tech = EventCategory(name='Công nghệ', color_class='purple')
        cat_academic = EventCategory(name='Học thuật', color_class='emerald')
        cat_culture = EventCategory(name='Văn hóa & Kỹ năng', color_class='amber')

        db.session.add_all([cat_career, cat_tech, cat_academic, cat_culture])
        db.session.commit()

        print("3. Creating 4 Core Events with Real-World System Date & Time...")
        today = date.today()
        year = today.year

        # EVENT 1: Ngày hội việc làm NEU (APPROVED, Today, Full-day checkin active)
        e_job = Event(
            code=f'NEU-JOB-{year}',
            title=f'Ngày hội việc làm NEU {year}',
            subtitle='Mở lối sự nghiệp, kết nối hơn 50 doanh nghiệp hàng đầu',
            category_id=cat_career.id,
            organizer_id=org_career.id,
            organizer_name='Trung tâm Tư vấn hướng nghiệp & Việc làm NEU',
            organizer_email=org_career.email,
            organizer_phone='024 3628 0280',
            location='Hội trường A2 & Sảnh nhà A1',
            target_audience='Sinh viên & cựu sinh viên NEU',
            fee='Miễn phí',
            event_date=today,
            start_time=time(7, 30),
            end_time=time(23, 59), # Open throughout today
            registration_deadline=datetime.combine(today, time(23, 59)),
            max_seats=300,
            registered_seats=1,
            attended_seats=0,
            description=f"""Ngày hội việc làm NEU {year} mang đến cơ hội gặp gỡ hơn 50 doanh nghiệp hàng đầu trong lĩnh vực tài chính, ngân hàng, công nghệ và kinh doanh. Khám phá các vị trí thực tập, tuyển dụng chính thức và phỏng vấn trực tiếp tại hội trường.""",
            agenda_json=json.dumps([
                {"time": "08:00–08:30", "title": "Đón tiếp sinh viên & mở cổng điểm danh", "venue": "Sảnh nhà A1"},
                {"time": "08:30–09:30", "title": f"Khai mạc & đối thoại nghề nghiệp {year}", "venue": "Hội trường A2"},
                {"time": "09:30–15:30", "title": "Phỏng vấn tuyển dụng & nộp hồ sơ trực tiếp", "venue": "Khu gian hàng doanh nghiệp"},
                {"time": "15:30–16:30", "title": "Tổng kết & bốc thăm trúng thưởng", "venue": "Hội trường A2"}
            ]),
            checklist_json=json.dumps([
                "Chuẩn bị thẻ sinh viên NEU hoặc mã vé điện tử trên app",
                "Mang theo ít nhất 3 bản CV in sẵn để ứng tuyển",
                "Trang phục lịch sự, chỉnh tề"
            ]),
            handbook_name=f'Cam_nang_Ngay_hoi_viec_lam_NEU_{year}.pdf',
            sponsor_benefits="""- Bộ quà tặng Welcome Kit NEU (Tote bag NEU + Sổ tay NEU + Bút ký)
- Voucher giảm giá 50% khóa học Luyện thi chứng chỉ quốc tế CFA/ACCA từ Smart Train
- Cơ hội nhận học bổng thực tập tài năng trị giá 5.000.000 VNĐ từ MB Bank & BIDV
- Fast-track phỏng vấn đặc cách vòng sơ loại tại hơn 10 tập đoàn đối tác""",
            union_points_plus=10,
            union_points_minus=2,
            status='APPROVED',
            is_featured=True
        )

        # EVENT 2: Hội thảo Ứng dụng AI & Công nghệ số (PENDING, for Manager review test)
        e_ai = Event(
            code=f'NEU-AI-{year}',
            title=f'Hội thảo Ứng dụng AI & Công nghệ số trong Doanh nghiệp {year}',
            subtitle='Tiếp cận xu hướng Generative AI và chuyển đổi số thực tiễn',
            category_id=cat_tech.id,
            organizer_id=org_it.id,
            organizer_name='Khoa Công nghệ thông tin',
            organizer_email=org_it.email,
            organizer_phone='024 3628 0280',
            location='Hội trường B1, Nhà B',
            target_audience='Sinh viên quan tâm đến AI và chuyển đổi số',
            fee='Miễn phí',
            event_date=today + timedelta(days=7),
            start_time=time(9, 0),
            end_time=time(11, 30),
            registration_deadline=datetime.combine(today + timedelta(days=6), time(23, 59)),
            max_seats=150,
            registered_seats=0,
            attended_seats=0,
            description="""Hội thảo do Khoa Công nghệ thông tin tổ chức nhằm giúp sinh viên cập nhật các đột phá công nghệ mới nhất về Trí tuệ nhân tạo, ứng dụng AI trong phân tích dữ liệu kinh doanh và định hướng nghề nghiệp thời đại số.""",
            agenda_json=json.dumps([
                {"time": "09:00–09:20", "title": "Khai mạc hội thảo", "venue": "Hội trường B1"},
                {"time": "09:20–10:30", "title": "Chuyên đề: Generative AI trong quản trị doanh nghiệp", "venue": "Hội trường B1"},
                {"time": "10:30–11:30", "title": "Hỏi đáp (Q&A) cùng chuyên gia", "venue": "Hội trường B1"}
            ]),
            handbook_name=f'Tai_lieu_Hoi_thao_AI_{year}.pdf',
            union_points_plus=5,
            union_points_minus=0,
            status='PENDING', # Requires Manager approval at /moderation
            is_featured=False
        )

        # EVENT 3: Tọa đàm Viết CV & Phỏng vấn (COMPLETED, attended with feedbacks)
        e_skill = Event(
            code=f'NEU-SKILL-{year}',
            title=f'Tọa đàm Kỹ năng Viết CV & Chinh phục Nhà tuyển dụng {year}',
            subtitle='Bí quyết hoàn thiện hồ sơ ứng tuyển chuyên nghiệp và phỏng vấn tự tin',
            category_id=cat_culture.id,
            organizer_id=org_career.id,
            organizer_name='Trung tâm Tư vấn hướng nghiệp & Việc làm NEU',
            organizer_email=org_career.email,
            organizer_phone='024 3628 0280',
            location='Phòng Hội thảo G, Tòa nhà Thế kỷ',
            target_audience='Sinh viên năm 3 & năm 4 NEU',
            fee='Miễn phí',
            event_date=today - timedelta(days=3),
            start_time=time(14, 0),
            end_time=time(16, 30),
            registration_deadline=datetime.combine(today - timedelta(days=4), time(23, 59)),
            max_seats=100,
            registered_seats=2,
            attended_seats=2,
            description="""Tọa đàm chuyên sâu về kỹ năng viết CV nổi bật, giải quyết các câu hỏi tình huống trong phỏng vấn tuyển dụng thực tế cùng các chuyên gia nhân sự đầu ngành.""",
            agenda_json=json.dumps([
                {"time": "14:00–14:30", "title": "Check-in & ổn định chỗ ngồi", "venue": "Phòng Hội thảo G"},
                {"time": "14:30–15:30", "title": "Cấu trúc một bản CV chuẩn quốc tế", "venue": "Phòng Hội thảo G"},
                {"time": "15:30–16:30", "title": "Thực hành phỏng vấn thử tại chỗ", "venue": "Phòng Hội thảo G"}
            ]),
            handbook_name=f'Cam_nang_Viet_CV_Neu_{year}.pdf',
            union_points_plus=5,
            union_points_minus=1,
            status='COMPLETED',
            is_featured=False
        )

        # EVENT 4: NEU Tech Hackathon (APPROVED, Registration open)
        e_hack = Event(
            code=f'NEU-HACK-{year}',
            title=f'Cuộc thi Sáng tạo Công nghệ NEU Hackathon {year}',
            subtitle='Sân chơi đổi mới sáng tạo và lập trình giải pháp số cho sinh viên',
            category_id=cat_tech.id,
            organizer_id=org_it.id,
            organizer_name='Khoa Công nghệ thông tin',
            organizer_email=org_it.email,
            organizer_phone='024 3628 0280',
            location='Không gian Khởi nghiệp Tầng 3, Thư viện Phạm Văn Đồng',
            target_audience='Toàn thể sinh viên khối kinh tế và công nghệ NEU',
            fee='Miễn phí',
            event_date=today + timedelta(days=14),
            start_time=time(8, 0),
            end_time=time(17, 0),
            registration_deadline=datetime.combine(today + timedelta(days=12), time(23, 59)),
            max_seats=120,
            registered_seats=0,
            attended_seats=0,
            description="""Cuộc thi thường niên nhằm thúc đẩy tinh thần khởi nghiệp, sáng tạo giải pháp công nghệ số giải quyết các bài toán kinh tế - xã hội dành cho sinh viên NEU.""",
            handbook_name=f'The_le_NEU_Hackathon_{year}.pdf',
            sponsor_benefits="""- Áo thun NEU Hackathon bản giới hạn & Bộ sticker lập trình viên
- Tài khoản AWS Cloud Credits trị giá $100 / bạn do Amazon Web Services tài trợ
- Học bổng 100% khóa học Lập trình Full-stack / AI trị giá 12.000.000 VNĐ cho top thí sinh
- Cơ hội được các quỹ đầu tư mạo hiểm cố vấn phát triển sản phẩm thực tế""",
            union_points_plus=15,
            union_points_minus=5,
            status='APPROVED',
            is_featured=True
        )

        # EVENT 5: Đại nhạc hội Chào Xuân & NEU Youth Festival 2027 (Năm học 2026-2027, Học kỳ Xuân 2027)
        e_spring_fest = Event(
            code='NEU-SPRING-2027',
            title='Đại nhạc hội Chào Xuân & NEU Youth Festival 2027',
            subtitle='Bùng nổ đam mê tuổi trẻ, kết nối sinh viên toàn trường chào đón năm mới',
            category_id=cat_culture.id,
            organizer_id=org_career.id,
            organizer_name='Trung tâm Tư vấn hướng nghiệp & Việc làm NEU',
            organizer_email=org_career.email,
            organizer_phone='024 3628 0280',
            location='Sân quảng trường NEU',
            target_audience='Toàn thể sinh viên và cựu sinh viên NEU',
            fee='Miễn phí',
            event_date=date(2027, 3, 20),
            start_time=time(18, 30),
            end_time=time(22, 30),
            registration_deadline=datetime(2027, 3, 19, 23, 59),
            max_seats=500,
            registered_seats=1,
            attended_seats=0,
            description="""Đại nhạc hội NEU Youth Festival 2027 là đêm hội âm nhạc và nghệ thuật thường niên lớn nhất trường, quy tụ các câu lạc bộ nghệ thuật sinh viên và nghệ sĩ khách mời nổi tiếng.""",
            handbook_name='So_tay_NEU_Youth_Festival_2027.pdf',
            sponsor_benefits="""- Vòng tay dạ quang VIP & bộ quà tặng độc quyền NEU Youth Festival 2027
- Voucher đồ uống & ẩm thực miễn phí từ Highlands Coffee & Phúc Long
- Cơ hội trúng tai nghe không dây Sony và loa Bluetooth trong phần bốc thăm may mắn""",
            union_points_plus=10,
            union_points_minus=2,
            status='APPROVED',
            is_featured=False
        )

        # EVENT 6: Tọa đàm Fintech 2027 (Năm học 2026-2027, Học kỳ Xuân 2027)
        e_fintech = Event(
            code='NEU-FINTECH-2027',
            title='Tọa đàm Công nghệ Tài chính Fintech & Cơ hội Nghề nghiệp 2027',
            subtitle='Xu hướng ngân hàng số, thanh toán thông minh và kỹ năng tài chính thời kỳ 4.0',
            category_id=cat_tech.id,
            organizer_id=org_it.id,
            organizer_name='Khoa Công nghệ thông tin',
            organizer_email=org_it.email,
            organizer_phone='024 3628 0280',
            location='Hội trường A2',
            target_audience='Sinh viên Khoa CNTT và Viện Ngân hàng - Tài chính',
            fee='Miễn phí',
            event_date=date(2027, 4, 15),
            start_time=time(8, 30),
            end_time=time(11, 30),
            registration_deadline=datetime(2027, 4, 14, 23, 59),
            max_seats=200,
            registered_seats=0,
            attended_seats=0,
            description="""Tọa đàm chuyên sâu về hệ sinh thái Fintech, xu hướng ngân hàng mở và nhu cầu nhân lực công nghệ số trong ngành tài chính.""",
            handbook_name='Cam_nang_Fintech_NEU_2027.pdf',
            union_points_plus=8,
            union_points_minus=0,
            status='APPROVED',
            is_featured=False
        )

        # EVENT 6B: Workshop Digital Marketing & Xây dựng Thương hiệu cá nhân (Năm học 2026-2027)
        e_marketing = Event(
            code=f'NEU-MKT-{year}',
            title=f'Workshop Digital Marketing & Xây dựng Thương hiệu cá nhân {year}',
            subtitle='Thực chiến xây dựng kênh nội dung số và kỹ năng định vị bản thân',
            category_id=cat_career.id,
            organizer_id=org_career.id,
            organizer_name='Trung tâm Tư vấn hướng nghiệp & Việc làm NEU',
            organizer_email=org_career.email,
            organizer_phone='024 3628 0280',
            location='Phòng Hội thảo G, Tòa nhà Thế kỷ',
            target_audience='Sinh viên toàn trường đam mê Marketing và Truyền thông',
            fee='Miễn phí',
            event_date=today + timedelta(days=25),
            start_time=time(14, 0),
            end_time=time(17, 0),
            registration_deadline=datetime.combine(today + timedelta(days=24), time(23, 59)),
            max_seats=150,
            registered_seats=0,
            attended_seats=0,
            description="""Workshop hướng dẫn sinh viên các công cụ sáng tạo nội dung số, chiến lược xây dựng thương hiệu cá nhân trên LinkedIn và TikTok từ các chuyên gia Marketing đầu ngành.""",
            handbook_name=f'Cam_nang_Marketing_NEU_{year}.pdf',
            union_points_plus=6,
            union_points_minus=1,
            status='APPROVED',
            is_featured=False
        )

        # EVENT 6C: Cuộc thi Giải quyết Tình huống Kinh doanh NEU Case Competition (Năm học 2026-2027)
        e_case = Event(
            code=f'NEU-CASE-{year}',
            title=f'Cuộc thi Giải quyết Tình huống Kinh doanh NEU Case Competition {year}',
            subtitle='Thử thách tư duy chiến lược và phân tích bài toán kinh doanh thực tế',
            category_id=cat_academic.id,
            organizer_id=org_career.id,
            organizer_name='Trung tâm Tư vấn hướng nghiệp & Việc làm NEU',
            organizer_email=org_career.email,
            organizer_phone='024 3628 0280',
            location='Hội trường A2',
            target_audience='Sinh viên khối ngành kinh tế và kinh doanh',
            fee='Miễn phí',
            event_date=today + timedelta(days=35),
            start_time=time(8, 0),
            end_time=time(12, 0),
            registration_deadline=datetime.combine(today + timedelta(days=32), time(23, 59)),
            max_seats=250,
            registered_seats=0,
            attended_seats=0,
            description="""Sân chơi học thuật đỉnh cao mô phỏng các bài toán tái cấu trúc và tăng trưởng của các tập đoàn đa quốc gia dành cho sinh viên NEU.""",
            handbook_name=f'The_le_Case_Competition_{year}.pdf',
            union_points_plus=12,
            union_points_minus=3,
            status='APPROVED',
            is_featured=False
        )

        # EVENT 6D: Chiến dịch Tình nguyện Đông Ấm NEU (Năm học 2026-2027)
        e_volunteer = Event(
            code=f'NEU-VOL-{year}',
            title=f'Chiến dịch Tình nguyện Đông Ấm - Đoàn Thanh niên NEU {year}',
            subtitle='Lan tỏa yêu thương, chung tay sẻ chia cùng trẻ em vùng cao',
            category_id=cat_culture.id,
            organizer_id=org_career.id,
            organizer_name='Trung tâm Tư vấn hướng nghiệp & Việc làm NEU',
            organizer_email=org_career.email,
            organizer_phone='024 3628 0280',
            location='Sân nhà A1 & Các điểm tình nguyện',
            target_audience='Đoàn viên, sinh viên Đại học Kinh tế Quốc dân',
            fee='Miễn phí',
            event_date=today + timedelta(days=45),
            start_time=time(7, 30),
            end_time=time(17, 30),
            registration_deadline=datetime.combine(today + timedelta(days=40), time(23, 59)),
            max_seats=300,
            registered_seats=0,
            attended_seats=0,
            description="""Chiến dịch thường niên do Đoàn Đại học phát động nhằm quyên góp chăn ấm, sách vở và tổ chức các hoạt động an sinh xã hội ý nghĩa.""",
            handbook_name=f'Ke_hoach_Dong_Am_{year}.pdf',
            union_points_plus=15,
            union_points_minus=0,
            status='APPROVED',
            is_featured=False
        )

        # EVENT 7: Ngày hội Văn hóa Sinh viên Quốc tế NEU 2025 (Năm học 2025-2026, Học kỳ Thu 2025)
        e_2025_cult = Event(
            code='NEU-CULT-2025',
            title='Ngày hội Văn hóa Sinh viên Quốc tế NEU 2025',
            subtitle='Giao lưu văn hóa đa quốc gia, ẩm thực và âm nhạc sinh viên',
            category_id=cat_culture.id,
            organizer_id=org_career.id,
            organizer_name='Trung tâm Tư vấn hướng nghiệp & Việc làm NEU',
            organizer_email=org_career.email,
            organizer_phone='024 3628 0280',
            location='Hội trường A2 & Khuôn viên NEU',
            target_audience='Sinh viên trong nước và lưu học sinh quốc tế',
            fee='Miễn phí',
            event_date=date(2025, 11, 14),
            start_time=time(8, 0),
            end_time=time(17, 0),
            registration_deadline=datetime(2025, 11, 13, 23, 59),
            max_seats=350,
            registered_seats=1,
            attended_seats=1,
            description="""Ngày hội kết nối văn hóa, trưng bày gian hàng truyền thống các quốc gia có lưu học sinh học tập tại NEU, tôn vinh tinh thần hội nhập quốc tế.""",
            handbook_name='Cam_nang_Van_hoa_NEU_2025.pdf',
            union_points_plus=5,
            union_points_minus=0,
            status='COMPLETED',
            is_featured=False
        )

        # EVENT 8: Hội nghị Nghiên cứu Khoa học Sinh viên Khoa CNTT 2026 (Năm học 2025-2026, Học kỳ Xuân 2026)
        e_2026_sci = Event(
            code='NEU-SCI-2026',
            title='Hội nghị Nghiên cứu Khoa học Sinh viên Khoa CNTT 2026',
            subtitle='Báo cáo công trình khoa học xuất sắc và giải pháp công nghệ ứng dụng thực tiễn',
            category_id=cat_academic.id,
            organizer_id=org_it.id,
            organizer_name='Khoa Công nghệ thông tin',
            organizer_email=org_it.email,
            organizer_phone='024 3628 0280',
            location='Phòng B101, Nhà A2',
            target_audience='Sinh viên nghiên cứu khoa học NEU',
            fee='Miễn phí',
            event_date=date(2026, 4, 10),
            start_time=time(8, 0),
            end_time=time(12, 0),
            registration_deadline=datetime(2026, 4, 9, 23, 59),
            max_seats=180,
            registered_seats=0,
            attended_seats=0,
            description="""Hội nghị thường niên vinh danh các đề tài nghiên cứu khoa học sinh viên xuất sắc về Trí tuệ nhân tạo, Phân tích dữ liệu lớn và Khoa học máy tính.""",
            handbook_name='Ky_yeu_NCKH_CNTT_2026.pdf',
            union_points_plus=10,
            union_points_minus=0,
            status='COMPLETED',
            is_featured=False
        )

        # EVENT 9: Lễ Khai giảng & Chào Tân sinh viên Khóa 66 NEU (Năm học 2024-2025, Học kỳ Thu 2024)
        e_2024_welcome = Event(
            code='NEU-K66-2024',
            title='Lễ Khai giảng & Chào Tân sinh viên Khóa 66 NEU',
            subtitle='Khởi đầu hành trình thanh xuân rực rỡ tại Đại học Kinh tế Quốc dân',
            category_id=cat_culture.id,
            organizer_id=org_career.id,
            organizer_name='Trung tâm Tư vấn hướng nghiệp & Việc làm NEU',
            organizer_email=org_career.email,
            organizer_phone='024 3628 0280',
            location='Hội trường A2',
            target_audience='Tân sinh viên Khóa 66 NEU',
            fee='Miễn phí',
            event_date=date(2024, 9, 20),
            start_time=time(7, 30),
            end_time=time(11, 30),
            registration_deadline=datetime(2024, 9, 19, 23, 59),
            max_seats=600,
            registered_seats=1,
            attended_seats=1,
            description="""Chương trình chào đón tân sinh viên Khóa 66 nhập học tại NEU với các hoạt động giao lưu thầy cô, giới thiệu các câu lạc bộ và hướng dẫn hòa nhập môi trường đại học.""",
            handbook_name='So_tay_Tan_sinh_vien_K66.pdf',
            union_points_plus=10,
            union_points_minus=0,
            status='COMPLETED',
            is_featured=False
        )

        # EVENT 10: NEU Junior Code Camp 2025 (Năm học 2024-2025, Học kỳ Xuân 2025)
        e_2025_codecamp = Event(
            code='NEU-CODECAMP-2025',
            title='NEU Junior Code Camp & Web Dev Workshop 2025',
            subtitle='Khóa đào tạo kỹ năng lập trình web và tư duy thuật toán cho sinh viên',
            category_id=cat_tech.id,
            organizer_id=org_it.id,
            organizer_name='Khoa Công nghệ thông tin',
            organizer_email=org_it.email,
            organizer_phone='024 3628 0280',
            location='Phòng B101, Nhà A2',
            target_audience='Sinh viên năm nhất và năm hai yêu thích lập trình',
            fee='Miễn phí',
            event_date=date(2025, 3, 15),
            start_time=time(13, 30),
            end_time=time(17, 30),
            registration_deadline=datetime(2025, 3, 14, 23, 59),
            max_seats=100,
            registered_seats=0,
            attended_seats=0,
            description="""Workshop thực hành xây dựng ứng dụng web cơ bản với HTML/CSS/JavaScript và Python Flask do giảng viên Khoa CNTT trực tiếp hướng dẫn.""",
            handbook_name='Tai_lieu_Code_Camp_2025.pdf',
            union_points_plus=5,
            union_points_minus=0,
            status='COMPLETED',
            is_featured=False
        )

        db.session.add_all([e_job, e_ai, e_skill, e_hack, e_spring_fest, e_fintech, e_marketing, e_case, e_volunteer, e_2025_cult, e_2026_sci, e_2024_welcome, e_2025_codecamp])
        db.session.commit()

        print("4. Creating Attendance Sessions & Registrations...")
        # 4.1 Live Session for NEU-JOB (Active all day today)
        session_job = AttendanceSession(
            event_id=e_job.id,
            session_pin=f'JOB{year}',
            qr_token=f'NEU:CHECKIN:NEU-JOB-{year}',
            valid_from=datetime.combine(today, time(0, 0)),
            valid_to=datetime.combine(today, time(23, 59)),
            is_active=True
        )
        db.session.add(session_job)

        # 4.2 Live Session for NEU-AI (Distinct PIN & QR Token)
        session_ai = AttendanceSession(
            event_id=e_ai.id,
            session_pin=f'AI{year}',
            qr_token=f'NEU:CHECKIN:NEU-AI-{year}',
            valid_from=datetime.combine(e_ai.event_date, time(0, 0)),
            valid_to=datetime.combine(e_ai.event_date, time(23, 59)),
            is_active=True
        )
        db.session.add(session_ai)

        # 4.3 Live Session for NEU-HACK (Distinct PIN & QR Token)
        session_hack = AttendanceSession(
            event_id=e_hack.id,
            session_pin=f'HACK{year}',
            qr_token=f'NEU:CHECKIN:NEU-HACK-{year}',
            valid_from=datetime.combine(e_hack.event_date, time(0, 0)),
            valid_to=datetime.combine(e_hack.event_date, time(23, 59)),
            is_active=True
        )
        db.session.add(session_hack)

        # 4.4 Past Session for NEU-SKILL (Completed event)
        session_skill = AttendanceSession(
            event_id=e_skill.id,
            session_pin=f'SKILL{year}',
            qr_token=f'NEU:CHECKIN:NEU-SKILL-{year}',
            valid_from=datetime.combine(e_skill.event_date, time(13, 30)),
            valid_to=datetime.combine(e_skill.event_date, time(17, 0)),
            is_active=False
        )
        db.session.add(session_skill)
        db.session.commit()

        # Student Thu registered for NEU-JOB (Not yet checked in, ready to test scan QR)
        reg_thu_job = Registration(
            ticket_code=f'NEU-JOB-{year}-0112',
            user_id=student_thu.id,
            event_id=e_job.id,
            registration_status='REGISTERED',
            attendance_status='NOT_YET',
            registered_at=datetime.now() - timedelta(hours=3)
        )
        db.session.add(reg_thu_job)

        # Student Thu attended NEU-SKILL
        reg_thu_skill = Registration(
            ticket_code=f'NEU-SKILL-{year}-01',
            user_id=student_thu.id,
            event_id=e_skill.id,
            registration_status='REGISTERED',
            attendance_status='ATTENDED',
            registered_at=datetime.combine(e_skill.event_date - timedelta(days=2), time(10, 0))
        )
        db.session.add(reg_thu_skill)
        db.session.commit()

        att_thu_skill = AttendanceRecord(
            session_id=session_skill.id,
            registration_id=reg_thu_skill.id,
            user_id=student_thu.id,
            checked_in_at=datetime.combine(e_skill.event_date, time(14, 5)),
            checkin_method='QR',
            status='ATTENDED'
        )
        db.session.add(att_thu_skill)

        # Student Anh attended NEU-SKILL (Has not submitted feedback yet)
        reg_anh_skill = Registration(
            ticket_code=f'NEU-SKILL-{year}-02',
            user_id=student_anh.id,
            event_id=e_skill.id,
            registration_status='REGISTERED',
            attendance_status='ATTENDED',
            registered_at=datetime.combine(e_skill.event_date - timedelta(days=1), time(14, 30))
        )
        db.session.add(reg_anh_skill)
        db.session.commit()

        att_anh_skill = AttendanceRecord(
            session_id=session_skill.id,
            registration_id=reg_anh_skill.id,
            user_id=student_anh.id,
            checked_in_at=datetime.combine(e_skill.event_date, time(14, 10)),
            checkin_method='QR',
            status='ATTENDED'
        )
        db.session.add(att_anh_skill)

        # Student Thu registrations across academic periods
        reg_thu_spring = Registration(
            ticket_code='NEU-SPRING-2027-0112',
            user_id=student_thu.id,
            event_id=e_spring_fest.id,
            registration_status='REGISTERED',
            attendance_status='NOT_YET',
            registered_at=datetime(2027, 2, 1, 9, 0)
        )
        reg_thu_cult = Registration(
            ticket_code='NEU-CULT-2025-0112',
            user_id=student_thu.id,
            event_id=e_2025_cult.id,
            registration_status='REGISTERED',
            attendance_status='ATTENDED',
            registered_at=datetime(2025, 11, 1, 8, 30)
        )
        reg_thu_welcome = Registration(
            ticket_code='NEU-K66-2024-0112',
            user_id=student_thu.id,
            event_id=e_2024_welcome.id,
            registration_status='REGISTERED',
            attendance_status='ATTENDED',
            registered_at=datetime(2024, 9, 10, 14, 0)
        )
        db.session.add_all([reg_thu_spring, reg_thu_cult, reg_thu_welcome])
        db.session.commit()

        print("5. Creating Sample Feedback...")
        # Feedback submitted by Student Thu for NEU-SKILL
        fb_thu = Feedback(
            event_id=e_skill.id,
            user_id=student_thu.id,
            rating_stars=5,
            rating_content=5,
            rating_organization=5,
            rating_speaker=5,
            rating_venue=4,
            comment="Buổi tọa đàm vô cùng thiết thực! Diễn giả hướng dẫn tận tình từng đề mục trong CV và chia sẻ các lỗi sai sinh viên thường mắc phải.",
            is_anonymous=False,
            created_at=datetime.now() - timedelta(hours=1, minutes=20)
        )
        db.session.add(fb_thu)

        print("6. Creating Sample Approval Log...")
        approval_job = ApprovalLog(
            event_id=e_job.id,
            manager_id=manager.id,
            action='APPROVE',
            note='Kế hoạch tổ chức hoàn thiện, địa điểm Hội trường A2 đã được xác nhận không trùng lịch.',
            created_at=datetime.now() - timedelta(days=4)
        )
        db.session.add(approval_job)

        db.session.commit()
        print("[SUCCESS] Data seeding completed successfully! Database is ready with 5 users and 10 events across academic periods.")

if __name__ == '__main__':
    from app import app
    seed_database(app)
