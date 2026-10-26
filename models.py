"""
Database Models for NEU Events Management System
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False) # MSSV or Email prefix
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='STUDENT') # STUDENT, ORGANIZER, MANAGER
    department = db.Column(db.String(150), nullable=True) # E.g., Khoa Công nghệ thông tin, Phòng CTCT & QLSV
    student_id = db.Column(db.String(20), nullable=True) # MSSV
    phone = db.Column(db.String(20), nullable=True)
    avatar_initials = db.Column(db.String(5), default='NEU')
    is_password_set = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    @property
    def display_email(self):
        if self.role == 'STUDENT' and self.student_id:
            return f"{self.student_id}@st.neu.edu.vn"
        return self.email

    # Relationships
    registrations = db.relationship('Registration', backref='user', lazy=True)
    organized_events = db.relationship('Event', backref='organizer', lazy=True)
    feedbacks = db.relationship('Feedback', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')
        self.is_password_set = True

    def check_password(self, password):
        if not self.password_hash or self.password_hash.startswith('!UNSET_'):
            return False
        if self.role == 'STUDENT' and not getattr(self, 'is_password_set', False):
            return False
        return check_password_hash(self.password_hash, password)


class EventCategory(db.Model):
    __tablename__ = 'event_categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False) # Nghề nghiệp, Học thuật, Hội thảo, Cộng đồng, Văn hóa
    color_class = db.Column(db.String(30), default='blue') # for badge styling
    events = db.relationship('Event', backref='category', lazy=True)


class Event(db.Model):
    __tablename__ = 'events'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(30), unique=True, nullable=False) # E.g., NEU-JOB-2026, NEU-AI-2026
    title = db.Column(db.String(255), nullable=False)
    subtitle = db.Column(db.String(255), nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey('event_categories.id'), nullable=False)
    organizer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    organizer_name = db.Column(db.String(150), nullable=False) # E.g., Trung tâm Tư vấn hướng nghiệp & Việc làm
    organizer_email = db.Column(db.String(100), default='events@neu.edu.vn')
    organizer_phone = db.Column(db.String(50), default='024 3628 0280')

    location = db.Column(db.String(200), nullable=False) # E.g., Hội trường A2 & sảnh nhà A1
    target_audience = db.Column(db.String(150), default='Sinh viên & cựu sinh viên NEU')
    fee = db.Column(db.String(50), default='Miễn phí')

    event_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    registration_deadline = db.Column(db.DateTime, nullable=False)

    max_seats = db.Column(db.Integer, nullable=False, default=200)
    registered_seats = db.Column(db.Integer, default=0)
    attended_seats = db.Column(db.Integer, default=0)

    description = db.Column(db.Text, nullable=False)
    agenda_json = db.Column(db.Text, nullable=True) # JSON timeline of agenda
    checklist_json = db.Column(db.Text, nullable=True) # JSON items to prepare
    handbook_name = db.Column(db.String(150), default='Cẩm nang sự kiện NEU.pdf')
    handbook_url = db.Column(db.String(500), nullable=True) # URL / file path của ấn phẩm chương trình
    union_points_plus = db.Column(db.Integer, default=5, nullable=False) # Điểm cộng Đoàn khi tham dự
    union_points_minus = db.Column(db.Integer, default=0, nullable=False) # Điểm phạt Đoàn nếu vắng mặt
    sponsor_benefits = db.Column(db.Text, nullable=True) # Quyền lợi, quà tặng, voucher khóa học từ nhà tài trợ
    cover_image_url = db.Column(db.String(500), nullable=True)

    status = db.Column(db.String(20), default='APPROVED') # DRAFT, PENDING, APPROVED, REJECTED, CANCELLED, COMPLETED
    is_featured = db.Column(db.Boolean, default=False)
    cancel_reason = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)

    # Relationships
    registrations = db.relationship('Registration', backref='event', lazy=True, cascade="all, delete-orphan")
    attendance_sessions = db.relationship('AttendanceSession', backref='event', lazy=True, cascade="all, delete-orphan")
    feedbacks = db.relationship('Feedback', backref='event', lazy=True, cascade="all, delete-orphan")
    approval_logs = db.relationship('ApprovalLog', backref='event', lazy=True, cascade="all, delete-orphan")

    @property
    def remaining_seats(self):
        return max(0, self.max_seats - self.registered_seats)

    @property
    def academic_year(self):
        if not self.event_date:
            return ""
        if self.event_date.month >= 8:
            return f"{self.event_date.year}-{self.event_date.year + 1}"
        else:
            return f"{self.event_date.year - 1}-{self.event_date.year}"

    @property
    def semester(self):
        if not self.event_date:
            return ""
        m, y = self.event_date.month, self.event_date.year
        if m >= 8:
            return f"Học kỳ Thu {y}"
        elif m <= 5:
            return f"Học kỳ Xuân {y}"
        else:
            return f"Học kỳ Hè {y}"

    @property
    def sponsor_benefits_list(self):
        if not self.sponsor_benefits:
            return []
        lines = []
        for line in self.sponsor_benefits.split('\n'):
            cleaned = line.strip().lstrip('-•*+ ').strip()
            if cleaned:
                lines.append(cleaned)
        return lines

    @property
    def is_registration_open(self):
        if self.status != 'APPROVED':
            return False
        return (datetime.now() <= self.registration_deadline) and (self.remaining_seats > 0)

    @property
    def attendance_rate(self):
        if self.registered_seats > 0:
            return round((self.attended_seats / self.registered_seats) * 100, 1)
        return 0.0

    @property
    def average_rating(self):
        valid_ratings = [f.rating_stars for f in self.feedbacks if f.rating_stars is not None]
        if valid_ratings:
            return round(sum(valid_ratings) / len(valid_ratings), 1)
        return None

    @property
    def agenda_items(self):
        import json
        if self.agenda_json:
            try:
                items = json.loads(self.agenda_json)
                if isinstance(items, list) and len(items) > 0:
                    return items
            except Exception:
                pass
        return [
            {"time": f"{self.start_time.strftime('%H:%M')}–{self.end_time.strftime('%H:%M')}", "title": "Chương trình sự kiện chính", "venue": self.location}
        ]

    @property
    def is_completed(self):
        from datetime import date
        return self.status == 'COMPLETED' or (self.event_date is not None and self.event_date < date.today())

    @property
    def current_status_label(self):
        from datetime import date
        today = date.today()
        if self.status == 'CANCELLED':
            return 'Đã hủy'
        if self.status == 'REJECTED':
            return 'Từ chối duyệt'
        if self.status == 'PENDING':
            return 'Chờ duyệt'
        if self.status == 'COMPLETED' or self.event_date < today:
            return 'Đã kết thúc'
        if self.event_date == today and self.status == 'APPROVED':
            return 'Đang diễn ra'
        if self.status == 'APPROVED':
            return 'Sắp diễn ra'
        return self.status

    @property
    def current_status_badge(self):
        label = self.current_status_label
        if label == 'Đang diễn ra':
            return {'label': label, 'class': 'bg-emerald-500/90 text-white animate-pulse', 'dot': 'bg-white'}
        elif label == 'Đã kết thúc':
            return {'label': label, 'class': 'bg-slate-600/85 text-white', 'dot': 'bg-slate-300'}
        elif label in ['Đã hủy', 'Từ chối duyệt']:
            return {'label': label, 'class': 'bg-rose-500/85 text-white', 'dot': 'bg-white'}
        elif label == 'Chờ duyệt':
            return {'label': label, 'class': 'bg-amber-500/85 text-white', 'dot': 'bg-white'}
        else: # Sắp diễn ra
            return {'label': label, 'class': 'bg-blue-600/85 text-white', 'dot': 'bg-white'}


class Registration(db.Model):
    __tablename__ = 'registrations'

    id = db.Column(db.Integer, primary_key=True)
    ticket_code = db.Column(db.String(40), unique=True, nullable=False) # E.g., NEU-AI-0123
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    registration_status = db.Column(db.String(20), default='REGISTERED') # REGISTERED, CANCELLED
    attendance_status = db.Column(db.String(20), default='NOT_YET') # NOT_YET, ATTENDED, ABSENT, NOT_APPLICABLE
    registered_at = db.Column(db.DateTime, default=datetime.now)

    attendance_record = db.relationship('AttendanceRecord', backref='registration', uselist=False, lazy=True)


class AttendanceSession(db.Model):
    __tablename__ = 'attendance_sessions'

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    session_pin = db.Column(db.String(10), nullable=False) # E.g., AI1210
    qr_token = db.Column(db.String(100), nullable=False)
    valid_from = db.Column(db.DateTime, nullable=False)
    valid_to = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)

    records = db.relationship('AttendanceRecord', backref='session', lazy=True)


class AttendanceRecord(db.Model):
    __tablename__ = 'attendance_records'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('attendance_sessions.id'), nullable=False)
    registration_id = db.Column(db.Integer, db.ForeignKey('registrations.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    checked_in_at = db.Column(db.DateTime, default=datetime.now)
    checkin_method = db.Column(db.String(20), default='PIN') # PIN, QR, MANUAL
    status = db.Column(db.String(20), default='ATTENDED') # ATTENDED, ABSENT


class Feedback(db.Model):
    __tablename__ = 'feedbacks'

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    rating_stars = db.Column(db.Integer, nullable=False) # 1 to 5
    rating_content = db.Column(db.Integer, default=5) # 1 to 5
    rating_organization = db.Column(db.Integer, default=5)
    rating_speaker = db.Column(db.Integer, default=5)
    rating_venue = db.Column(db.Integer, default=5)
    comment = db.Column(db.Text, nullable=True)
    is_anonymous = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)


class ApprovalLog(db.Model):
    __tablename__ = 'approval_logs'

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    manager_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String(30), nullable=False) # APPROVE, REJECT, REQUEST_CHANGE
    note = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
