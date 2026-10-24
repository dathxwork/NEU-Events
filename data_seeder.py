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

        # 1.3 Organizer 2 (Viện CNTT & Kinh tế số)
        org_it = User(
            username='it@neu.edu.vn',
            email='it@neu.edu.vn',
            full_name='Viện CNTT & Kinh tế số',
            role='ORGANIZER',
            department='Viện Công nghệ thông tin & Kinh tế số',
            phone='024 3628 0280 • 8011',
            avatar_initials='IT'
        )
        org_it.set_password('123')

        # 1.4 Student 1 (Nguyễn Thị Thu - Viện CNTT & Kinh tế số)
        student_thu = User(
            username='11244035',
            email='thunguyen@st.neu.edu.vn',
            full_name='Nguyễn Thị Thu',
            role='STUDENT',
            department='Viện CNTT & Kinh tế số',
            student_id='11244035',
            phone='0987123456',
            avatar_initials='TT'
        )
        student_thu.set_password('123')

        # 1.5 Student 2 (Nguyễn Minh Anh - Khoa Marketing)
        student_anh = User(
            username='11240123',
            email='minhanh@st.neu.edu.vn',
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
            organizer_name='Viện Công nghệ thông tin & Kinh tế số',
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
            description="""Hội thảo do Viện CNTT & Kinh tế số tổ chức nhằm giúp sinh viên cập nhật các đột phá công nghệ mới nhất về Trí tuệ nhân tạo, ứng dụng AI trong phân tích dữ liệu kinh doanh và định hướng nghề nghiệp thời đại số.""",
            agenda_json=json.dumps([
                {"time": "09:00–09:20", "title": "Khai mạc hội thảo", "venue": "Hội trường B1"},
                {"time": "09:20–10:30", "title": "Chuyên đề: Generative AI trong quản trị doanh nghiệp", "venue": "Hội trường B1"},
                {"time": "10:30–11:30", "title": "Hỏi đáp (Q&A) cùng chuyên gia", "venue": "Hội trường B1"}
            ]),
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
            organizer_name='Viện Công nghệ thông tin & Kinh tế số',
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
            status='APPROVED',
            is_featured=True
        )

        db.session.add_all([e_job, e_ai, e_skill, e_hack])
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
            created_at=datetime.combine(e_skill.event_date, time(17, 15))
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
        print("[SUCCESS] Data seeding completed successfully! Database is ready with 5 users and 4 events.")

if __name__ == '__main__':
    from app import app
    seed_database(app)
