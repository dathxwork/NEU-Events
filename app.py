"""
NEU Events - Cổng Quản lý và Tổ chức Sự kiện Đại học Kinh tế Quốc dân
Main Flask Web Application
"""
import os
import random
from datetime import datetime, date, time
from io import StringIO
import csv
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, jsonify, Response
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

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Vui lòng đăng nhập để tiếp tục.'
login_manager.login_message_category = 'warning'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Context Processors for Templates
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

    return dict(
        today=today,
        now=now,
        current_year=today.year,
        current_month_year=today.strftime('%m/%Y'),
        current_date_str=today.strftime('%d/%m/%Y'),
        get_pending_count=get_pending_count,
        is_reviewed=is_reviewed
    )

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

    query = Event.query

    # Status tab filtering
    today = date.today()
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

    events_list = query.order_by(Event.event_date.asc()).all()

    # Calculate counts for tabs
    counts = {
        'all': Event.query.filter(Event.status.in_(['APPROVED', 'COMPLETED', 'CANCELLED'])).count(),
        'upcoming': Event.query.filter(Event.status == 'APPROVED', Event.event_date > today).count(),
        'active': Event.query.filter(Event.status == 'APPROVED', Event.event_date == today).count(),
        'completed': Event.query.filter(Event.status == 'COMPLETED').count(),
        'cancelled': Event.query.filter(Event.status == 'CANCELLED').count()
    }

    featured = Event.query.filter_by(is_featured=True).first()
    categories = EventCategory.query.all()

    return render_template(
        'events.html',
        events=events_list,
        categories=categories,
        featured_event=featured,
        current_tab=tab,
        counts=counts
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
        registered_at=datetime.utcnow()
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

    query = Registration.query.filter_by(user_id=current_user.id)

    if filter_type == 'upcoming':
        query = query.join(Event).filter(Event.event_date >= today, Registration.registration_status == 'REGISTERED', Registration.attendance_status != 'ATTENDED')
    elif filter_type == 'attended':
        query = query.filter_by(attendance_status='ATTENDED')
    elif filter_type == 'absent':
        query = query.filter_by(attendance_status='ABSENT')
    elif filter_type == 'cancelled':
        query = query.join(Event).filter((Event.status == 'CANCELLED') | (Registration.registration_status == 'CANCELLED'))

    user_registrations = query.order_by(Registration.registered_at.desc()).all()

    # KPI Statistics
    all_regs = Registration.query.filter_by(user_id=current_user.id).all()
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
    if current_user.role != 'ORGANIZER':
        flash('Bạn không có quyền xuất danh sách điểm danh. Quyền này chỉ dành riêng cho Ban tổ chức!', 'error')
        return redirect(url_for('events'))

    event = Event.query.get_or_404(event_id)
    # Check if organizer owns this event
    if event.organizer_id != current_user.id:
        flash('Bạn không có quyền xuất danh sách của sự kiện do Ban tổ chức khác tổ chức!', 'error')
        return redirect(url_for('events'))

    registrations = Registration.query.filter_by(event_id=event.id, registration_status='REGISTERED').all()

    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['MSSV', 'Ho va ten', 'Email', 'Khoa/Phong ban', 'Ma ve', 'Trang thai tham du', 'Thoi gian diem danh'])

    for r in registrations:
        att_time = r.attendance_record.checked_in_at.strftime('%H:%M %d/%m/%Y') if r.attendance_record else 'Chua diem danh'
        cw.writerow([
            r.user.student_id or r.user.username,
            r.user.full_name,
            r.user.email,
            r.user.department or '',
            r.ticket_code,
            'Da tham du' if r.attendance_status == 'ATTENDED' else 'Chua diem danh',
            att_time
        ])

    output = si.getvalue()
    filename = f"Diem_danh_{event.code}_{date.today().strftime('%Y%m%d')}.csv"
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
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

    # Strict isolation: ORGANIZER only sees their own events
    my_events = Event.query.filter_by(organizer_id=current_user.id).order_by(Event.event_date.desc()).all()

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
        flash('Đã lưu thay đổi thông tin sự kiện thành công!', 'success')
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
        # STUDENT VIEW
        user_attended_regs = Registration.query.filter_by(
            user_id=current_user.id,
            attendance_status='ATTENDED'
        ).all()
        attended_events = [r.event for r in user_attended_regs]

        # Student's past submitted feedbacks
        my_feedbacks = Feedback.query.filter_by(user_id=current_user.id).order_by(Feedback.created_at.desc()).all()

        return render_template(
            'feedback.html',
            attended_events=attended_events,
            selected_event_id=selected_event_id,
            my_feedbacks=my_feedbacks
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

    fb = Feedback(
        event_id=event_id,
        user_id=current_user.id,
        rating_stars=rating_stars,
        rating_content=rating_content,
        rating_organization=rating_organization,
        rating_speaker=rating_speaker,
        rating_venue=rating_venue,
        comment=comment,
        is_anonymous=is_anonymous
    )
    db.session.add(fb)
    db.session.commit()

    flash('Cảm ơn bạn đã gửi đánh giá! Ý kiến của bạn sẽ giúp BTC nâng cao chất lượng các sự kiện tiếp theo.', 'success')
    return redirect(url_for('feedback'))

# ----------------- 8. REPORTS & ANALYTICS -----------------

@app.route('/analytics')
@login_required
def analytics():
    if current_user.role not in ['ORGANIZER', 'MANAGER']:
        flash('Bạn không có quyền truy cập trang Báo cáo – thống kê.', 'error')
        return redirect(url_for('events'))

    # Compute real dynamic statistics
    if current_user.role == 'ORGANIZER':
        org_ev_ids = [e.id for e in Event.query.filter_by(organizer_id=current_user.id).all()]
        events_count = len(org_ev_ids)
        regs_count = Registration.query.filter(Registration.event_id.in_(org_ev_ids)).count() if org_ev_ids else 0
        att_count = Registration.query.filter(Registration.event_id.in_(org_ev_ids), Registration.attendance_status == 'ATTENDED').count() if org_ev_ids else 0
    else:
        events_count = Event.query.count()
        regs_count = Registration.query.count()
        att_count = Registration.query.filter_by(attendance_status='ATTENDED').count()

    rate = round(att_count / regs_count * 100, 1) if regs_count > 0 else 0.0

    stats = {
        'events': events_count,
        'registrations': regs_count,
        'attended': att_count,
        'rate': rate
    }

    return render_template('analytics.html', stats=stats)

# ----------------- APP INITIALIZATION -----------------

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Automatically seed compact clean dataset if missing or mismatching
        if User.query.count() != 5 or Event.query.count() != 4:
            from data_seeder import seed_database
            seed_database(app)
    print("Starting NEU Events Web Server at http://127.0.0.1:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
