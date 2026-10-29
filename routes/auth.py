"""
NEU Events - Authentication & Core Routes
Handles login, logout, password reset, role switching, notification APIs, and period switching.
"""
from flask import (
    Blueprint, render_template, request, redirect, url_for,
    flash, jsonify, session
)
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User
from routes.utils import get_user_notifications

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('events'))
    return redirect(url_for('login'))

@auth_bp.route('/login', methods=['GET', 'POST'])
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
        if user.role == 'ADMIN':
            flash('Chào mừng Quản trị viên hệ thống đã đăng nhập thành công!', 'success')
        elif user.role == 'MANAGER':
            flash('Chào mừng Đơn vị quản lý đã đăng nhập thành công!', 'success')
        elif user.role == 'ORGANIZER':
            flash(f'Chào mừng Ban tổ chức ({user.full_name}) đã đăng nhập thành công!', 'success')
        else:
            flash(f'Chào mừng sinh viên {user.full_name} đã đăng nhập thành công!', 'success')
        next_page = request.args.get('next')
        return redirect(next_page or url_for('events'))

    return render_template('login.html', login_id=login_id)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Bạn đã đăng xuất an toàn khỏi hệ thống NEU Events.', 'info')
    return redirect(url_for('login'))

@auth_bp.route('/set-password', methods=['POST'])
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

@auth_bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    """Allow Organizer, Manager, Student, and Admin to change their assigned password"""
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

@auth_bp.route('/switch-role/<role>')
@login_required
def switch_role(role):
    """Disable public role switching for security"""
    flash('Chức năng chuyển đổi nhanh đã bị vô hiệu hóa vì lý do bảo mật. Vui lòng đăng nhập đúng tài khoản được cấp.', 'warning')
    return redirect(request.referrer or url_for('events'))

@auth_bp.route('/api/check-student', methods=['GET'])
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

@auth_bp.route('/api/set-period', methods=['POST'])
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

@auth_bp.route('/api/notifications', methods=['GET'])
@login_required
def api_notifications():
    notifs = get_user_notifications(current_user)
    unread_count = sum(1 for n in notifs if n.get('unread'))
    return jsonify({
        'success': True,
        'notifications': notifs,
        'unread_count': unread_count
    })

@auth_bp.route('/api/notifications/read-all', methods=['POST'])
@login_required
def api_notifications_read_all():
    return jsonify({'success': True, 'unread_count': 0})

@auth_bp.route('/api/notifications/clear', methods=['POST'])
@login_required
def api_notifications_clear():
    return jsonify({'success': True, 'notifications': [], 'unread_count': 0})
