import csv
import calendar
from datetime import datetime, date, timedelta
from io import StringIO, BytesIO
from flask import Blueprint, render_template, request, redirect, url_for, flash, Response, session
from flask_login import login_required, current_user
import openpyxl
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from openpyxl.utils import get_column_letter

from models import db, User, Event, EventCategory, Registration, ApprovalLog
from routes.utils import get_period_date_range

manager_bp = Blueprint('manager', __name__)

# ----------------- MODERATION (MANAGER & ADMIN) -----------------

@manager_bp.route('/moderation')
@login_required
def moderation():
    if current_user.role not in ['MANAGER', 'ADMIN']:
        flash('Bạn không có quyền truy cập phân hệ Kiểm duyệt sự kiện.', 'error')
        return redirect(url_for('events'))

    pending = Event.query.filter_by(status='PENDING').order_by(Event.created_at.desc()).all()
    approved = Event.query.filter_by(status='APPROVED').order_by(Event.event_date.desc()).limit(10).all()

    return render_template(
        'moderation.html',
        pending_events=pending,
        approved_events=approved
    )

@manager_bp.route('/moderation/approve/<int:event_id>', methods=['POST'])
@login_required
def approve_event(event_id):
    if current_user.role not in ['MANAGER', 'ADMIN']:
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

@manager_bp.route('/moderation/reject/<int:event_id>', methods=['POST'])
@login_required
def reject_event(event_id):
    if current_user.role not in ['MANAGER', 'ADMIN']:
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

# ----------------- REPORTS & ANALYTICS -----------------

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

    # Timeline Bar Chart Data (Weekly, Monthly, Quarterly, Yearly)
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

@manager_bp.route('/analytics')
@login_required
def analytics():
    if current_user.role not in ['ORGANIZER', 'MANAGER', 'ADMIN']:
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

@manager_bp.route('/analytics/export')
@login_required
def export_analytics():
    if current_user.role not in ['ORGANIZER', 'MANAGER', 'ADMIN']:
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
