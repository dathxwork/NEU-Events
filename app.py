"""
NEU Events - Cổng Quản lý và Tổ chức Sự kiện Đại học Kinh tế Quốc dân
Main Flask Web Application
"""
import os
import random
from datetime import datetime, date, time, timedelta
import calendar
from io import StringIO, BytesIO
import csv
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, jsonify, Response, session
)
from flask_login import (
    LoginManager, login_user, logout_user,
    login_required, current_user
)

from models import (
    db, User, EventCategory, Event, Registration,
    AttendanceSession, AttendanceRecord, Feedback, ApprovalLog
)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'neu-events-super-secret-key-2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///neu_events.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads', 'publications')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Vui lòng đăng nhập để tiếp tục.'
login_manager.login_message_category = 'warning'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.after_request
def add_cache_control_headers(response):
    if 'text/html' in response.headers.get('Content-Type', ''):
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response

# Context Processors for Templates
def get_period_date_range(academic_year, semester=None):
    """
    Returns (start_date, end_date) for a given academic year and optional semester.
    academic_year: '2026-2027', '2025-2026', 'ALL', etc.
    semester: 'Học kỳ Thu 2026', 'Học kỳ Xuân 2027', 'Học kỳ Hè 2027', 'ALL', etc.
    """
    start_date = None
    end_date = None

    if academic_year and academic_year != 'ALL':
        try:
            parts = str(academic_year).strip().split('-')
            if len(parts) == 2:
                y1, y2 = int(parts[0]), int(parts[1])
                start_date = date(y1, 8, 1)
                end_date = date(y2, 7, 31)
        except Exception:
            pass

    if semester and semester not in ['ALL', 'Tất cả học kỳ']:
        import re
        m = re.search(r'(\d{4})', str(semester))
        if m:
            sem_year = int(m.group(1))
            if 'Thu' in semester:
                return date(sem_year, 8, 1), date(sem_year, 12, 31)
            elif 'Xuân' in semester:
                return date(sem_year, 1, 1), date(sem_year, 5, 31)
            elif 'Hè' in semester:
                return date(sem_year, 6, 1), date(sem_year, 7, 31)

    return start_date, end_date

def get_user_notifications(user):
    if not user or not getattr(user, 'is_authenticated', False):
        return []

    notifications = []
    now_dt = datetime.now()
    now_time_str = now_dt.strftime('%H:%M %d/%m/%Y')

    def format_event_time(ev):
        if not ev:
            return ""
        date_str = ev.event_date.strftime("%d/%m/%Y") if ev.event_date else ""
        if ev.start_time and ev.end_time:
            time_str = f"{ev.start_time.strftime('%H:%M')} - {ev.end_time.strftime('%H:%M')}"
        elif ev.start_time:
            time_str = ev.start_time.strftime('%H:%M')
        else:
            time_str = ""
        
        if time_str and date_str:
            return f"{time_str}, {date_str}"
        return time_str or date_str or "Sắp diễn ra"
    
    if user.role == 'STUDENT':
        # 1. Registered events & tickets
        regs = Registration.query.filter_by(user_id=user.id, registration_status='REGISTERED')\
                                 .order_by(Registration.registered_at.desc()).limit(3).all()
        for reg in regs:
            ev = reg.event
            if not ev:
                continue
            points = ev.union_points_plus or 5
            ev_time = format_event_time(ev)
            reg_time = reg.registered_at.strftime('%H:%M %d/%m/%Y') if reg.registered_at else now_time_str

            if reg.attendance_status == 'ATTENDED':
                checkin_time = reg_time
                if hasattr(reg, 'attendance_record') and reg.attendance_record and reg.attendance_record.checked_in_at:
                    checkin_time = reg.attendance_record.checked_in_at.strftime('%H:%M %d/%m/%Y')
                notifications.append({
                    'id': f'notif_checkin_{reg.id}',
                    'title': 'Điểm danh & Nhận Điểm Đoàn thành công',
                    'message': f'Bạn đã được ghi nhận tham dự sự kiện <strong>{ev.title}</strong> vào lúc <strong>{checkin_time}</strong>.<br><span class="inline-flex items-center gap-1 mt-1 text-[11px] text-slate-600"><i class="fa-regular fa-calendar-check text-[10px] text-emerald-600"></i>Thời gian sự kiện: <strong>{ev_time}</strong></span><br><span class="inline-flex items-center gap-1 text-[11px] text-emerald-600 font-semibold mt-0.5"><i class="fa-solid fa-award text-[10px]"></i>Cộng +{points} Điểm Đoàn</span>',
                    'time': checkin_time,
                    'icon': 'fa-solid fa-award',
                    'icon_color': 'text-emerald-600',
                    'icon_bg': 'bg-emerald-50 border-emerald-100',
                    'link': f'/events/{ev.id}',
                    'unread': True,
                    'tag': 'Điểm Đoàn'
                })
            else:
                notifications.append({
                    'id': f'notif_reg_{reg.id}',
                    'title': 'Vé tham gia sự kiện đã sẵn sàng',
                    'message': f'Vé điện tử sự kiện <strong>{ev.title}</strong> đã sẵn sàng.<br><span class="inline-flex items-center gap-1 mt-1 text-[11px] text-slate-700 font-medium"><i class="fa-regular fa-clock text-[10px] text-blue-600"></i>Thời gian: <strong>{ev_time}</strong></span><br><span class="inline-flex items-center gap-1 text-[11px] text-slate-700 font-medium"><i class="fa-solid fa-location-dot text-[10px] text-rose-500"></i>Địa điểm: {ev.location}</span><br><span class="inline-flex items-center gap-1 mt-0.5 text-[11px] text-slate-600">Mã vé: <code class="bg-slate-100 text-neu-700 font-mono font-bold px-1.5 py-0.2 rounded text-[11px]">{reg.ticket_code}</code></span>',
                    'time': reg_time,
                    'icon': 'fa-solid fa-ticket',
                    'icon_color': 'text-blue-600',
                    'icon_bg': 'bg-blue-50 border-blue-100',
                    'link': f'/events/{ev.id}',
                    'unread': True,
                    'tag': 'Vé điện tử'
                })
        
        # 2. Upcoming events open for registration
        open_events = Event.query.filter_by(status='APPROVED').order_by(Event.id.desc()).limit(2).all()
        for ev in open_events:
            is_reg = any(r.user_id == user.id for r in ev.registrations if r.registration_status == 'REGISTERED')
            if not is_reg:
                ev_time = format_event_time(ev)
                ev_created = ev.created_at.strftime('%H:%M %d/%m/%Y') if ev.created_at else now_time_str
                deadline_str = ev.registration_deadline.strftime('%H:%M %d/%m/%Y') if ev.registration_deadline else ''
                deadline_html = f'<br><span class="inline-flex items-center gap-1 text-[11px] text-rose-600 font-medium"><i class="fa-solid fa-hourglass-half text-[10px]"></i>Hạn đăng ký: <strong>{deadline_str}</strong></span>' if deadline_str else ''
                notifications.append({
                    'id': f'notif_open_ev_{ev.id}',
                    'title': 'Sự kiện mới mở cổng đăng ký',
                    'message': f'Sự kiện <strong>{ev.title}</strong> vừa mở đăng ký.<br><span class="inline-flex items-center gap-1 mt-1 text-[11px] text-slate-700 font-medium"><i class="fa-regular fa-clock text-[10px] text-amber-600"></i>Thời gian: <strong>{ev_time}</strong></span><br><span class="inline-flex items-center gap-1 text-[11px] text-slate-700 font-medium"><i class="fa-solid fa-location-dot text-[10px] text-rose-500"></i>Địa điểm: {ev.location}</span>{deadline_html}',
                    'time': ev_created,
                    'icon': 'fa-solid fa-calendar-plus',
                    'icon_color': 'text-amber-600',
                    'icon_bg': 'bg-amber-50 border-amber-100',
                    'link': f'/events/{ev.id}',
                    'unread': True,
                    'tag': 'Đăng ký mới'
                })
                break
        
        # 3. Always include general student system update
        notifications.append({
            'id': 'notif_system_welcome',
            'title': 'Cổng thông tin sự kiện NEU Events',
            'message': f'Đại học Kinh tế Quốc dân đồng hành cùng sinh viên trong mọi hoạt động học thuật, kỹ năng và kết nối doanh nghiệp.<br><span class="inline-flex items-center gap-1 mt-1 text-[11px] text-slate-500"><i class="fa-regular fa-clock text-[10px] text-neu-600"></i>Thời gian cập nhật: <strong>{now_time_str}</strong></span>',
            'time': now_time_str,
            'icon': 'fa-solid fa-bell',
            'icon_color': 'text-neu-700',
            'icon_bg': 'bg-neu-50 border-neu-100',
            'link': '/events',
            'unread': False,
            'tag': 'Hệ thống'
        })

    elif user.role == 'ORGANIZER':
        # Organizer notifications
        org_events = Event.query.filter_by(organizer_id=user.id).order_by(Event.id.desc()).limit(3).all()
        for ev in org_events:
            ev_time = format_event_time(ev)
            ev_created = ev.created_at.strftime('%H:%M %d/%m/%Y') if ev.created_at else now_time_str
            if ev.status == 'APPROVED':
                notifications.append({
                    'id': f'notif_org_approved_{ev.id}',
                    'title': 'Sự kiện đã được phê duyệt',
                    'message': f'Sự kiện <strong>{ev.title}</strong> đã được Đơn vị Quản lý phê duyệt mở đăng ký chính thức ra toàn trường.<br><span class="inline-flex items-center gap-1 mt-1 text-[11px] text-slate-700 font-medium"><i class="fa-regular fa-clock text-[10px] text-emerald-600"></i>Thời gian tổ chức: <strong>{ev_time}</strong></span><br><span class="inline-flex items-center gap-1 text-[11px] text-slate-700 font-medium"><i class="fa-solid fa-location-dot text-[10px] text-rose-500"></i>Địa điểm: {ev.location}</span>',
                    'time': ev_created,
                    'icon': 'fa-solid fa-circle-check',
                    'icon_color': 'text-emerald-600',
                    'icon_bg': 'bg-emerald-50 border-emerald-100',
                    'link': f'/events/{ev.id}',
                    'unread': True,
                    'tag': 'Phê duyệt'
                })
            elif ev.status == 'PENDING':
                notifications.append({
                    'id': f'notif_org_pending_{ev.id}',
                    'title': 'Hồ sơ sự kiện đang chờ xét duyệt',
                    'message': f'Hồ sơ sự kiện <strong>{ev.title}</strong> đang trong quá trình thẩm định nội dung và định mức Điểm Đoàn.<br><span class="inline-flex items-center gap-1 mt-1 text-[11px] text-slate-700 font-medium"><i class="fa-regular fa-clock text-[10px] text-amber-600"></i>Thời gian dự kiến: <strong>{ev_time}</strong></span>',
                    'time': ev_created,
                    'icon': 'fa-solid fa-clock-rotate-left',
                    'icon_color': 'text-amber-600',
                    'icon_bg': 'bg-amber-50 border-amber-100',
                    'link': f'/events/{ev.id}',
                    'unread': True,
                    'tag': 'Đang thẩm định'
                })
            
            # Registration progress
            max_s = ev.max_seats or 100
            reg_s = ev.registered_seats or len([r for r in ev.registrations if r.registration_status == 'REGISTERED'])
            pct = int((reg_s / max_s) * 100) if max_s else 0
            notifications.append({
                'id': f'notif_org_prog_{ev.id}',
                'title': f'Tiến độ đăng ký ({reg_s}/{max_s} chỗ)',
                'message': f'Sự kiện <strong>{ev.title}</strong> hiện đã đạt {pct}% tỷ lệ lấp đầy hội trường.<br><span class="inline-flex items-center gap-1 mt-1 text-[11px] text-slate-700 font-medium"><i class="fa-regular fa-clock text-[10px] text-blue-600"></i>Thời gian sự kiện: <strong>{ev_time}</strong></span>',
                'time': now_time_str,
                'icon': 'fa-solid fa-chart-line',
                'icon_color': 'text-blue-600',
                'icon_bg': 'bg-blue-50 border-blue-100',
                'link': f'/events/{ev.id}',
                'unread': False,
                'tag': 'Thống kê'
            })
        
        notifications.append({
            'id': 'notif_org_checkin_guide',
            'title': 'Sẵn sàng mở phiên điểm danh QR & PIN',
            'message': f'Sử dụng công cụ Điểm danh tại sự kiện để quét mã QR vé sinh viên và cấp phát Điểm Đoàn công bằng, tự động.<br><span class="inline-flex items-center gap-1 mt-1 text-[11px] text-slate-500"><i class="fa-regular fa-clock text-[10px] text-indigo-600"></i>Thời gian hệ thống: <strong>{now_time_str}</strong></span>',
            'time': now_time_str,
            'icon': 'fa-solid fa-qrcode',
            'icon_color': 'text-indigo-600',
            'icon_bg': 'bg-indigo-50 border-indigo-100',
            'link': '/checkin',
            'unread': False,
            'tag': 'Điểm danh'
        })

    elif user.role == 'MANAGER':
        # Manager notifications
        pending_list = Event.query.filter_by(status='PENDING').all()
        if pending_list:
            notifications.append({
                'id': 'notif_mgr_pending_alert',
                'title': f'Có {len(pending_list)} sự kiện chờ phê duyệt',
                'message': f'Các Câu lạc bộ và Ban tổ chức đã nộp <strong>{len(pending_list)} hồ sơ sự kiện mới</strong> cần thẩm định.<br><span class="inline-flex items-center gap-1 mt-1 text-[11px] text-purple-700 font-medium"><i class="fa-regular fa-clock text-[10px]"></i>Thời gian ghi nhận: <strong>{now_time_str}</strong></span>',
                'time': now_time_str,
                'icon': 'fa-solid fa-file-circle-exclamation',
                'icon_color': 'text-purple-600',
                'icon_bg': 'bg-purple-50 border-purple-100',
                'link': '/moderation',
                'unread': True,
                'tag': 'Kiểm duyệt'
            })
        
        recent_approved = Event.query.filter_by(status='APPROVED').order_by(Event.id.desc()).limit(2).all()
        for ev in recent_approved:
            ev_time = format_event_time(ev)
            ev_created = ev.created_at.strftime('%H:%M %d/%m/%Y') if ev.created_at else now_time_str
            notifications.append({
                'id': f'notif_mgr_app_{ev.id}',
                'title': 'Sự kiện phong trào toàn trường',
                'message': f'Chương trình <strong>{ev.title}</strong> do {ev.organizer_name or "BTC"} điều phối đang mở công khai.<br><span class="inline-flex items-center gap-1 mt-1 text-[11px] text-slate-700 font-medium"><i class="fa-regular fa-clock text-[10px] text-blue-600"></i>Thời gian diễn ra: <strong>{ev_time}</strong> tại {ev.location}</span>',
                'time': ev_created,
                'icon': 'fa-solid fa-shield-check',
                'icon_color': 'text-blue-600',
                'icon_bg': 'bg-blue-50 border-blue-100',
                'link': f'/events/{ev.id}',
                'unread': False,
                'tag': 'Cấp trường'
            })
            break
        
        notifications.append({
            'id': 'notif_mgr_analytics_ready',
            'title': 'Báo cáo KPI hoạt động toàn trường',
            'message': f'Dữ liệu phân tích thống kê lượt sinh viên tham dự và định mức Điểm Đoàn toàn học kỳ đã được cập nhật.<br><span class="inline-flex items-center gap-1 mt-1 text-[11px] text-slate-500"><i class="fa-regular fa-clock text-[10px] text-emerald-600"></i>Thời gian cập nhật: <strong>{now_time_str}</strong></span>',
            'time': now_time_str,
            'icon': 'fa-solid fa-chart-pie',
            'icon_color': 'text-emerald-600',
            'icon_bg': 'bg-emerald-50 border-emerald-100',
            'link': '/analytics',
            'unread': False,
            'tag': 'Báo cáo'
        })
        
    return notifications


@app.context_processor
def inject_global_data():
    today = date.today()
    now = datetime.now()
    def get_pending_count():
        return Event.query.filter_by(status='PENDING').count()

    def is_reviewed(event_id):
        if not current_user.is_authenticated:
            return False
        return Feedback.query.filter_by(event_id=event_id, user_id=current_user.id).first() is not None

    default_year = f"{today.year}-{today.year + 1}" if today.month >= 8 else f"{today.year - 1}-{today.year}"
    current_academic_year = request.args.get('academic_year') or session.get('academic_year') or default_year
    current_semester = request.args.get('semester') or session.get('semester') or 'ALL'

    user_notifs = get_user_notifications(current_user)
    user_unread_notif_count = sum(1 for n in user_notifs if n.get('unread'))

    return dict(
        today=today,
        now=now,
        current_year=today.year,
        current_month_year=today.strftime('%m/%Y'),
        current_date_str=today.strftime('%d/%m/%Y'),
        get_pending_count=get_pending_count,
        is_reviewed=is_reviewed,
        current_academic_year=current_academic_year,
        current_semester=current_semester,
        user_notifications=user_notifs,
        unread_notif_count=user_unread_notif_count
    )

@app.route('/api/set-period', methods=['POST'])
def api_set_period():
    data = request.get_json() or {}
    year = data.get('academic_year')
    sem = data.get('semester')
    if year:
        session['academic_year'] = year
    if sem:
        session['semester'] = sem
    return jsonify({
        'success': True,
        'academic_year': session.get('academic_year'),
        'semester': session.get('semester')
    })

@app.route('/api/notifications', methods=['GET'])
@login_required
def api_notifications():
    notifs = get_user_notifications(current_user)
    unread_count = sum(1 for n in notifs if n.get('unread'))
    return jsonify({
        'success': True,
        'notifications': notifs,
        'unread_count': unread_count
    })

@app.route('/api/notifications/read-all', methods=['POST'])
@login_required
def api_notifications_read_all():
    return jsonify({'success': True, 'unread_count': 0})

@app.route('/api/notifications/clear', methods=['POST'])
@login_required
def api_notifications_clear():
    return jsonify({'success': True, 'notifications': [], 'unread_count': 0})

# ----------------- AUTHENTICATION -----------------

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('events'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('events'))

    login_id = ''
    if request.method == 'POST':
        login_id = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        remember = bool(request.form.get('remember'))

        # Find user by MSSV, username, or email
        user = User.query.filter(
            (User.username == login_id) |
            (User.email == login_id) |
            (User.student_id == login_id)
        ).first()

        if not user:
            if login_id.isdigit():
                flash(f'Mã sinh viên "{login_id}" không tồn tại trong danh sách sinh viên Đại học Kinh tế Quốc dân. Vui lòng kiểm tra lại chính xác MSSV.', 'error')
            else:
                flash(f'Tài khoản "{login_id}" không tồn tại trong hệ thống NEU Events.', 'error')
            return render_template('login.html', login_id=login_id)

        if not user.check_password(password):
            if user.role == 'STUDENT' and not getattr(user, 'is_password_set', False):
                flash('Mã sinh viên này chưa thiết lập mật khẩu cá nhân. Vui lòng bấm "Tự đặt mật khẩu" bên dưới để kích hoạt tài khoản của bạn.', 'warning')
            else:
                flash('Mật khẩu không chính xác. Sinh viên có thể sử dụng chức năng "Tự đặt mật khẩu" bên dưới để kích hoạt hoặc đặt lại mật khẩu.', 'error')
            return render_template('login.html', login_id=login_id)

        login_user(user, remember=remember)
        if user.role == 'MANAGER':
            flash('Chào mừng Đơn vị quản lý đã đăng nhập thành công!', 'success')
        elif user.role == 'ORGANIZER':
            flash(f'Chào mừng Ban tổ chức ({user.full_name}) đã đăng nhập thành công!', 'success')
        else:
            flash(f'Chào mừng sinh viên {user.full_name} đã đăng nhập thành công!', 'success')
        next_page = request.args.get('next')
        return redirect(next_page or url_for('events'))

    return render_template('login.html', login_id=login_id)

@app.route('/api/check-student', methods=['GET'])
def check_student():
    """Verify if MSSV belongs to an active NEU student"""
    student_id = request.args.get('student_id', '').strip()
    if not student_id:
        return jsonify({'exists': False, 'message': 'Vui lòng cung cấp mã sinh viên.'})

    user = User.query.filter(
        (User.student_id == student_id) |
        (User.username == student_id)
    ).first()

    if user and user.role == 'STUDENT':
        return jsonify({
            'exists': True,
            'full_name': user.full_name,
            'department': user.department or 'Đại học Kinh tế Quốc dân',
            'student_id': user.student_id or user.username,
            'email': user.email
        })
    else:
        return jsonify({
            'exists': False,
            'message': f'Mã sinh viên "{student_id}" không tồn tại trong danh sách sinh viên Đại học Kinh tế Quốc dân.'
        })

@app.route('/api/ticket/<ticket_code>', methods=['GET'])
def api_get_ticket(ticket_code):
    """API endpoint to get and verify ticket information by ticket_code"""
    ticket_code = (ticket_code or '').strip()
    reg = Registration.query.filter_by(ticket_code=ticket_code).first()
    if not reg:
        return jsonify({'exists': False, 'message': 'Mã vé không tồn tại trong hệ thống NEU Events.'}), 404

    return jsonify({
        'exists': True,
        'ticket_code': reg.ticket_code,
        'student_id': reg.user.student_id or reg.user.username,
        'student_name': reg.user.full_name,
        'department': reg.user.department or 'Đại học Kinh tế Quốc dân',
        'event_id': reg.event.id,
        'event_title': reg.event.title,
        'event_code': reg.event.code,
        'event_date': reg.event.event_date.strftime('%d/%m/%Y'),
        'event_time': f"{reg.event.start_time.strftime('%H:%M')} – {reg.event.end_time.strftime('%H:%M')}",
        'location': reg.event.location,
        'registration_status': reg.registration_status,
        'attendance_status': reg.attendance_status
    })

@app.route('/set-password', methods=['POST'])
def set_password():
    """Allow NEU students to set/reset their own password without Microsoft SSO integration"""
    student_id = request.form.get('student_id', '').strip()
    new_password = request.form.get('new_password', '').strip()
    confirm_password = request.form.get('confirm_password', '').strip()
    remember = bool(request.form.get('remember'))

    user = User.query.filter(
        (User.student_id == student_id) |
        (User.username == student_id)
    ).first()

    if not user or user.role != 'STUDENT':
        flash('Mã sinh viên không hợp lệ hoặc không thuộc danh sách sinh viên NEU.', 'error')
        return redirect(url_for('login'))

    if len(new_password) < 6:
        flash('Mật khẩu phải có độ dài tối thiểu 6 ký tự để bảo mật tài khoản.', 'error')
        return redirect(url_for('login'))

    if new_password != confirm_password:
        flash('Mật khẩu xác nhận không khớp. Vui lòng nhập lại chính xác.', 'error')
        return redirect(url_for('login'))

    user.set_password(new_password)
    db.session.commit()

    login_user(user, remember=remember)
    flash(f'Thiết lập mật khẩu thành công! Chào mừng sinh viên {user.full_name} ({user.student_id}).', 'success')
    return redirect(url_for('events'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Bạn đã đăng xuất an toàn khỏi hệ thống NEU Events.', 'info')
    return redirect(url_for('login'))

@app.route('/switch-role/<role>')
@login_required
def switch_role(role):
    """Disable public role switching for security"""
    flash('Chức năng chuyển đổi nhanh đã bị vô hiệu hóa vì lý do bảo mật. Vui lòng đăng nhập đúng tài khoản được cấp.', 'warning')
    return redirect(request.referrer or url_for('events'))

@app.route('/change-password', methods=['POST'])
@login_required
def change_password():
    """Allow Organizer, Manager, and Student to change their assigned password"""
    old_password = request.form.get('old_password', '').strip()
    new_password = request.form.get('new_password', '').strip()
    confirm_password = request.form.get('confirm_password', '').strip()

    if not current_user.check_password(old_password):
        flash('Mật khẩu hiện tại không chính xác. Vui lòng kiểm tra lại.', 'error')
        return redirect(request.referrer or url_for('events'))

    if len(new_password) < 6:
        flash('Mật khẩu mới phải có tối thiểu 6 ký tự để đảm bảo bảo mật.', 'error')
        return redirect(request.referrer or url_for('events'))

    if new_password != confirm_password:
        flash('Mật khẩu xác nhận không trùng khớp. Vui lòng nhập lại.', 'error')
        return redirect(request.referrer or url_for('events'))

    current_user.set_password(new_password)
    db.session.commit()

    flash('Đổi mật khẩu thành công! Mật khẩu mới đã được cập nhật.', 'success')
    return redirect(request.referrer or url_for('events'))

# ----------------- 1. DISCOVERY & EVENT LIST -----------------

@app.route('/events')
@login_required
def events():
    q = request.args.get('q', '').strip()
    time_filter = request.args.get('time_filter', '')
    location = request.args.get('location', '')
    category_id = request.args.get('category', '')
    tab = request.args.get('tab', 'all')

    today = date.today()
    default_year = f"{today.year}-{today.year + 1}" if today.month >= 8 else f"{today.year - 1}-{today.year}"
    academic_year = request.args.get('academic_year') or session.get('academic_year') or default_year
    semester = request.args.get('semester') or session.get('semester') or 'ALL'

    if 'academic_year' in request.args:
        session['academic_year'] = request.args.get('academic_year')
    if 'semester' in request.args:
        session['semester'] = request.args.get('semester')

    query = Event.query

    # Status tab filtering
    if tab == 'upcoming':
        query = query.filter(Event.status == 'APPROVED', Event.event_date > today)
    elif tab == 'active':
        query = query.filter(Event.status == 'APPROVED', Event.event_date == today)
    elif tab == 'completed':
        query = query.filter(Event.status == 'COMPLETED')
    elif tab == 'cancelled':
        query = query.filter(Event.status == 'CANCELLED')
    else: # all approved / completed / cancelled
        query = query.filter(Event.status.in_(['APPROVED', 'COMPLETED', 'CANCELLED']))

    # Academic period filtering
    start_d, end_d = get_period_date_range(academic_year, semester)
    if start_d:
        query = query.filter(Event.event_date >= start_d)
    if end_d:
        query = query.filter(Event.event_date <= end_d)

    # Keyword filter
    if q:
        query = query.filter(
            (Event.title.ilike(f'%{q}%')) |
            (Event.organizer_name.ilike(f'%{q}%')) |
            (Event.code.ilike(f'%{q}%'))
        )

    # Location filter
    if location:
        query = query.filter(Event.location.ilike(f'%{location}%'))

    # Category filter
    if category_id and category_id.isdigit():
        query = query.filter(Event.category_id == int(category_id))

    # Time filter (Month/Year)
    if time_filter:
        try:
            parts = time_filter.split('/')
            if len(parts) == 2:
                m, y = int(parts[0]), int(parts[1])
                from sqlalchemy import extract
                query = query.filter(extract('month', Event.event_date) == m, extract('year', Event.event_date) == y)
        except Exception:
            pass

    # Pagination setup (6 events per page)
    import math
    page = request.args.get('page', 1, type=int)
    if not page or page < 1:
        page = 1
    per_page = 6

    total_events = query.count()
    total_pages = max(1, math.ceil(total_events / per_page))
    if page > total_pages:
        page = total_pages

    # All matched events (used for full calendar view)
    all_matched_events = query.order_by(Event.event_date.asc()).all()

    # Paginated events for current grid page
    offset_count = (page - 1) * per_page
    paginated_events = query.order_by(Event.event_date.asc()).offset(offset_count).limit(per_page).all()

    start_index = (page - 1) * per_page + 1 if total_events > 0 else 0
    end_index = min(page * per_page, total_events)

    def page_url(p):
        args = request.args.to_dict()
        args['page'] = p
        return url_for('events', **args) + '#eventsSection'

    def tab_url(tab_name):
        args = {k: v for k, v in request.args.items() if k not in ('tab', 'page') and v}
        args['tab'] = tab_name
        return url_for('events', **args) + '#eventsSection'

    # Calculate counts for tabs (scoped to selected academic period)
    base_count_q = Event.query
    if start_d:
        base_count_q = base_count_q.filter(Event.event_date >= start_d)
    if end_d:
        base_count_q = base_count_q.filter(Event.event_date <= end_d)

    counts = {
        'all': base_count_q.filter(Event.status.in_(['APPROVED', 'COMPLETED', 'CANCELLED'])).count(),
        'upcoming': base_count_q.filter(Event.status == 'APPROVED', Event.event_date > today).count(),
        'active': base_count_q.filter(Event.status == 'APPROVED', Event.event_date == today).count(),
        'completed': base_count_q.filter(Event.status == 'COMPLETED').count(),
        'cancelled': base_count_q.filter(Event.status == 'CANCELLED').count()
    }

    featured_q = Event.query.filter_by(is_featured=True)
    if start_d:
        featured_q = featured_q.filter(Event.event_date >= start_d)
    if end_d:
        featured_q = featured_q.filter(Event.event_date <= end_d)
    featured = featured_q.first()
    if not featured and all_matched_events:
        featured = all_matched_events[0]

    categories = EventCategory.query.all()

    # Prepare Calendar Months Data (Không giới hạn - Toàn bộ các tháng theo thời gian)
    import calendar as py_calendar
    months_keys = set()
    if start_d and end_d:
        cur_y, cur_m = start_d.year, start_d.month
        while (cur_y < end_d.year) or (cur_y == end_d.year and cur_m <= end_d.month):
            months_keys.add((cur_y, cur_m))
            cur_m += 1
            if cur_m > 12:
                cur_m = 1
                cur_y += 1
    
    for ev in all_matched_events:
        months_keys.add((ev.event_date.year, ev.event_date.month))
    months_keys.add((today.year, today.month))

    sorted_months = sorted(list(months_keys))
    calendar_months = []
    for (m_year, m_month) in sorted_months:
        start_weekday, num_days = py_calendar.monthrange(m_year, m_month)
        is_cur = (m_year == today.year and m_month == today.month)
        month_events = [ev for ev in all_matched_events if ev.event_date.year == m_year and ev.event_date.month == m_month]
        days_list = []
        for d in range(1, num_days + 1):
            d_events = [ev for ev in month_events if ev.event_date.day == d]
            days_list.append({
                'day': d,
                'is_today': (is_cur and d == today.day),
                'events': d_events
            })
        calendar_months.append({
            'year': m_year,
            'month': m_month,
            'label': f"Tháng {m_month:02d}/{m_year}",
            'is_current': is_cur,
            'start_weekday': start_weekday,
            'days': days_list,
            'event_count': len(month_events)
        })

    # Available time filter options for search dropdown
    available_time_filters = [
        {'value': f"{cm['month']:02d}/{cm['year']}", 'label': f"{cm['month']:02d}/{cm['year']}"}
        for cm in calendar_months
    ]

    return render_template(
        'events.html',
        events=paginated_events,
        all_events=all_matched_events,
        calendar_months=calendar_months,
        available_time_filters=available_time_filters,
        categories=categories,
        featured_event=featured,
        current_tab=tab,
        counts=counts,
        page=page,
        total_pages=total_pages,
        total_events=total_events,
        start_index=start_index,
        end_index=end_index,
        page_url=page_url,
        tab_url=tab_url
    )

# ----------------- 2. EVENT DETAILS & REGISTRATION -----------------

@app.route('/events/<int:event_id>')
@login_required
def event_detail(event_id):
    event = Event.query.get_or_404(event_id)
    existing_reg = Registration.query.filter_by(
        user_id=current_user.id,
        event_id=event.id,
        registration_status='REGISTERED'
    ).first()

    return render_template(
        'event_detail.html',
        event=event,
        existing_registration=existing_reg
    )

@app.route('/events/<int:event_id>/register', methods=['POST'])
@login_required
def register_event(event_id):
    if current_user.role != 'STUDENT':
        flash('Chỉ tài khoản sinh viên mới được đăng ký tham gia sự kiện. Ban tổ chức và Quản lý không thể đăng ký.', 'warning')
        return redirect(url_for('event_detail', event_id=event_id))

    event = Event.query.get_or_404(event_id)

    # Validation
    if not event.is_registration_open:
        flash('Rất tiếc, sự kiện này đã hết chỗ hoặc quá hạn đăng ký!', 'error')
        return redirect(url_for('event_detail', event_id=event.id))

    existing_reg = Registration.query.filter_by(
        user_id=current_user.id,
        event_id=event.id,
        registration_status='REGISTERED'
    ).first()

    if existing_reg:
        flash('Bạn đã đăng ký tham gia sự kiện này rồi!', 'warning')
        return redirect(url_for('event_detail', event_id=event.id))

    # Create new ticket code
    random_num = random.randint(100, 999)
    prefix = event.code.split('-')[1] if '-' in event.code else 'EVT'
    ticket_code = f"NEU-{prefix}-{random_num}"

    new_reg = Registration(
        ticket_code=ticket_code,
        user_id=current_user.id,
        event_id=event.id,
        registration_status='REGISTERED',
        attendance_status='NOT_YET',
        registered_at=datetime.now()
    )

    event.registered_seats += 1
    db.session.add(new_reg)
    db.session.commit()

    flash(f'🎉 Đăng ký thành công! Mã vé của bạn là: {ticket_code}. Hãy đến đúng giờ để điểm danh nhé!', 'success')
    return redirect(url_for('my_events'))

@app.route('/registrations/<int:reg_id>/cancel', methods=['POST'])
@login_required
def cancel_registration(reg_id):
    reg = Registration.query.get_or_404(reg_id)
    if reg.user_id != current_user.id and current_user.role not in ['ORGANIZER', 'MANAGER']:
        flash('Bạn không có quyền thực hiện thao tác này.', 'error')
        return redirect(url_for('my_events'))

    # RULE: Events already checked in (ATTENDED) or already completed cannot be cancelled
    if reg.attendance_status == 'ATTENDED':
        flash('Bạn đã điểm danh tham gia sự kiện này nên không thể hủy đăng ký!', 'error')
        return redirect(request.referrer or url_for('my_events'))

    if reg.event.status == 'COMPLETED' or reg.event.event_date < date.today():
        flash('Sự kiện này đã kết thúc nên không thể hủy đăng ký!', 'error')
        return redirect(request.referrer or url_for('my_events'))

    reg.registration_status = 'CANCELLED'
    reg.attendance_status = 'NOT_APPLICABLE'
    if reg.event.registered_seats > 0:
        reg.event.registered_seats -= 1

    db.session.commit()
    flash(f'Đã hủy đăng ký sự kiện "{reg.event.title}". Chỗ trống đã được mở cho sinh viên khác.', 'info')
    return redirect(request.referrer or url_for('my_events'))

# ----------------- 3. REGISTERED EVENTS (MY EVENTS) -----------------

@app.route('/my-events')
@login_required
def my_events():
    if current_user.role != 'STUDENT':
        flash('Mục "Sự kiện đã đăng ký" chỉ dành riêng cho sinh viên.', 'info')
        return redirect(url_for('organizer_events') if current_user.role in ['ORGANIZER', 'MANAGER'] else url_for('events'))

    filter_type = request.args.get('filter', 'all')
    today = date.today()
    default_year = f"{today.year}-{today.year + 1}" if today.month >= 8 else f"{today.year - 1}-{today.year}"
    academic_year = request.args.get('academic_year') or session.get('academic_year') or default_year
    semester = request.args.get('semester') or session.get('semester') or 'ALL'

    if 'academic_year' in request.args:
        session['academic_year'] = request.args.get('academic_year')
    if 'semester' in request.args:
        session['semester'] = request.args.get('semester')

    start_d, end_d = get_period_date_range(academic_year, semester)

    query = Registration.query.filter_by(user_id=current_user.id).join(Event)

    if start_d:
        query = query.filter(Event.event_date >= start_d)
    if end_d:
        query = query.filter(Event.event_date <= end_d)

    if filter_type == 'upcoming':
        query = query.filter(Event.event_date >= today, Registration.registration_status == 'REGISTERED', Registration.attendance_status != 'ATTENDED')
    elif filter_type == 'attended':
        query = query.filter(Registration.attendance_status == 'ATTENDED')
    elif filter_type == 'absent':
        query = query.filter(Registration.attendance_status == 'ABSENT')
    elif filter_type == 'cancelled':
        query = query.filter((Event.status == 'CANCELLED') | (Registration.registration_status == 'CANCELLED'))

    user_registrations = query.order_by(Registration.registered_at.desc()).all()

    # KPI Statistics within selected period
    all_regs_q = Registration.query.filter_by(user_id=current_user.id).join(Event)
    if start_d:
        all_regs_q = all_regs_q.filter(Event.event_date >= start_d)
    if end_d:
        all_regs_q = all_regs_q.filter(Event.event_date <= end_d)
    all_regs = all_regs_q.all()

    stats = {
        'total': len([r for r in all_regs if r.registration_status == 'REGISTERED']),
        'upcoming': len([r for r in all_regs if r.registration_status == 'REGISTERED' and r.event.event_date >= today and r.attendance_status != 'ATTENDED']),
        'attended': len([r for r in all_regs if r.attendance_status == 'ATTENDED']),
        'absent': len([r for r in all_regs if r.attendance_status == 'ABSENT'])
    }

    # Find live event today for hero banner
    live_reg = None
    for r in all_regs:
        if r.event.event_date == today and r.registration_status == 'REGISTERED' and r.event.status == 'APPROVED':
            live_reg = r
            break

    return render_template(
        'my_events.html',
        registrations=user_registrations,
        stats=stats,
        live_registration=live_reg,
        current_filter=filter_type
    )

def get_or_create_event_session(event):
    """Ensure every event has its own dedicated attendance session with a completely distinct PIN and QR token"""
    session = AttendanceSession.query.filter_by(event_id=event.id, is_active=True).first()
    if not session:
        session = AttendanceSession.query.filter_by(event_id=event.id).first()
        if session:
            session.is_active = True
        else:
            # Generate unique PIN and QR Token based strictly on this specific event's code and ID
            clean_part = event.code.replace('NEU-', '').replace('-', '')
            session_pin = f"{clean_part[:8]}"
            qr_token = f"NEU:CHECKIN:{event.code}"

            existing = AttendanceSession.query.filter_by(session_pin=session_pin).first()
            if existing and existing.event_id != event.id:
                session_pin = f"{clean_part[:5]}{event.id}"

            session = AttendanceSession(
                event_id=event.id,
                session_pin=session_pin,
                qr_token=qr_token,
                valid_from=datetime.combine(event.event_date, time(0, 0)),
                valid_to=datetime.combine(event.event_date, time(23, 59)),
                is_active=True
            )
            db.session.add(session)
        db.session.commit()
    return session

# ----------------- 4. ATTENDANCE & CHECK-IN -----------------

@app.route('/checkin')
@login_required
def checkin():
    if current_user.role == 'MANAGER':
        flash('Đơn vị Quản lý không có quyền truy cập chức năng điểm danh.', 'warning')
        return redirect(url_for('events'))

    event_id = request.args.get('event_id')
    reg_id = request.args.get('reg_id')
    today = date.today()

    if current_user.role == 'ORGANIZER':
        all_events = Event.query.filter_by(organizer_id=current_user.id, status='APPROVED').all()
    else: # STUDENT
        # In check-in: strictly only events that THIS student registered for AND that take place TODAY (real-world time)
        my_today_regs = Registration.query.join(Event).filter(
            Registration.user_id == current_user.id,
            Registration.registration_status == 'REGISTERED',
            Event.status == 'APPROVED',
            Event.event_date == today
        ).all()
        all_events = [r.event for r in my_today_regs]

    if reg_id and reg_id.isdigit():
        target_reg = Registration.query.get(int(reg_id))
        if target_reg:
            if current_user.role == 'STUDENT':
                active_event = target_reg.event if target_reg.event in all_events else (all_events[0] if all_events else None)
            else:
                active_event = target_reg.event
        else:
            active_event = all_events[0] if all_events else None
    elif event_id and event_id.isdigit():
        target_event = Event.query.get(int(event_id))
        # Check permissions for organizer
        if current_user.role == 'ORGANIZER':
            if target_event and target_event.organizer_id != current_user.id:
                flash('Bạn không có quyền quản lý điểm danh sự kiện của Ban tổ chức khác. Đã chuyển về sự kiện của bạn.', 'warning')
                active_event = all_events[0] if all_events else None
            else:
                active_event = target_event
        else: # STUDENT
            if target_event and target_event in all_events:
                active_event = target_event
            else:
                if target_event:
                    flash('Bạn chỉ có thể điểm danh các sự kiện bạn đã đăng ký và diễn ra trong ngày hôm nay.', 'warning')
                active_event = all_events[0] if all_events else None
    else:
        active_event = all_events[0] if all_events else None

    active_session = None
    active_reg = None
    user_att_record = None
    attendees_list = []
    live_stats = {'registered': 0, 'attended': 0, 'not_yet': 0}

    if active_event:
        # Guarantee every event has its own unique, distinct session and QR code
        active_session = get_or_create_event_session(active_event)

        # Student's registration for this event
        active_reg = Registration.query.filter_by(
            event_id=active_event.id,
            user_id=current_user.id
        ).first()

        if active_reg:
            user_att_record = AttendanceRecord.query.filter_by(registration_id=active_reg.id).first()

        # Live attendee list for organizer
        attendees_list = Registration.query.filter_by(
            event_id=active_event.id,
            registration_status='REGISTERED'
        ).all()

        attended_count = len([a for a in attendees_list if a.attendance_status == 'ATTENDED'])
        live_stats = {
            'registered': len(attendees_list),
            'attended': attended_count,
            'not_yet': max(0, len(attendees_list) - attended_count)
        }

    return render_template(
        'checkin.html',
        active_event=active_event,
        all_events=all_events,
        active_session=active_session,
        active_registration=active_reg,
        user_attendance_record=user_att_record,
        attendees_list=attendees_list,
        live_stats=live_stats
    )

@app.route('/checkin/submit', methods=['POST'])
@login_required
def submit_checkin():
    if current_user.role != 'STUDENT':
        flash('Chỉ tài khoản sinh viên mới được điểm danh tham gia sự kiện.', 'error')
        return redirect(url_for('events'))

    event_id = request.form.get('event_id')
    code_input = (request.form.get('qr_code') or request.form.get('pin', '')).strip().upper()

    event = Event.query.get_or_404(int(event_id))
    session = get_or_create_event_session(event)

    # Validate against session PIN or QR Token of this specific event
    is_valid_code = False
    valid_keys = [session.session_pin.upper(), session.qr_token.upper()]
    if code_input in valid_keys or session.session_pin.upper() in code_input or session.qr_token.upper() in code_input:
        is_valid_code = True

    if not is_valid_code:
        # Check if user accidentally scanned another event's QR Code
        other_session = AttendanceSession.query.filter(
            (AttendanceSession.qr_token.ilike(f"%{code_input}%")) | 
            (AttendanceSession.session_pin.ilike(code_input))
        ).first()
        if other_session and other_session.event_id != event.id:
            flash(f'Mã QR này thuộc về sự kiện "{other_session.event.title}". Mỗi sự kiện có mã QR điểm danh riêng biệt, vui lòng quét đúng mã của sự kiện này!', 'error')
        else:
            flash('Mã QR điểm danh không chính xác hoặc không thuộc sự kiện này!', 'error')
        return redirect(url_for('checkin', event_id=event.id))

    # Find or create registration for this student
    reg = Registration.query.filter_by(event_id=event.id, user_id=current_user.id).first()
    if not reg:
        # Auto register on the spot if slots available
        reg = Registration(
            ticket_code=f"NEU-{event.code.split('-')[1]}-{random.randint(100, 999)}",
            user_id=current_user.id,
            event_id=event.id,
            registration_status='REGISTERED',
            attendance_status='NOT_YET'
        )
        event.registered_seats += 1
        db.session.add(reg)
        db.session.commit()

    if reg.attendance_status == 'ATTENDED':
        flash('Bạn đã điểm danh sự kiện này rồi!', 'info')
        return redirect(url_for('checkin', event_id=event.id))

    # Record attendance (Students strictly use QR method)
    reg.attendance_status = 'ATTENDED'
    method = 'QR' if current_user.role == 'STUDENT' else 'PIN'
    record = AttendanceRecord(
        session_id=session.id,
        registration_id=reg.id,
        user_id=current_user.id,
        checked_in_at=datetime.now(),
        checkin_method=method,
        status='ATTENDED'
    )
    event.attended_seats += 1
    db.session.add(record)
    db.session.commit()

    flash('🎉 Điểm danh bằng mã QR thành công! Sự kiện đã được ghi nhận vào lịch sử hoạt động của bạn.', 'success')
    return redirect(url_for('checkin', event_id=event.id))

@app.route('/checkin/manual/<int:reg_id>', methods=['POST'])
@login_required
def manual_checkin(reg_id):
    # Only ORGANIZER has permission to manually confirm attendance for others
    if current_user.role != 'ORGANIZER':
        flash('Bạn không có quyền xác nhận điểm danh thủ công. Quyền này chỉ dành riêng cho Ban tổ chức sự kiện!', 'error')
        return redirect(url_for('events'))

    reg = Registration.query.get_or_404(reg_id)
    # Check if organizer owns this event
    if reg.event.organizer_id != current_user.id:
        flash('Bạn không có quyền xác nhận điểm danh cho sự kiện của Ban tổ chức khác!', 'error')
        return redirect(url_for('checkin', event_id=reg.event_id))

    session = AttendanceSession.query.filter_by(event_id=reg.event_id, is_active=True).first()

    reg.attendance_status = 'ATTENDED'
    if session:
        record = AttendanceRecord(
            session_id=session.id,
            registration_id=reg.id,
            user_id=reg.user_id,
            checked_in_at=datetime.now(),
            checkin_method='MANUAL',
            status='ATTENDED'
        )
        db.session.add(record)
    reg.event.attended_seats += 1
    db.session.commit()

    flash(f'Đã xác nhận điểm danh thủ công cho sinh viên {reg.user.full_name} ({reg.user.student_id}).', 'success')
    return redirect(request.referrer or url_for('checkin', event_id=reg.event_id))

@app.route('/checkin/export/<int:event_id>')
@login_required
def export_attendance(event_id):
    if current_user.role not in ['ORGANIZER', 'MANAGER']:
        flash('Bạn không có quyền xuất danh sách điểm danh. Quyền này chỉ dành riêng cho Ban tổ chức và Đơn vị Quản lý!', 'error')
        return redirect(url_for('events'))

    event = Event.query.get_or_404(event_id)
    # Check if organizer owns this event (Manager can export any event)
    if current_user.role == 'ORGANIZER' and event.organizer_id != current_user.id:
        flash('Bạn không có quyền xuất danh sách của sự kiện do Ban tổ chức khác tổ chức!', 'error')
        return redirect(url_for('events'))

    registrations = Registration.query.filter_by(event_id=event.id, registration_status='REGISTERED').all()

    export_format = request.args.get('format', 'xlsx').lower()

    if export_format == 'csv':
        # UTF-8 BOM CSV export with full Vietnamese support
        si = StringIO()
        si.write('\ufeff')
        cw = csv.writer(si)
        cw.writerow(['STT', 'MSSV', 'Họ và tên', 'Email', 'Khoa/Phòng ban', 'Mã vé', 'Trạng thái tham dự', 'Thời gian điểm danh', 'Hình thức điểm danh'])

        for idx, r in enumerate(registrations, 1):
            att_time = r.attendance_record.checked_in_at.strftime('%H:%M %d/%m/%Y') if r.attendance_record else 'Chưa điểm danh'
            method = 'Quét QR' if (r.attendance_record and r.attendance_record.checkin_method == 'QR_CODE') else ('Thủ công' if r.attendance_record else '—')
            cw.writerow([
                idx,
                r.user.student_id or r.user.username,
                r.user.full_name,
                r.user.email,
                r.user.department or '',
                r.ticket_code,
                'Đã tham dự' if r.attendance_status == 'ATTENDED' else 'Chưa điểm danh',
                att_time,
                method
            ])

        output_bytes = si.getvalue().encode('utf-8-sig')
        filename = f"Diem_danh_{event.code}_{date.today().strftime('%Y%m%d')}.csv"
        return Response(
            output_bytes,
            mimetype="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )

    # Default export: Professional Excel (.xlsx) workbook using openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Diem_danh"
    ws.views.sheetView[0].showGridLines = True

    # Styling definitions
    font_title = Font(name="Calibri", size=14, bold=True, color="002B49")
    font_sub = Font(name="Calibri", size=10, italic=True, color="475569")
    font_header = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    font_data = Font(name="Calibri", size=10, color="0F172A")
    font_bold = Font(name="Calibri", size=10, bold=True, color="0F172A")

    fill_header = PatternFill(start_color="002B49", end_color="002B49", fill_type="solid")
    fill_zebra = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")

    thin_border_side = Side(border_style="thin", color="CBD5E1")
    border_cell = Border(left=thin_border_side, right=thin_border_side, top=thin_border_side, bottom=thin_border_side)

    align_center = Alignment(horizontal="center", vertical="center")
    align_left = Alignment(horizontal="left", vertical="center")

    # Row 1: Title
    ws.merge_cells("A1:I1")
    cell_title = ws["A1"]
    cell_title.value = "DANH SÁCH SINH VIÊN ĐĂNG KÝ VÀ ĐIỂM DANH SỰ KIỆN"
    cell_title.font = font_title
    cell_title.alignment = align_center
    ws.row_dimensions[1].height = 28

    # Row 2: Subtitle
    ws.merge_cells("A2:I2")
    cell_sub = ws["A2"]
    cell_sub.value = f"Sự kiện: {event.title} ({event.code})  |  Ngày tổ chức: {event.event_date.strftime('%d/%m/%Y')}  |  Đơn vị: {event.organizer_name}"
    cell_sub.font = font_sub
    cell_sub.alignment = align_center
    ws.row_dimensions[2].height = 20

    # Row 3: Blank spacer
    ws.row_dimensions[3].height = 10

    # Row 4: Table Headers
    headers = [
        "STT",
        "Mã sinh viên (MSSV)",
        "Họ và tên",
        "Email",
        "Khoa / Viện / Phòng ban",
        "Mã vé điện tử",
        "Trạng thái tham dự",
        "Thời gian điểm danh",
        "Hình thức điểm danh"
    ]
    ws.row_dimensions[4].height = 24
    for col_idx, h in enumerate(headers, 1):
        cell = ws.cell(row=4, column=col_idx, value=h)
        cell.font = font_header
        cell.fill = fill_header
        cell.alignment = align_center
        cell.border = border_cell

    # Row 5+: Data rows
    for row_idx, r in enumerate(registrations, 5):
        ws.row_dimensions[row_idx].height = 20
        att_time = r.attendance_record.checked_in_at.strftime('%H:%M %d/%m/%Y') if r.attendance_record else 'Chưa điểm danh'
        method = 'Quét QR' if (r.attendance_record and r.attendance_record.checkin_method == 'QR_CODE') else ('Thủ công' if r.attendance_record else '—')
        status_text = 'Đã tham dự' if r.attendance_status == 'ATTENDED' else 'Chưa điểm danh'

        row_data = [
            row_idx - 4,
            r.user.student_id or r.user.username,
            r.user.full_name,
            r.user.email,
            r.user.department or '',
            r.ticket_code,
            status_text,
            att_time,
            method
        ]

        is_even = ((row_idx - 4) % 2 == 0)
        for col_idx, val in enumerate(row_data, 1):
            cell = ws.cell(row=row_idx, column=col_idx, value=val)
            cell.font = font_data
            cell.border = border_cell
            if is_even:
                cell.fill = fill_zebra

            # Alignments
            if col_idx in [1, 2, 6, 7, 8, 9]:
                cell.alignment = align_center
            else:
                cell.alignment = align_left

            # Highlight attended status
            if col_idx == 7 and status_text == 'Đã tham dự':
                cell.font = Font(name="Calibri", size=10, bold=True, color="15803D")

    # Row summary
    summary_row = len(registrations) + 5
    ws.row_dimensions[summary_row].height = 22
    ws.merge_cells(start_row=summary_row, start_column=1, end_row=summary_row, end_column=9)
    cell_sum = ws.cell(row=summary_row, column=1, value=f"Tổng số đăng ký: {len(registrations)}  |  Đã tham dự: {event.attended_seats} sinh viên ({event.attendance_rate}%)")
    cell_sum.font = font_bold
    cell_sum.alignment = align_left

    # Auto-fit column widths
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            if cell.row in [1, 2, summary_row]:
                continue
            val_str = str(cell.value or '')
            max_len = max(max_len, len(val_str))
        ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)

    filename = f"Diem_danh_{event.code}_{date.today().strftime('%Y%m%d')}.xlsx"
    return Response(
        buf.getvalue(),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache"
        }
    )

# ----------------- 5. EVENT MANAGEMENT (ORGANIZER) -----------------

@app.route('/organizer/events')
@login_required
def organizer_events():
    # Strictly for ORGANIZER role only
    if current_user.role != 'ORGANIZER':
        flash('Trang Quản lý sự kiện chỉ dành riêng cho Ban tổ chức.', 'error')
        return redirect(url_for('events'))

    edit_id = request.args.get('edit_id')
    is_new = request.args.get('new') == '1'

    academic_year = request.args.get('academic_year') or session.get('academic_year')
    semester = request.args.get('semester') or session.get('semester')

    if 'academic_year' in request.args:
        session['academic_year'] = request.args.get('academic_year')
    if 'semester' in request.args:
        session['semester'] = request.args.get('semester')

    start_d, end_d = get_period_date_range(academic_year, semester)

    # Strict isolation: ORGANIZER only sees their own events
    query = Event.query.filter_by(organizer_id=current_user.id)
    if start_d:
        query = query.filter(Event.event_date >= start_d)
    if end_d:
        query = query.filter(Event.event_date <= end_d)
    my_events = query.order_by(Event.event_date.desc()).all()

    if is_new:
        selected_event = None
    elif edit_id and edit_id.isdigit():
        target = Event.query.get(int(edit_id))
        if not target:
            flash('Sự kiện không tồn tại trong hệ thống.', 'error')
            return redirect(url_for('organizer_events'))
        # SECURITY CHECK: Block organizer from viewing another organizer's event
        if target.organizer_id != current_user.id:
            flash('Bạn không có quyền truy cập hoặc chỉnh sửa sự kiện của Ban tổ chức khác!', 'error')
            return redirect(url_for('organizer_events'))
        if target.is_completed:
            flash('Sự kiện đã kết thúc, hệ thống đã khóa chức năng chỉnh sửa nội dung.', 'warning')
        selected_event = target
    else:
        selected_event = my_events[0] if my_events else None

    categories = EventCategory.query.all()
    selected_registrations = []
    if selected_event:
        selected_registrations = Registration.query.filter_by(
            event_id=selected_event.id,
            registration_status='REGISTERED'
        ).all()

    return render_template(
        'organizer_events.html',
        my_events=my_events,
        selected_event=selected_event,
        selected_registrations=selected_registrations,
        categories=categories
    )

@app.route('/organizer/events/save', methods=['POST'])
@login_required
def save_event():
    # Manager is strictly forbidden from creating or editing events
    if current_user.role == 'MANAGER':
        flash('Đơn vị Quản lý không được phép tạo mới hoặc chỉnh sửa sự kiện. Thẩm quyền này thuộc về Ban tổ chức.', 'error')
        return redirect(url_for('organizer_events'))

    if current_user.role != 'ORGANIZER':
        flash('Bạn không có quyền thực hiện thao tác này.', 'error')
        return redirect(url_for('events'))

    event_id = request.form.get('event_id')
    title = request.form.get('title', '').strip()
    category_id = int(request.form.get('category_id'))
    organizer_name = request.form.get('organizer_name', '').strip()
    event_date_str = request.form.get('event_date')
    start_time_str = request.form.get('start_time')
    end_time_str = request.form.get('end_time')
    location = request.form.get('location', '').strip()
    max_seats = int(request.form.get('max_seats', 200))
    reg_deadline_str = request.form.get('reg_deadline')
    fee = request.form.get('fee', 'Miễn phí')
    description = request.form.get('description', '').strip()
    union_points_plus = int(request.form.get('union_points_plus', 5) or 5)
    union_points_minus = int(request.form.get('union_points_minus', 0) or 0)
    sponsor_benefits = request.form.get('sponsor_benefits', '').strip() or None
    handbook_name = request.form.get('handbook_name', '').strip() or 'Cẩm nang sự kiện NEU.pdf'

    # Check publication file upload
    handbook_file = request.files.get('handbook_file')
    uploaded_handbook_url = None
    if handbook_file and handbook_file.filename:
        from werkzeug.utils import secure_filename
        filename = secure_filename(handbook_file.filename)
        if not filename:
            filename = f"publication_{int(datetime.now().timestamp())}.pdf"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        handbook_file.save(file_path)
        handbook_name = handbook_file.filename
        uploaded_handbook_url = f"/static/uploads/publications/{filename}"

    ev_date = datetime.strptime(event_date_str, '%Y-%m-%d').date()
    st_time = datetime.strptime(start_time_str, '%H:%M').time()
    ed_time = datetime.strptime(end_time_str, '%H:%M').time()
    reg_dl = datetime.strptime(reg_deadline_str, '%Y-%m-%d')

    if event_id and event_id.isdigit():
        event = Event.query.get_or_404(int(event_id))
        # SECURITY CHECK: Block organizer from updating another organizer's event
        if event.organizer_id != current_user.id:
            flash('Bạn không có quyền chỉnh sửa sự kiện của Ban tổ chức khác!', 'error')
            return redirect(url_for('organizer_events'))

        # REQ 1: Block edit if event is completed
        if event.is_completed:
            flash('Sự kiện đã kết thúc, không thể chỉnh sửa thông tin.', 'error')
            return redirect(url_for('organizer_events', edit_id=event.id))

        event.title = title
        event.category_id = category_id
        event.organizer_name = organizer_name
        event.event_date = ev_date
        event.start_time = st_time
        event.end_time = ed_time
        event.location = location
        event.max_seats = max_seats
        event.registration_deadline = reg_dl
        event.fee = fee
        event.description = description
        event.union_points_plus = union_points_plus
        event.union_points_minus = union_points_minus
        event.sponsor_benefits = sponsor_benefits
        if handbook_name:
            event.handbook_name = handbook_name
        if uploaded_handbook_url:
            event.handbook_url = uploaded_handbook_url

        # REQ 3: When editing, status must reset to PENDING and require Manager/Admin approval
        event.status = 'PENDING'
        event.cancel_reason = None

        log = ApprovalLog(
            event_id=event.id,
            manager_id=current_user.id,
            action='REQUEST_CHANGE',
            note='Ban tổ chức đã cập nhật thông tin sự kiện. Hồ sơ chuyển sang trạng thái Chờ duyệt để Đơn vị Quản lý phê duyệt lại.'
        )
        db.session.add(log)

        flash('Đã lưu thay đổi thông tin sự kiện. Hồ sơ đã chuyển sang trạng thái "Chờ duyệt" để Đơn vị Quản lý kiểm duyệt lại trước khi hiển thị Đã duyệt.', 'success')
    else:
        # Create new
        code = f"NEU-EVT-{random.randint(1000, 9999)}"
        new_event = Event(
            code=code,
            title=title,
            category_id=category_id,
            organizer_id=current_user.id,
            organizer_name=organizer_name,
            organizer_email=current_user.email,
            location=location,
            event_date=ev_date,
            start_time=st_time,
            end_time=ed_time,
            registration_deadline=reg_dl,
            max_seats=max_seats,
            fee=fee,
            description=description,
            union_points_plus=union_points_plus,
            union_points_minus=union_points_minus,
            sponsor_benefits=sponsor_benefits,
            handbook_name=handbook_name,
            handbook_url=uploaded_handbook_url,
            status='PENDING' # requires approval
        )
        db.session.add(new_event)
        flash('Tạo sự kiện mới thành công! Hồ sơ đã được gửi sang Đơn vị Quản lý để kiểm duyệt.', 'success')

    db.session.commit()
    return redirect(url_for('organizer_events', edit_id=event_id if event_id else None))

@app.route('/organizer/events/<int:event_id>/cancel', methods=['POST'])
@login_required
def cancel_event(event_id):
    # Manager is not allowed to directly cancel events here; must use moderation
    if current_user.role == 'MANAGER':
        flash('Đơn vị Quản lý không được phép hủy sự kiện tại đây. Vui lòng sử dụng phân hệ Kiểm duyệt để từ chối duyệt.', 'error')
        return redirect(url_for('moderation'))

    if current_user.role != 'ORGANIZER':
        flash('Bạn không có quyền thực hiện thao tác này.', 'error')
        return redirect(url_for('events'))

    event = Event.query.get_or_404(event_id)
    # SECURITY CHECK: Block organizer from cancelling another organizer's event
    if event.organizer_id != current_user.id:
        flash('Bạn không có quyền hủy sự kiện của Ban tổ chức khác!', 'error')
        return redirect(url_for('organizer_events'))

    # RULE: Events already completed or with students checked in cannot be cancelled
    if event.status == 'COMPLETED' or event.event_date < date.today():
        flash('Sự kiện đã kết thúc nên không thể hủy!', 'error')
        return redirect(url_for('organizer_events', edit_id=event.id))

    if event.attended_seats > 0:
        flash(f'Sự kiện đã có {event.attended_seats} sinh viên điểm danh tham dự nên không thể hủy!', 'error')
        return redirect(url_for('organizer_events', edit_id=event.id))

    if event.status == 'CANCELLED':
        flash('Sự kiện này đã bị hủy trước đó.', 'info')
        return redirect(url_for('organizer_events', edit_id=event.id))

    reason = request.form.get('cancel_reason', 'Kế hoạch tổ chức có thay đổi.')

    event.status = 'CANCELLED'
    event.cancel_reason = reason
    db.session.commit()

    flash(f'Đã hủy sự kiện "{event.title}". Thông báo và lý do hủy đã được gửi đến {event.registered_seats} sinh viên đăng ký.', 'warning')
    return redirect(url_for('organizer_events', edit_id=event.id))

# ----------------- 6. MODERATION (MANAGER) -----------------

@app.route('/moderation')
@login_required
def moderation():
    if current_user.role != 'MANAGER':
        flash('Bạn không có quyền truy cập phân hệ Kiểm duyệt sự kiện.', 'error')
        return redirect(url_for('events'))

    pending = Event.query.filter_by(status='PENDING').order_by(Event.created_at.desc()).all()
    approved = Event.query.filter_by(status='APPROVED').order_by(Event.event_date.desc()).limit(10).all()

    return render_template(
        'moderation.html',
        pending_events=pending,
        approved_events=approved
    )

@app.route('/moderation/approve/<int:event_id>', methods=['POST'])
@login_required
def approve_event(event_id):
    if current_user.role != 'MANAGER':
        flash('Bạn không có quyền thực hiện thao tác này.', 'error')
        return redirect(url_for('events'))

    event = Event.query.get_or_404(event_id)
    event.status = 'APPROVED'

    log = ApprovalLog(
        event_id=event.id,
        manager_id=current_user.id,
        action='APPROVE',
        note='Hồ sơ đáp ứng đầy đủ quy chế tổ chức sự kiện NEU.'
    )
    db.session.add(log)
    db.session.commit()

    flash(f'Đã phê duyệt sự kiện "{event.title}". Sự kiện hiện đã xuất bản công khai trên cổng khám phá!', 'success')
    return redirect(url_for('moderation'))

@app.route('/moderation/reject/<int:event_id>', methods=['POST'])
@login_required
def reject_event(event_id):
    if current_user.role != 'MANAGER':
        flash('Bạn không có quyền thực hiện thao tác này.', 'error')
        return redirect(url_for('events'))

    event = Event.query.get_or_404(event_id)
    reason = request.form.get('reason', 'Nội dung cần bổ sung.')

    event.status = 'REJECTED'
    event.cancel_reason = reason

    log = ApprovalLog(
        event_id=event.id,
        manager_id=current_user.id,
        action='REJECT',
        note=reason
    )
    db.session.add(log)
    db.session.commit()

    flash(f'Đã từ chối sự kiện "{event.title}". Lý do đã được gửi phản hồi về Ban tổ chức đơn vị.', 'info')
    return redirect(url_for('moderation'))

# ----------------- 7. FEEDBACK & EVALUATION -----------------

@app.route('/feedback')
@login_required
def feedback():
    if current_user.role == 'MANAGER':
        flash('Đơn vị Quản lý không có quyền truy cập chức năng đánh giá sự kiện.', 'warning')
        return redirect(url_for('events'))

    selected_event_id = request.args.get('event_id')
    if selected_event_id and selected_event_id.isdigit():
        selected_event_id = int(selected_event_id)
    else:
        selected_event_id = None

    if current_user.role == 'ORGANIZER':
        # Fetch events strictly for this organizer
        org_events = Event.query.filter_by(organizer_id=current_user.id).order_by(Event.event_date.desc()).all()

        selected_event = None
        if selected_event_id:
            target_event = Event.query.get(selected_event_id)
            if target_event:
                if target_event.organizer_id != current_user.id:
                    flash('Bạn không có quyền xem đánh giá của sự kiện do Ban tổ chức khác tổ chức!', 'error')
                    selected_event = org_events[0] if org_events else None
                else:
                    selected_event = target_event
        if not selected_event and org_events:
            selected_event = org_events[0]

        selected_feedbacks = []
        feedback_stats = {
            'total': 0,
            'avg_rating': 0.0,
            'satisfaction_rate': 0,
            'avg_content': 0.0,
            'avg_org': 0.0,
            'avg_speaker': 0.0,
            'avg_venue': 0.0,
            'star_counts': {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
        }

        if selected_event:
            selected_feedbacks = Feedback.query.filter_by(event_id=selected_event.id).order_by(Feedback.created_at.desc()).all()
            total = len(selected_feedbacks)
            feedback_stats['total'] = total
            if total > 0:
                stars = [f.rating_stars for f in selected_feedbacks if f.rating_stars]
                if stars:
                    feedback_stats['avg_rating'] = round(sum(stars) / len(stars), 1)
                    feedback_stats['satisfaction_rate'] = round(len([s for s in stars if s >= 4]) / len(stars) * 100)
                    for s in stars:
                        if s in feedback_stats['star_counts']:
                            feedback_stats['star_counts'][s] += 1
                feedback_stats['avg_content'] = round(sum([f.rating_content or 5 for f in selected_feedbacks]) / total, 1)
                feedback_stats['avg_org'] = round(sum([f.rating_organization or 5 for f in selected_feedbacks]) / total, 1)
                feedback_stats['avg_speaker'] = round(sum([f.rating_speaker or 5 for f in selected_feedbacks]) / total, 1)
                feedback_stats['avg_venue'] = round(sum([f.rating_venue or 5 for f in selected_feedbacks]) / total, 1)

        return render_template(
            'feedback.html',
            org_events=org_events,
            selected_event=selected_event,
            selected_feedbacks=selected_feedbacks,
            feedback_stats=feedback_stats
        )

    else:
        # STUDENT VIEW: Real-time evaluation history (evaluated vs pending)
        user_attended_regs = Registration.query.filter_by(
            user_id=current_user.id,
            attendance_status='ATTENDED'
        ).order_by(Registration.registered_at.desc()).all()
        attended_events = [r.event for r in user_attended_regs if r.event]

        # Student's past submitted feedbacks ordered by real system timestamp created_at desc
        my_feedbacks = Feedback.query.filter_by(user_id=current_user.id).order_by(Feedback.created_at.desc()).all()
        feedback_map = {fb.event_id: fb for fb in my_feedbacks}

        # Segregate evaluated items
        evaluated_items = []
        for fb in my_feedbacks:
            if fb.event:
                matching_reg = next((r for r in user_attended_regs if r.event_id == fb.event_id), None)
                evaluated_items.append({
                    'event': fb.event,
                    'registration': matching_reg,
                    'feedback': fb,
                    'status': 'EVALUATED'
                })

        # Segregate pending items (attended but not yet evaluated)
        pending_items = []
        for reg in user_attended_regs:
            ev = reg.event
            if ev and ev.id not in feedback_map:
                pending_items.append({
                    'event': ev,
                    'registration': reg,
                    'feedback': None,
                    'status': 'PENDING'
                })

        # Determine currently selected event for the evaluation form
        selected_event = None
        if selected_event_id:
            selected_event = next((e for e in attended_events if e.id == selected_event_id), None)
        if not selected_event:
            # Default to first pending event, otherwise first attended event
            if pending_items:
                selected_event = pending_items[0]['event']
            elif attended_events:
                selected_event = attended_events[0]

        active_feedback = feedback_map.get(selected_event.id) if selected_event else None

        return render_template(
            'feedback.html',
            attended_events=attended_events,
            selected_event=selected_event,
            selected_event_id=selected_event.id if selected_event else None,
            active_feedback=active_feedback,
            my_feedbacks=my_feedbacks,
            evaluated_items=evaluated_items,
            pending_items=pending_items,
            feedback_map=feedback_map
        )

@app.route('/feedback/submit', methods=['POST'])
@login_required
def submit_feedback():
    if current_user.role != 'STUDENT':
        flash('Chỉ tài khoản sinh viên mới được gửi đánh giá sự kiện.', 'error')
        return redirect(url_for('feedback'))

    event_id = int(request.form.get('event_id'))
    rating_stars = int(request.form.get('rating_stars', 5))
    rating_content = int(request.form.get('rating_content', 5))
    rating_organization = int(request.form.get('rating_organization', 5))
    rating_speaker = int(request.form.get('rating_speaker', 5))
    rating_venue = int(request.form.get('rating_venue', 5))
    comment = request.form.get('comment', '').strip()
    is_anonymous = bool(request.form.get('is_anonymous'))

    # Verify student attended
    reg = Registration.query.filter_by(
        event_id=event_id,
        user_id=current_user.id,
        attendance_status='ATTENDED'
    ).first()

    if not reg:
        flash('Chỉ những sinh viên đã điểm danh tham dự mới có quyền đánh giá sự kiện này.', 'error')
        return redirect(url_for('feedback'))

    # Check if student already gave feedback for this event -> update with current system time
    fb = Feedback.query.filter_by(event_id=event_id, user_id=current_user.id).first()
    if fb:
        fb.rating_stars = rating_stars
        fb.rating_content = rating_content
        fb.rating_organization = rating_organization
        fb.rating_speaker = rating_speaker
        fb.rating_venue = rating_venue
        fb.comment = comment
        fb.is_anonymous = is_anonymous
        fb.created_at = datetime.now()
        flash('Đánh giá của bạn đã được cập nhật thành công theo thời gian hệ thống!', 'success')
    else:
        fb = Feedback(
            event_id=event_id,
            user_id=current_user.id,
            rating_stars=rating_stars,
            rating_content=rating_content,
            rating_organization=rating_organization,
            rating_speaker=rating_speaker,
            rating_venue=rating_venue,
            comment=comment,
            is_anonymous=is_anonymous,
            created_at=datetime.now()
        )
        db.session.add(fb)
        flash('Cảm ơn bạn đã gửi đánh giá! Ý kiến của bạn sẽ giúp BTC nâng cao chất lượng các sự kiện tiếp theo.', 'success')

    db.session.commit()
    return redirect(url_for('feedback', event_id=event_id))

# ----------------- 8. REPORTS & ANALYTICS -----------------

def get_analytics_data(user, args, session_obj):
    period = args.get('period')
    organizer = args.get('organizer')
    category_id = args.get('category_id')

    # Date range resolution
    start_d, end_d = None, None

    if period == 'ALL' or not period:
        start_d, end_d = None, None
    elif period == 'THIS_WEEK':
        t = date.today()
        start_d = t - timedelta(days=t.weekday())
        end_d = start_d + timedelta(days=6)
    elif period == 'THIS_MONTH':
        t = date.today()
        start_d = date(t.year, t.month, 1)
        _, last_day = calendar.monthrange(t.year, t.month)
        end_d = date(t.year, t.month, last_day)
    elif period == 'THIS_QUARTER':
        t = date.today()
        q_idx = (t.month - 1) // 3 + 1
        m_start = (q_idx - 1) * 3 + 1
        m_end = q_idx * 3
        start_d = date(t.year, m_start, 1)
        _, last_day = calendar.monthrange(t.year, m_end)
        end_d = date(t.year, m_end, last_day)
    elif period == 'THIS_YEAR':
        t = date.today()
        start_d = date(t.year, 1, 1)
        end_d = date(t.year, 12, 31)
    elif period and period.startswith('Q') and len(period) >= 2 and period[1] in '1234':
        t = date.today()
        q_idx = int(period[1])
        parts = period.split('_')
        y = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else t.year
        m_start = (q_idx - 1) * 3 + 1
        m_end = q_idx * 3
        start_d = date(y, m_start, 1)
        _, last_day = calendar.monthrange(y, m_end)
        end_d = date(y, m_end, last_day)
    elif period and '-' in period and len(period.split('-')) == 2 and period.split('-')[0].isdigit():
        start_d, end_d = get_period_date_range(period, None)
    elif period and any(k in period for k in ['Thu', 'Xuân', 'Hè']):
        start_d, end_d = get_period_date_range(None, period)
    else:
        academic_year = args.get('academic_year') or session_obj.get('academic_year')
        semester = args.get('semester') or session_obj.get('semester')
        if academic_year or semester:
            start_d, end_d = get_period_date_range(academic_year, semester)

    # Base query based on user role
    if user.role == 'ORGANIZER':
        q = Event.query.filter_by(organizer_id=user.id)
    else:
        q = Event.query
        if organizer and organizer != 'ALL':
            q = q.filter(Event.organizer_name == organizer)

    if start_d:
        q = q.filter(Event.event_date >= start_d)
    if end_d:
        q = q.filter(Event.event_date <= end_d)

    if category_id and category_id != 'ALL':
        try:
            q = q.filter(Event.category_id == int(category_id))
        except (ValueError, TypeError):
            pass

    display_events = q.order_by(Event.event_date.desc()).all()
    ev_ids = [e.id for e in display_events]
    events_count = len(ev_ids)
    regs_count = Registration.query.filter(Registration.event_id.in_(ev_ids)).count() if ev_ids else 0
    att_count = Registration.query.filter(Registration.event_id.in_(ev_ids), Registration.attendance_status == 'ATTENDED').count() if ev_ids else 0
    rate = round(att_count / regs_count * 100, 1) if regs_count > 0 else 0.0

    stats = {
        'events': events_count,
        'registrations': regs_count,
        'attended': att_count,
        'rate': rate
    }

    # Category distribution for donut chart
    cat_colors = {
        'Nghề nghiệp': '#0F4C81',
        'Công nghệ': '#3b82f6',
        'Học thuật': '#10b981',
        'Văn hóa & Kỹ năng': '#f59e0b',
        'Cộng đồng': '#14b8a6',
        'Văn hóa': '#ec4899'
    }
    fallback_palette = ['#0F4C81', '#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4', '#64748b']

    cat_counts = {}
    for ev in display_events:
        c_name = ev.category.name if ev.category else 'Khác'
        cat_counts[c_name] = cat_counts.get(c_name, 0) + 1

    category_items = []
    cat_labels = []
    cat_counts_list = []
    cat_colors_list = []

    sorted_cats = sorted(cat_counts.items(), key=lambda x: x[1], reverse=True)
    for idx, (cat_name, cnt) in enumerate(sorted_cats):
        pct = round((cnt / events_count) * 100, 1) if events_count > 0 else 0
        color = cat_colors.get(cat_name, fallback_palette[idx % len(fallback_palette)])
        category_items.append({
            'name': cat_name,
            'count': cnt,
            'pct': pct,
            'color': color
        })
        cat_labels.append(cat_name)
        cat_counts_list.append(cnt)
        cat_colors_list.append(color)

    category_data = {
        'total': events_count,
        'labels': cat_labels,
        'counts': cat_counts_list,
        'colors': cat_colors_list,
        'categories': category_items
    }

    # Timeline Bar Chart Data (both Weekly and Monthly)
    today = date.today()

    # 1. Weekly data: 8 consecutive weeks
    if start_d and end_d and (end_d - start_d).days <= 70:
        w_cur = start_d - timedelta(days=start_d.weekday())
        w_end_limit = end_d
        weekly_labels = []
        weekly_regs = []
        weekly_att = []
        while w_cur <= w_end_limit:
            w_next = w_cur + timedelta(days=6)
            weekly_labels.append(f"{w_cur.strftime('%d/%m')}–{w_next.strftime('%d/%m')}")
            ev_in_w = [e for e in display_events if w_cur <= e.event_date <= w_next]
            weekly_regs.append(sum(e.registered_seats for e in ev_in_w))
            weekly_att.append(sum(e.attended_seats for e in ev_in_w))
            w_cur += timedelta(days=7)
    else:
        monday_this_week = today - timedelta(days=today.weekday())
        weekly_labels = []
        weekly_regs = []
        weekly_att = []
        for i in range(-4, 4):
            w_start_i = monday_this_week + timedelta(weeks=i)
            w_end_i = w_start_i + timedelta(days=6)
            weekly_labels.append(f"{w_start_i.strftime('%d/%m')}–{w_end_i.strftime('%d/%m')}")
            ev_in_w = [e for e in display_events if w_start_i <= e.event_date <= w_end_i]
            weekly_regs.append(sum(e.registered_seats for e in ev_in_w))
            weekly_att.append(sum(e.attended_seats for e in ev_in_w))

    # 2. Monthly data
    if start_d and end_d:
        m_cur = date(start_d.year, start_d.month, 1)
        m_end_limit = date(end_d.year, end_d.month, 1)
        monthly_labels = []
        monthly_regs = []
        monthly_att = []
        while m_cur <= m_end_limit:
            lbl = f"Tháng {m_cur.month:02d}" if start_d.year == end_d.year else f"T{m_cur.month:02d}/{str(m_cur.year)[2:]}"
            monthly_labels.append(lbl)
            ev_in_m = [e for e in display_events if e.event_date.year == m_cur.year and e.event_date.month == m_cur.month]
            monthly_regs.append(sum(e.registered_seats for e in ev_in_m))
            monthly_att.append(sum(e.attended_seats for e in ev_in_m))
            if m_cur.month == 12:
                m_cur = date(m_cur.year + 1, 1, 1)
            else:
                m_cur = date(m_cur.year, m_cur.month + 1, 1)
    else:
        # All time: all distinct months from display_events
        distinct_ym = sorted(list(set((e.event_date.year, e.event_date.month) for e in display_events)))
        monthly_labels = []
        monthly_regs = []
        monthly_att = []
        for y, m in distinct_ym:
            monthly_labels.append(f"T{m:02d}/{str(y)[2:]}")
            ev_in_m = [e for e in display_events if e.event_date.year == y and e.event_date.month == m]
            monthly_regs.append(sum(e.registered_seats for e in ev_in_m))
            monthly_att.append(sum(e.attended_seats for e in ev_in_m))

    # 3. Quarterly data
    if start_d and end_d:
        y_cur = start_d.year
        q_cur = (start_d.month - 1) // 3 + 1
        y_end = end_d.year
        q_end = (end_d.month - 1) // 3 + 1
        quarterly_labels = []
        quarterly_regs = []
        quarterly_att = []
        while (y_cur < y_end) or (y_cur == y_end and q_cur <= q_end):
            lbl = f"Quý {q_cur}" if start_d.year == end_d.year else f"Q{q_cur}/{str(y_cur)[2:]}"
            quarterly_labels.append(lbl)
            m_start = (q_cur - 1) * 3 + 1
            m_end = q_cur * 3
            ev_in_q = [e for e in display_events if e.event_date.year == y_cur and m_start <= e.event_date.month <= m_end]
            quarterly_regs.append(sum(e.registered_seats for e in ev_in_q))
            quarterly_att.append(sum(e.attended_seats for e in ev_in_q))
            if q_cur == 4:
                y_cur += 1
                q_cur = 1
            else:
                q_cur += 1
    else:
        distinct_yq = sorted(list(set((e.event_date.year, (e.event_date.month - 1) // 3 + 1) for e in display_events)))
        quarterly_labels = []
        quarterly_regs = []
        quarterly_att = []
        if not distinct_yq:
            distinct_yq = [(today.year, q) for q in range(1, 5)]
        for y, q in distinct_yq:
            quarterly_labels.append(f"Q{q}/{str(y)[2:]}")
            m_start = (q - 1) * 3 + 1
            m_end = q * 3
            ev_in_q = [e for e in display_events if e.event_date.year == y and m_start <= e.event_date.month <= m_end]
            quarterly_regs.append(sum(e.registered_seats for e in ev_in_q))
            quarterly_att.append(sum(e.attended_seats for e in ev_in_q))

    # 4. Yearly data
    if start_d and end_d and start_d.year != end_d.year:
        y_cur = start_d.year
        yearly_labels = []
        yearly_regs = []
        yearly_att = []
        while y_cur <= end_d.year:
            yearly_labels.append(f"Năm {y_cur}")
            ev_in_y = [e for e in display_events if e.event_date.year == y_cur]
            yearly_regs.append(sum(e.registered_seats for e in ev_in_y))
            yearly_att.append(sum(e.attended_seats for e in ev_in_y))
            y_cur += 1
    else:
        distinct_y = sorted(list(set(e.event_date.year for e in display_events)))
        if not distinct_y:
            distinct_y = [today.year - 1, today.year, today.year + 1]
        elif len(distinct_y) == 1:
            only_y = distinct_y[0]
            distinct_y = [only_y - 1, only_y, only_y + 1]
        yearly_labels = []
        yearly_regs = []
        yearly_att = []
        for y in distinct_y:
            yearly_labels.append(f"Năm {y}")
            ev_in_y = [e for e in display_events if e.event_date.year == y]
            yearly_regs.append(sum(e.registered_seats for e in ev_in_y))
            yearly_att.append(sum(e.attended_seats for e in ev_in_y))

    bar_chart_data = {
        'week': {
            'labels': weekly_labels,
            'registrations': weekly_regs,
            'attendances': weekly_att
        },
        'weekly': {
            'labels': weekly_labels,
            'registrations': weekly_regs,
            'attendances': weekly_att
        },
        'month': {
            'labels': monthly_labels,
            'registrations': monthly_regs,
            'attendances': monthly_att
        },
        'monthly': {
            'labels': monthly_labels,
            'registrations': monthly_regs,
            'attendances': monthly_att
        },
        'quarter': {
            'labels': quarterly_labels,
            'registrations': quarterly_regs,
            'attendances': quarterly_att
        },
        'quarterly': {
            'labels': quarterly_labels,
            'registrations': quarterly_regs,
            'attendances': quarterly_att
        },
        'year': {
            'labels': yearly_labels,
            'registrations': yearly_regs,
            'attendances': yearly_att
        },
        'yearly': {
            'labels': yearly_labels,
            'registrations': yearly_regs,
            'attendances': yearly_att
        }
    }

    # Available organizers for filter dropdown (if Manager)
    available_organizers = [r[0] for r in db.session.query(Event.organizer_name).distinct().order_by(Event.organizer_name).all() if r[0]]
    available_categories = EventCategory.query.order_by(EventCategory.id).all()

    return {
        'stats': stats,
        'events': display_events,
        'category_data': category_data,
        'bar_chart_data': bar_chart_data,
        'available_organizers': available_organizers,
        'available_categories': available_categories,
        'selected_period': period or 'ALL',
        'selected_organizer': organizer or 'ALL',
        'selected_category': category_id or 'ALL',
        'start_d': start_d,
        'end_d': end_d
    }

@app.route('/analytics')
@login_required
def analytics():
    if current_user.role not in ['ORGANIZER', 'MANAGER']:
        flash('Bạn không có quyền truy cập trang Báo cáo – thống kê.', 'error')
        return redirect(url_for('events'))

    analytics_data = get_analytics_data(current_user, request.args, session)

    return render_template(
        'analytics.html',
        stats=analytics_data['stats'],
        events=analytics_data['events'],
        category_data=analytics_data['category_data'],
        bar_chart_data=analytics_data['bar_chart_data'],
        available_organizers=analytics_data['available_organizers'],
        available_categories=analytics_data['available_categories'],
        selected_period=analytics_data['selected_period'],
        selected_organizer=analytics_data['selected_organizer'],
        selected_category=analytics_data['selected_category']
    )

@app.route('/analytics/export')
@login_required
def export_analytics():
    if current_user.role not in ['ORGANIZER', 'MANAGER']:
        flash('Bạn không có quyền xuất báo cáo thống kê.', 'error')
        return redirect(url_for('events'))

    export_format = request.args.get('format', 'xlsx').lower()
    analytics_data = get_analytics_data(current_user, request.args, session)
    display_events = analytics_data['events']
    stats = analytics_data['stats']
    events_count = stats['events']
    regs_count = stats['registrations']
    att_count = stats['attended']
    rate = stats['rate']
    raw_period = analytics_data['selected_period']
    if raw_period == 'THIS_WEEK':
        academic_year = 'Tuần hiện tại'
    elif raw_period == 'THIS_MONTH':
        academic_year = f'Tháng {date.today().strftime("%m/%Y")}'
    elif raw_period == 'THIS_QUARTER':
        academic_year = f'Quý {(date.today().month - 1) // 3 + 1}/{date.today().year}'
    elif raw_period == 'THIS_YEAR':
        academic_year = f'Năm {date.today().year}'
    elif raw_period == 'ALL':
        academic_year = 'Toàn bộ thời gian'
    else:
        academic_year = raw_period or 'Tất cả'
    semester = request.args.get('semester') or ''

    now_str = datetime.now().strftime('%H:%M %d/%m/%Y')
    date_file_str = date.today().strftime('%Y%m%d')

    if export_format == 'csv':
        # CSV with UTF-8 BOM
        si = StringIO()
        si.write('\ufeff')
        cw = csv.writer(si)
        cw.writerow(['BÁO CÁO THỐNG KÊ HOẠT ĐỘNG SỰ KIỆN - NEU EVENTS'])
        cw.writerow([f'Thời gian xuất: {now_str}', f'Người xuất: {current_user.full_name} ({current_user.email})'])
        cw.writerow([f'Năm học: {academic_year or "Tất cả"}', f'Học kỳ: {semester or "Tất cả"}'])
        cw.writerow([])
        cw.writerow(['TỔNG QUAN CHỈ SỐ KPI'])
        cw.writerow(['Tổng số sự kiện', 'Tổng lượt đăng ký', 'Tổng lượt tham dự', 'Tỷ lệ tham dự chung'])
        cw.writerow([events_count, regs_count, att_count, f'{rate}%'])
        cw.writerow([])
        cw.writerow(['DANH SÁCH CHI TIẾT HIỆU QUẢ TỪNG SỰ KIỆN'])
        cw.writerow(['STT', 'Mã sự kiện', 'Tên sự kiện', 'Ngày tổ chức', 'Đơn vị tổ chức', 'Địa điểm', 'Đăng ký', 'Tham dự', 'Tỷ lệ tham dự', 'Đánh giá', 'Trạng thái'])
        for idx, ev in enumerate(display_events, 1):
            att_seats = ev.attended_seats if ev.event_date <= date.today() else '—'
            st_text = 'Đang diễn ra' if (ev.status == 'APPROVED' and ev.event_date == date.today()) else ('Đã hủy' if ev.status == 'CANCELLED' else ('Đã kết thúc' if (ev.status == 'COMPLETED' or ev.event_date < date.today()) else ('Chờ duyệt' if ev.status == 'PENDING' else 'Sắp diễn ra')))
            cw.writerow([
                idx,
                ev.code,
                ev.title,
                ev.event_date.strftime('%d/%m/%Y'),
                ev.organizer_name,
                ev.location,
                ev.registered_seats,
                att_seats,
                f'{ev.attendance_rate}%',
                f'{ev.average_rating} / 5' if ev.average_rating else 'Chưa có',
                st_text
            ])
        output_bytes = si.getvalue().encode('utf-8-sig')
        filename = f"Bao_cao_thong_ke_NEU_Events_{date_file_str}.csv"
        return Response(
            output_bytes,
            mimetype="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )

    elif export_format == 'pdf':
        return render_template(
            'analytics_report_pdf.html',
            stats=stats,
            events=display_events,
            academic_year=academic_year,
            semester=semester,
            export_time=now_str
        )

    # Default: Professional Excel (.xlsx) using openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Bao_cao_thong_ke"
    ws.views.sheetView[0].showGridLines = True

    # Styling definitions
    font_title = Font(name="Calibri", size=14, bold=True, color="002B49")
    font_sub = Font(name="Calibri", size=10, italic=True, color="475569")
    font_header = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    font_kpi_head = Font(name="Calibri", size=10, bold=True, color="1E3A8A")
    font_kpi_val = Font(name="Calibri", size=12, bold=True, color="002B49")
    font_data = Font(name="Calibri", size=10, color="0F172A")

    fill_header = PatternFill(start_color="002B49", end_color="002B49", fill_type="solid")
    fill_kpi = PatternFill(start_color="EFF6FF", end_color="EFF6FF", fill_type="solid")
    fill_zebra = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")

    thin_border_side = Side(border_style="thin", color="CBD5E1")
    border_cell = Border(left=thin_border_side, right=thin_border_side, top=thin_border_side, bottom=thin_border_side)

    align_center = Alignment(horizontal="center", vertical="center")
    align_left = Alignment(horizontal="left", vertical="center")
    align_right = Alignment(horizontal="right", vertical="center")

    # Row 1: Title
    ws.merge_cells("A1:K1")
    cell_title = ws["A1"]
    cell_title.value = "BÁO CÁO THỐNG KÊ TỔNG HỢP HIỆU QUẢ HOẠT ĐỘNG SỰ KIỆN NEU"
    cell_title.font = font_title
    cell_title.alignment = align_center
    ws.row_dimensions[1].height = 28

    # Row 2: Subtitle
    ws.merge_cells("A2:K2")
    cell_sub = ws["A2"]
    cell_sub.value = f"Thời gian xuất: {now_str}  |  Người lập: {current_user.full_name} ({current_user.email})  |  Năm học: {academic_year or 'Tất cả'}  |  Học kỳ: {semester or 'Tất cả'}"
    cell_sub.font = font_sub
    cell_sub.alignment = align_center
    ws.row_dimensions[2].height = 20

    # Row 4: KPI Summary Table
    ws["B4"] = "Tổng số sự kiện"
    ws["D4"] = "Tổng lượt đăng ký"
    ws["F4"] = "Tổng lượt tham dự"
    ws["H4"] = "Tỷ lệ tham dự chung"
    for col_l in ["B4", "D4", "F4", "H4"]:
        ws[col_l].font = font_kpi_head
        ws[col_l].alignment = align_center
        ws[col_l].fill = fill_kpi
        ws[col_l].border = border_cell

    ws["B5"] = events_count
    ws["D5"] = regs_count
    ws["F5"] = att_count
    ws["H5"] = f"{rate}%"
    for col_l in ["B5", "D5", "F5", "H5"]:
        ws[col_l].font = font_kpi_val
        ws[col_l].alignment = align_center
        ws[col_l].border = border_cell
    ws.row_dimensions[4].height = 22
    ws.row_dimensions[5].height = 24

    # Row 7: Data Table Header
    headers = ['STT', 'Mã sự kiện', 'Tên sự kiện', 'Ngày tổ chức', 'Đơn vị tổ chức', 'Địa điểm', 'Đăng ký', 'Tham dự', 'Tỷ lệ', 'Đánh giá', 'Trạng thái']
    ws.row_dimensions[7].height = 26
    for col_idx, h in enumerate(headers, 1):
        cell = ws.cell(row=7, column=col_idx, value=h)
        cell.font = font_header
        cell.fill = fill_header
        cell.alignment = align_center
        cell.border = border_cell

    # Rows 8+: Events Data
    for row_idx, ev in enumerate(display_events, 8):
        att_seats = ev.attended_seats if ev.event_date <= date.today() else '—'
        st_text = 'Đang diễn ra' if (ev.status == 'APPROVED' and ev.event_date == date.today()) else ('Đã hủy' if ev.status == 'CANCELLED' else ('Đã kết thúc' if (ev.status == 'COMPLETED' or ev.event_date < date.today()) else ('Chờ duyệt' if ev.status == 'PENDING' else 'Sắp diễn ra')))
        row_vals = [
            row_idx - 7,
            ev.code,
            ev.title,
            ev.event_date.strftime('%d/%m/%Y'),
            ev.organizer_name,
            ev.location,
            ev.registered_seats,
            att_seats,
            f"{ev.attendance_rate}%",
            f"{ev.average_rating} / 5" if ev.average_rating else "Chưa có",
            st_text
        ]
        ws.row_dimensions[row_idx].height = 22
        is_even = (row_idx % 2 == 0)
        for col_idx, val in enumerate(row_vals, 1):
            cell = ws.cell(row=row_idx, column=col_idx, value=val)
            cell.font = font_data
            cell.border = border_cell
            if is_even:
                cell.fill = fill_zebra
            if col_idx in [1, 2, 4, 9, 10, 11]:
                cell.alignment = align_center
            elif col_idx in [7, 8]:
                cell.alignment = align_right
            else:
                cell.alignment = align_left

    # Auto-adjust column widths
    for col_idx in range(1, 12):
        col_letter = get_column_letter(col_idx)
        max_len = 0
        for row in range(7, len(display_events) + 8):
            cell_val = ws.cell(row=row, column=col_idx).value
            v_str = str(cell_val or '')
            if len(v_str) > max_len:
                max_len = len(v_str)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    filename = f"Bao_cao_thong_ke_NEU_Events_{date_file_str}.xlsx"
    return Response(
        buf.getvalue(),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

# ----------------- APP INITIALIZATION -----------------

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Automatically seed compact clean dataset if missing
        if User.query.count() == 0 or Event.query.count() == 0:
            from data_seeder import seed_database
            seed_database(app)
    print("Starting NEU Events Web Server at http://127.0.0.1:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
