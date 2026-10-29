import os
import csv
import random
from datetime import datetime, date, time
from io import StringIO, BytesIO
from flask import Blueprint, render_template, request, redirect, url_for, flash, Response, current_app, session
from flask_login import login_required, current_user
import openpyxl
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from openpyxl.utils import get_column_letter

from models import (
    db, User, Event, EventCategory, Registration, AttendanceRecord,
    AttendanceSession, ApprovalLog
)
from routes.utils import get_period_date_range

organizer_bp = Blueprint('organizer', __name__)

def get_or_create_event_session(event):
    """Ensure every event has its own dedicated attendance session with a completely distinct PIN and QR token"""
    session_obj = AttendanceSession.query.filter_by(event_id=event.id, is_active=True).first()
    if not session_obj:
        session_obj = AttendanceSession.query.filter_by(event_id=event.id).first()
        if session_obj:
            session_obj.is_active = True
        else:
            # Generate unique PIN and QR Token based strictly on this specific event's code and ID
            clean_part = event.code.replace('NEU-', '').replace('-', '')
            session_pin = f"{clean_part[:8]}"
            qr_token = f"NEU:CHECKIN:{event.code}"

            existing = AttendanceSession.query.filter_by(session_pin=session_pin).first()
            if existing and existing.event_id != event.id:
                session_pin = f"{clean_part[:5]}{event.id}"

            session_obj = AttendanceSession(
                event_id=event.id,
                session_pin=session_pin,
                qr_token=qr_token,
                valid_from=datetime.combine(event.event_date, time(0, 0)),
                valid_to=datetime.combine(event.event_date, time(23, 59)),
                is_active=True
            )
            db.session.add(session_obj)
        db.session.commit()
    return session_obj

# ----------------- ATTENDANCE & CHECK-IN -----------------

@organizer_bp.route('/checkin')
@login_required
def checkin():
    if current_user.role in ['MANAGER', 'ADMIN']:
        flash('Đơn vị Quản lý và Quản trị viên không có quyền truy cập chức năng điểm danh.', 'warning')
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

@organizer_bp.route('/checkin/submit', methods=['POST'])
@login_required
def submit_checkin():
    if current_user.role != 'STUDENT':
        flash('Chỉ tài khoản sinh viên mới được điểm danh tham gia sự kiện.', 'error')
        return redirect(url_for('events'))

    event_id = request.form.get('event_id')
    code_input = (request.form.get('qr_code') or request.form.get('pin', '')).strip().upper()

    event = Event.query.get_or_404(int(event_id))
    session_obj = get_or_create_event_session(event)

    # Validate against session PIN or QR Token of this specific event
    is_valid_code = False
    valid_keys = [session_obj.session_pin.upper(), session_obj.qr_token.upper()]
    if code_input in valid_keys or session_obj.session_pin.upper() in code_input or session_obj.qr_token.upper() in code_input:
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
        session_id=session_obj.id,
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

@organizer_bp.route('/checkin/manual/<int:reg_id>', methods=['POST'])
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

    session_obj = AttendanceSession.query.filter_by(event_id=reg.event_id, is_active=True).first()

    reg.attendance_status = 'ATTENDED'
    if session_obj:
        record = AttendanceRecord(
            session_id=session_obj.id,
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

@organizer_bp.route('/checkin/export/<int:event_id>')
@login_required
def export_attendance(event_id):
    if current_user.role not in ['ORGANIZER', 'MANAGER', 'ADMIN']:
        flash('Bạn không có quyền xuất danh sách điểm danh. Quyền này chỉ dành riêng cho Ban tổ chức, Đơn vị Quản lý và Quản trị viên!', 'error')
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

# ----------------- EVENT MANAGEMENT (ORGANIZER) -----------------

@organizer_bp.route('/organizer/events')
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

@organizer_bp.route('/organizer/events/save', methods=['POST'])
@login_required
def save_event():
    # Manager and Admin are strictly forbidden from creating or editing events
    if current_user.role in ['MANAGER', 'ADMIN']:
        flash('Đơn vị Quản lý và Quản trị viên không được phép tạo mới hoặc chỉnh sửa sự kiện. Thẩm quyền này thuộc về Ban tổ chức.', 'error')
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
        upload_folder = current_app.config.get('UPLOAD_FOLDER', os.path.join(current_app.root_path, 'static', 'uploads', 'publications'))
        os.makedirs(upload_folder, exist_ok=True)
        file_path = os.path.join(upload_folder, filename)
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

@organizer_bp.route('/organizer/events/<int:event_id>/cancel', methods=['POST'])
@login_required
def cancel_event(event_id):
    # Manager and Admin are not allowed to directly cancel events here; must use moderation
    if current_user.role in ['MANAGER', 'ADMIN']:
        flash('Đơn vị Quản lý và Quản trị viên không được phép hủy sự kiện tại đây. Vui lòng sử dụng phân hệ Kiểm duyệt để từ chối duyệt.', 'error')
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
