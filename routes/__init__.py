"""
NEU Events - Routes Package
Blueprints and routes partitioned by user role:
- auth.py: Xác thực tài khoản & tiện ích dùng chung
- student.py: Phân quyền Sinh viên (Khám phá sự kiện, Đăng ký, Vé điện tử, Đánh giá)
- organizer.py: Phân quyền Ban tổ chức (Quản lý sự kiện, Điểm danh QR/PIN/thủ công, Xuất danh sách)
- manager.py: Phân quyền Đơn vị quản lý (Kiểm duyệt sự kiện, Báo cáo & Thống kê KPI, Xuất báo cáo)
- admin.py: Phân quyền Quản trị viên (Quản trị tài khoản người dùng, Phân quyền hệ thống)
"""

from .auth import auth_bp
from .student import student_bp
from .organizer import organizer_bp
from .manager import manager_bp
from .admin import admin_bp
from .utils import get_period_date_range, get_user_notifications, get_pending_count, format_event_time

__all__ = [
    'auth_bp',
    'student_bp',
    'organizer_bp',
    'manager_bp',
    'admin_bp',
    'get_period_date_range',
    'get_user_notifications',
    'get_pending_count',
    'format_event_time'
]
