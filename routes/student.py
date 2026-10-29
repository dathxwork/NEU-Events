"""
NEU Events - Student Space Routes (Phân quyền Sinh viên)
Handles event discovery, event details, registration, ticket access, personal schedule, and evaluation.
"""
import random
import math
from datetime import datetime, date, timedelta
from flask import (
    Blueprint, render_template, request, redirect, url_for,
    flash, jsonify, session
)
from flask_login import login_required, current_user
from sqlalchemy import extract
from models import db, User, EventCategory, Event, Registration, Feedback
from routes.utils import get_period_date_range

student_bp = Blueprint('student', __name__)

# ----------------- 1. DISCOVERY & EVENT LIST -----------------

@student_bp.route('/events')
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
    else:  # all approved / completed / cancelled
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
                query = query.filter(extract('month', Event.event_date) == m, extract('year', Event.event_date) == y)
        except Exception:
            pass

    # Pagination setup (6 events per page)
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

    # Featured event selection strictly scoped to the selected academic period
    featured_q = Event.query.filter_by(is_featured=True)
    if start_d:
        featured_q = featured_q.filter(Event.event_date >= start_d)
    if end_d:
        featured_q = featured_q.filter(Event.event_date <= end_d)
    featured = featured_q.order_by(Event.event_date.asc()).first()

    # Fallback 1: First event from current tab query
    if not featured and all_matched_events:
        featured = all_matched_events[0]

    # Fallback 2: Any event in the selected academic period (if tab is empty for past years, e.g. 'upcoming')
    if not featured and (start_d or end_d):
        period_fallback_q = Event.query.filter(Event.status.in_(['APPROVED', 'COMPLETED', 'CANCELLED']))
        if start_d:
            period_fallback_q = period_fallback_q.filter(Event.event_date >= start_d)
        if end_d:
            period_fallback_q = period_fallback_q.filter(Event.event_date <= end_d)
        featured = period_fallback_q.order_by(Event.event_date.asc()).first()

    # Fallback 3: Global featured
    if not featured:
        featured = Event.query.filter_by(is_featured=True).first() or Event.query.first()

    categories = EventCategory.query.all()

    # Prepare Calendar Months Data
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
        cal = py_calendar.Calendar(firstweekday=0)
        month_days = cal.monthdayscalendar(m_year, m_month)

        month_events = [e for e in all_matched_events if e.event_date.year == m_year and e.event_date.month == m_month]

        calendar_months.append({
            'year': m_year,
            'month': m_month,
            'month_name': f"Tháng {m_month:02d}/{m_year}",
            'weeks': month_days,
            'events': month_events
        })

    # Available time filter options (sorted distinct months)
    available_time_filters = []
    distinct_months = sorted(list(set((e.event_date.month, e.event_date.year) for e in all_matched_events)), key=lambda x: (x[1], x[0]))
    for (m_val, y_val) in distinct_months:
        available_time_filters.append({
            'value': f"{m_val}/{y_val}",
            'label': f"Tháng {m_val:02d}/{y_val}"
        })

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

@student_bp.route('/events/<int:event_id>')
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

@student_bp.route('/events/<int:event_id>/register', methods=['POST'])
@login_required
def register_event(event_id):
    if current_user.role != 'STUDENT':
        flash('Chỉ tài khoản sinh viên mới được đăng ký tham gia sự kiện. Ban tổ chức và Quản lý không thể đăng ký.', 'warning')
        return redirect(url_for('event_detail', event_id=event_id))

    event = Event.query.get_or_404(event_id)

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

@student_bp.route('/registrations/<int:reg_id>/cancel', methods=['POST'])
@login_required
def cancel_registration(reg_id):
    reg = Registration.query.get_or_404(reg_id)
    if reg.user_id != current_user.id and current_user.role not in ['ORGANIZER', 'MANAGER', 'ADMIN']:
        flash('Bạn không có quyền thực hiện thao tác này.', 'error')
        return redirect(url_for('my_events'))

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

@student_bp.route('/my-events')
@login_required
def my_events():
    if current_user.role != 'STUDENT':
        flash('Mục "Sự kiện đã đăng ký" chỉ dành riêng cho sinh viên.', 'info')
        return redirect(url_for('organizer_events') if current_user.role == 'ORGANIZER' else (url_for('moderation') if current_user.role in ['MANAGER', 'ADMIN'] else url_for('events')))

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

@student_bp.route('/api/ticket/<ticket_code>', methods=['GET'])
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

# ----------------- 4. FEEDBACK & EVALUATION -----------------

@student_bp.route('/feedback')
@login_required
def feedback():
    if current_user.role in ['MANAGER', 'ADMIN']:
        flash('Đơn vị Quản lý và Quản trị viên không có quyền truy cập chức năng đánh giá sự kiện.', 'warning')
        return redirect(url_for('events'))

    selected_event_id = request.args.get('event_id')
    if selected_event_id and selected_event_id.isdigit():
        selected_event_id = int(selected_event_id)
    else:
        selected_event_id = None

    if current_user.role == 'ORGANIZER':
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
        user_attended_regs = Registration.query.filter_by(
            user_id=current_user.id,
            attendance_status='ATTENDED'
        ).order_by(Registration.registered_at.desc()).all()
        attended_events = [r.event for r in user_attended_regs if r.event]

        my_feedbacks = Feedback.query.filter_by(user_id=current_user.id).order_by(Feedback.created_at.desc()).all()
        feedback_map = {fb.event_id: fb for fb in my_feedbacks}

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

        selected_event = None
        if selected_event_id:
            selected_event = next((e for e in attended_events if e.id == selected_event_id), None)
        if not selected_event:
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

@student_bp.route('/feedback/submit', methods=['POST'])
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

    reg = Registration.query.filter_by(
        event_id=event_id,
        user_id=current_user.id,
        attendance_status='ATTENDED'
    ).first()

    if not reg:
        flash('Chỉ những sinh viên đã điểm danh tham dự mới có quyền đánh giá sự kiện này.', 'error')
        return redirect(url_for('feedback'))

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
