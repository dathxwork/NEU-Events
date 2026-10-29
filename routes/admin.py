from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy import or_

from models import db, User, Event, Registration, AttendanceRecord, Feedback, ApprovalLog

admin_bp = Blueprint('admin', __name__)

# ----------------- SYSTEM ADMINISTRATION (ADMIN) -----------------

@admin_bp.route('/admin/users')
@login_required
def admin_users():
    if current_user.role != 'ADMIN':
        flash('Bạn không có quyền truy cập trang Quản trị tài khoản & Phân quyền.', 'error')
        return redirect(url_for('events'))

    role_filter = request.args.get('role', 'ALL').strip().upper()
    search_q = request.args.get('q', '').strip()

    stats = {
        'total': User.query.count(),
        'admins': User.query.filter_by(role='ADMIN').count(),
        'managers': User.query.filter_by(role='MANAGER').count(),
        'organizers': User.query.filter_by(role='ORGANIZER').count(),
        'students': User.query.filter_by(role='STUDENT').count()
    }

    q = User.query
    if role_filter in ['ADMIN', 'MANAGER', 'ORGANIZER', 'STUDENT']:
        q = q.filter_by(role=role_filter)
    else:
        role_filter = 'ALL'

    if search_q:
        search_pattern = f"%{search_q}%"
        q = q.filter(
            or_(
                User.full_name.ilike(search_pattern),
                User.email.ilike(search_pattern),
                User.username.ilike(search_pattern),
                User.department.ilike(search_pattern),
                User.student_id.ilike(search_pattern),
                User.phone.ilike(search_pattern)
            )
        )

    users = q.order_by(User.id.asc()).all()

    return render_template(
        'admin_users.html',
        users=users,
        stats=stats,
        current_role=role_filter,
        q=search_q
    )

@admin_bp.route('/admin/users/create', methods=['POST'])
@login_required
def admin_create_user():
    if current_user.role != 'ADMIN':
        flash('Bạn không có quyền thực hiện thao tác này.', 'error')
        return redirect(url_for('events'))

    full_name = request.form.get('full_name', '').strip()
    email = request.form.get('email', '').strip().lower()
    username = request.form.get('username', '').strip() or email
    role = request.form.get('role', 'STUDENT').strip().upper()
    department = request.form.get('department', '').strip()
    phone = request.form.get('phone', '').strip()
    student_id = request.form.get('student_id', '').strip() or None
    password = request.form.get('password', '123').strip() or '123'

    if not full_name or not email:
        flash('Vui lòng điền đầy đủ Họ và tên cùng Email.', 'error')
        return redirect(url_for('admin_users'))

    if role not in ['ADMIN', 'MANAGER', 'ORGANIZER', 'STUDENT']:
        role = 'STUDENT'

    # Check if email or username already exists
    if User.query.filter((User.email == email) | (User.username == username)).first():
        flash(f'Tài khoản với email "{email}" hoặc tên đăng nhập "{username}" đã tồn tại trên hệ thống!', 'error')
        return redirect(url_for('admin_users'))

    words = [w for w in full_name.split() if w]
    initials = ''.join([w[0].upper() for w in words[:2]]) if words else 'NEU'
    if role == 'ADMIN':
        initials = 'ADM'
    elif role == 'MANAGER':
        initials = 'QL'

    new_user = User(
        email=email,
        username=username,
        full_name=full_name,
        role=role,
        department=department or 'Đại học Kinh tế Quốc dân',
        phone=phone or None,
        student_id=student_id if role == 'STUDENT' else None,
        avatar_initials=initials
    )
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()

    flash(f'Tạo thành công tài khoản {full_name} ({email}) với vai trò {new_user.role_label}!', 'success')
    return redirect(url_for('admin_users', role=role))

@admin_bp.route('/admin/users/<int:user_id>/update-role', methods=['POST'])
@login_required
def admin_update_user_role(user_id):
    if current_user.role != 'ADMIN':
        flash('Bạn không có quyền thực hiện thao tác này.', 'error')
        return redirect(url_for('events'))

    target_user = User.query.get_or_404(user_id)
    new_role = request.form.get('role', '').strip().upper()
    department = request.form.get('department', '').strip()

    if target_user.id == current_user.id and new_role != 'ADMIN':
        flash('Bạn không thể tự hạ quyền Quản trị viên của chính mình!', 'error')
        return redirect(url_for('admin_users'))

    if new_role not in ['ADMIN', 'MANAGER', 'ORGANIZER', 'STUDENT']:
        flash('Phân quyền không hợp lệ.', 'error')
        return redirect(url_for('admin_users'))

    target_user.role = new_role
    if department:
        target_user.department = department

    if new_role == 'ADMIN':
        target_user.avatar_initials = 'ADM'
    elif new_role == 'MANAGER':
        target_user.avatar_initials = 'QL'

    db.session.commit()
    flash(f'Đã cập nhật phân quyền tài khoản {target_user.full_name} sang vai trò {target_user.role_label}!', 'success')
    return redirect(url_for('admin_users', role=new_role))

@admin_bp.route('/admin/users/<int:user_id>/edit', methods=['POST'])
@login_required
def admin_edit_user(user_id):
    if current_user.role != 'ADMIN':
        flash('Bạn không có quyền thực hiện thao tác này.', 'error')
        return redirect(url_for('events'))

    target_user = User.query.get_or_404(user_id)
    full_name = request.form.get('full_name', '').strip()
    email = request.form.get('email', '').strip().lower()
    department = request.form.get('department', '').strip()
    phone = request.form.get('phone', '').strip()
    new_role = request.form.get('role', '').strip().upper()

    if not full_name or not email:
        flash('Họ và tên cùng Email không được để trống.', 'error')
        return redirect(url_for('admin_users'))

    existing = User.query.filter(User.email == email, User.id != target_user.id).first()
    if existing:
        flash(f'Email {email} đã được sử dụng bởi tài khoản khác!', 'error')
        return redirect(url_for('admin_users'))

    if target_user.id == current_user.id and new_role != 'ADMIN':
        flash('Bạn không thể tự hạ quyền Quản trị viên của chính mình!', 'error')
        new_role = 'ADMIN'

    target_user.full_name = full_name
    target_user.email = email
    if department:
        target_user.department = department
    target_user.phone = phone or target_user.phone
    if new_role in ['ADMIN', 'MANAGER', 'ORGANIZER', 'STUDENT']:
        target_user.role = new_role

    db.session.commit()
    flash(f'Đã cập nhật thông tin tài khoản {target_user.full_name} thành công!', 'success')
    return redirect(url_for('admin_users'))

@admin_bp.route('/admin/users/<int:user_id>/reset-password', methods=['POST'])
@login_required
def admin_reset_password(user_id):
    if current_user.role != 'ADMIN':
        flash('Bạn không có quyền thực hiện thao tác này.', 'error')
        return redirect(url_for('events'))

    target_user = User.query.get_or_404(user_id)
    new_pass = request.form.get('new_password', '123').strip() or '123'
    target_user.set_password(new_pass)
    db.session.commit()

    flash(f'Đã đặt lại mật khẩu cho tài khoản {target_user.email} về mặc định "{new_pass}" thành công!', 'success')
    return redirect(url_for('admin_users'))

@admin_bp.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@login_required
def admin_delete_user(user_id):
    if current_user.role != 'ADMIN':
        flash('Bạn không có quyền thực hiện thao tác này.', 'error')
        return redirect(url_for('events'))

    target_user = User.query.get_or_404(user_id)
    if target_user.id == current_user.id:
        flash('Bạn không thể tự xóa tài khoản Quản trị viên đang đăng nhập!', 'error')
        return redirect(url_for('admin_users'))

    ev_count = Event.query.filter_by(organizer_id=target_user.id).count()
    if ev_count > 0:
        flash(f'Không thể xóa tài khoản {target_user.full_name} vì đang sở hữu {ev_count} sự kiện trong hệ thống. Vui lòng chuyển quyền hoặc chuyển người phụ trách sự kiện trước khi xóa.', 'error')
        return redirect(url_for('admin_users'))

    Registration.query.filter_by(user_id=target_user.id).delete()
    AttendanceRecord.query.filter_by(user_id=target_user.id).delete()
    Feedback.query.filter_by(user_id=target_user.id).delete()
    ApprovalLog.query.filter_by(manager_id=target_user.id).delete()

    user_email = target_user.email
    db.session.delete(target_user)
    db.session.commit()

    flash(f'Đã xóa hoàn toàn tài khoản {user_email} khỏi hệ thống!', 'info')
    return redirect(url_for('admin_users'))
