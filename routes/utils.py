"""
NEU Events - Shared Route Utilities & Helpers
"""
from datetime import datetime, date, time
from models import db, User, Event, Registration, Feedback

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


def get_pending_count():
    return Event.query.filter_by(status='PENDING').count()


def get_user_notifications(user):
    if not user or not getattr(user, 'is_authenticated', False):
        return []

    notifications = []
    now_dt = datetime.now()
    now_time_str = now_dt.strftime('%H:%M %d/%m/%Y')

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

    elif user.role in ['MANAGER', 'ADMIN']:
        if user.role == 'ADMIN':
            user_count = User.query.count()
            notifications.append({
                'id': 'notif_admin_users_info',
                'title': 'Hệ thống tài khoản & Phân quyền',
                'message': f'Hệ thống đang quản lý <strong>{user_count} tài khoản</strong>. Bạn có quyền cấp quyền Đơn vị quản lý và Ban tổ chức.<br><span class="inline-flex items-center gap-1 mt-1 text-[11px] text-rose-700 font-medium"><i class="fa-solid fa-users-gear text-[10px]"></i>Quản trị viên toàn quyền</span>',
                'time': now_time_str,
                'icon': 'fa-solid fa-user-shield',
                'icon_color': 'text-rose-600',
                'icon_bg': 'bg-rose-50 border-rose-100',
                'link': '/admin/users',
                'unread': False,
                'tag': 'Quản trị'
            })
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
