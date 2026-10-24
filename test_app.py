"""
Automated Test Suite for NEU Events Management System
Tests authentication, role permissions, discovery, registration, check-in, feedback, and moderation.
Compatible with the 5-user, 4-event compact dataset.
"""
import unittest
from datetime import date
from app import app
from models import db, User, Event, EventCategory, Registration, AttendanceSession, AttendanceRecord, Feedback
from data_seeder import seed_database

class NeuEventsTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        seed_database(app)

    def setUp(self):
        self.client = app.test_client()

    def login(self, username, password):
        return self.client.post('/login', data={
            'username': username,
            'password': password
        }, follow_redirects=True)

    def logout(self):
        return self.client.get('/logout', follow_redirects=True)

    def test_01_login_success_student(self):
        """Test student login with valid credentials (11244035 / 123)"""
        response = self.login('11244035', '123')
        self.assertEqual(response.status_code, 200)
        self.assertIn('Nguyễn Thị Thu'.encode('utf-8'), response.data)
        self.logout()

    def test_02_login_invalid_password(self):
        """Test login fails with incorrect password"""
        response = self.login('11244035', 'wrongpass')
        self.assertEqual(response.status_code, 200)
        self.assertIn('không chính xác'.encode('utf-8'), response.data)

    def test_02b_login_invalid_mssv(self):
        """Test login fails when MSSV is not in NEU student registry"""
        response = self.login('99999999', 'anypassword')
        self.assertEqual(response.status_code, 200)
        self.assertIn('không tồn tại trong danh sách sinh viên Đại học Kinh tế Quốc dân'.encode('utf-8'), response.data)

    def test_02c_check_student_api(self):
        """Test public API for verifying MSSV in NEU database"""
        # Valid student
        res_valid = self.client.get('/api/check-student?student_id=11244035')
        self.assertEqual(res_valid.status_code, 200)
        json_valid = res_valid.get_json()
        self.assertTrue(json_valid['exists'])
        self.assertEqual(json_valid['student_id'], '11244035')
        self.assertEqual(json_valid['full_name'], 'Nguyễn Thị Thu')

        # Invalid student
        res_invalid = self.client.get('/api/check-student?student_id=99999999')
        self.assertEqual(res_invalid.status_code, 200)
        json_invalid = res_invalid.get_json()
        self.assertFalse(json_invalid['exists'])

    def test_03_event_discovery_page(self):
        """Test event listing and keyword search"""
        self.login('11244035', '123')
        response = self.client.get('/events')
        self.assertEqual(response.status_code, 200)
        self.assertIn('Khám phá sự kiện'.encode('utf-8'), response.data)
        self.assertIn(f'Ngày hội việc làm NEU {date.today().year}'.encode('utf-8'), response.data)
        self.logout()

    def test_04_event_detail_page(self):
        """Test viewing event detail for an existing event"""
        self.login('11244035', '123')
        with app.app_context():
            event = Event.query.filter_by(code=f'NEU-JOB-{date.today().year}').first()
            event_id = event.id
        
        response = self.client.get(f'/events/{event_id}')
        self.assertEqual(response.status_code, 200)
        self.assertIn(f'Ngày hội việc làm NEU {date.today().year}'.encode('utf-8'), response.data)
        self.logout()

    def test_05_my_events_page_student_only(self):
        """Test student's registered events schedule page is student-only"""
        # Student access -> OK
        self.login('11244035', '123')
        response = self.client.get('/my-events')
        self.assertEqual(response.status_code, 200)
        self.assertIn('Sự kiện đã đăng ký'.encode('utf-8'), response.data)
        self.logout()

        # Organizer access -> Blocked
        self.login('vieclam@neu.edu.vn', '123')
        org_resp = self.client.get('/my-events', follow_redirects=True)
        self.assertIn('chỉ dành riêng cho sinh viên'.encode('utf-8'), org_resp.data)
        self.logout()

    def test_06_checkin_page_student_view(self):
        """Test check-in page interface for student (QR-scan only and strictly registered events today)"""
        # Student 1 (Thu) has registered for JOB event happening today
        self.login('11244035', '123')
        response = self.client.get('/checkin')
        self.assertEqual(response.status_code, 200)
        self.assertIn('Điểm danh sự kiện'.encode('utf-8'), response.data)
        self.assertIn('Quét mã QR Code'.encode('utf-8'), response.data)
        self.assertNotIn('Quản lý phiên'.encode('utf-8'), response.data)
        # Dropdown only lists events student registered for today -> NEU-JOB is present, NEU-HACK is strictly absent
        self.assertIn(f'NEU-JOB-{date.today().year}'.encode('utf-8'), response.data)
        self.assertNotIn(f'NEU-HACK-{date.today().year}'.encode('utf-8'), response.data)
        self.logout()

        # Student 2 (Anh) has NO registered events today -> shows empty notice
        self.login('11240123', '123')
        res_empty = self.client.get('/checkin')
        self.assertEqual(res_empty.status_code, 200)
        self.assertIn('Không có sự kiện diễn ra hôm nay'.encode('utf-8'), res_empty.data)
        self.logout()

    def test_07_moderation_access_control(self):
        """Test RBAC: Student & Organizer cannot access moderation, but Manager can"""
        # Student access attempt -> Blocked
        self.login('11244035', '123')
        std_resp = self.client.get('/moderation', follow_redirects=True)
        self.assertEqual(std_resp.status_code, 200)
        self.assertIn('không có quyền'.encode('utf-8'), std_resp.data)
        self.logout()

        # Organizer access attempt -> Blocked
        self.login('vieclam@neu.edu.vn', '123')
        org_resp = self.client.get('/moderation', follow_redirects=True)
        self.assertEqual(org_resp.status_code, 200)
        self.assertIn('không có quyền'.encode('utf-8'), org_resp.data)
        self.logout()

        # Manager access attempt -> Allowed
        self.login('quanly@neu.edu.vn', '123')
        mgr_resp = self.client.get('/moderation')
        self.assertEqual(mgr_resp.status_code, 200)
        self.assertIn('Kiểm duyệt sự kiện'.encode('utf-8'), mgr_resp.data)
        self.assertIn('Hội thảo Ứng dụng AI'.encode('utf-8'), mgr_resp.data)
        self.logout()

    def test_08_organizer_events_page(self):
        """Test organizer events management page (strictly for ORGANIZER)"""
        # Organizer access -> Allowed
        self.login('vieclam@neu.edu.vn', '123')
        response = self.client.get('/organizer/events')
        self.assertEqual(response.status_code, 200)
        self.assertIn('Quản lý sự kiện'.encode('utf-8'), response.data)
        self.assertIn(f'Ngày hội việc làm NEU {date.today().year}'.encode('utf-8'), response.data)
        self.logout()

        # Manager access -> Blocked (Manager uses /moderation)
        self.login('quanly@neu.edu.vn', '123')
        mgr_resp = self.client.get('/organizer/events', follow_redirects=True)
        self.assertIn('chỉ dành riêng cho Ban tổ chức'.encode('utf-8'), mgr_resp.data)
        self.logout()

    def test_09_analytics_page(self):
        """Test reports and analytics page accessible by Manager & Organizer, blocked for Student"""
        # Manager -> OK
        self.login('quanly@neu.edu.vn', '123')
        response = self.client.get('/analytics')
        self.assertEqual(response.status_code, 200)
        self.assertIn('Báo cáo – thống kê'.encode('utf-8'), response.data)
        self.logout()

        # Student -> Blocked
        self.login('11244035', '123')
        std_resp = self.client.get('/analytics', follow_redirects=True)
        self.assertIn('không có quyền'.encode('utf-8'), std_resp.data)
        self.logout()

    def test_10_feedback_page_access(self):
        """Test feedback evaluation page accessible by Student and Organizer, blocked for Manager"""
        # Student -> OK
        self.login('11244035', '123')
        response = self.client.get('/feedback')
        self.assertEqual(response.status_code, 200)
        self.assertIn('Đánh giá sự kiện'.encode('utf-8'), response.data)
        self.logout()

        # Manager -> Blocked
        self.login('quanly@neu.edu.vn', '123')
        mgr_resp = self.client.get('/feedback', follow_redirects=True)
        self.assertIn('không có quyền truy cập chức năng đánh giá sự kiện'.encode('utf-8'), mgr_resp.data)
        self.logout()

    def test_11_manager_display_name(self):
        """Test manager login displays 'Đơn vị quản lý'"""
        login_res = self.login('quanly@neu.edu.vn', '123')
        self.assertEqual(login_res.status_code, 200)
        self.assertIn('Đơn vị quản lý'.encode('utf-8'), login_res.data)
        self.logout()

    def test_12_change_password_flow(self):
        """Test user changes password and can authenticate with new password"""
        self.login('vieclam@neu.edu.vn', '123')
        chg_res = self.client.post('/change-password', data={
            'old_password': '123',
            'new_password': 'organizerNewPass2026',
            'confirm_password': 'organizerNewPass2026'
        }, follow_redirects=True)
        self.assertEqual(chg_res.status_code, 200)
        self.assertIn('Đổi mật khẩu thành công'.encode('utf-8'), chg_res.data)
        self.logout()

        # Re-login with new password
        new_login = self.login('vieclam@neu.edu.vn', 'organizerNewPass2026')
        self.assertEqual(new_login.status_code, 200)
        self.logout()

        # Restore password for future tests
        with app.app_context():
            u = User.query.filter_by(username='vieclam@neu.edu.vn').first()
            if u:
                u.set_password('123')
                db.session.commit()

    def test_13_student_qr_checkin(self):
        """Test student self-check-in using QR Code token for active event"""
        self.login('11244035', '123')
        with app.app_context():
            event = Event.query.filter_by(code=f'NEU-JOB-{date.today().year}').first()
            session = AttendanceSession.query.filter_by(event_id=event.id, is_active=True).first()
            event_id = event.id
            pin = session.session_pin

        res = self.client.post('/checkin/submit', data={
            'event_id': str(event_id),
            'qr_code': pin
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn('Điểm danh bằng mã QR thành công'.encode('utf-8'), res.data)

        # Verify record recorded with checkin_method = QR
        with app.app_context():
            u = User.query.filter_by(username='11244035').first()
            reg = Registration.query.filter_by(event_id=event_id, user_id=u.id).first()
            self.assertEqual(reg.attendance_status, 'ATTENDED')
            record = AttendanceRecord.query.filter_by(registration_id=reg.id).first()
            self.assertEqual(record.checkin_method, 'QR')
        self.logout()

    def test_13b_distinct_event_qr_codes_and_cross_rejection(self):
        """Test each event has distinct QR code and cross-event QR scanning is strictly rejected"""
        with app.app_context():
            e_job = Event.query.filter_by(code=f'NEU-JOB-{date.today().year}').first()
            e_hack = Event.query.filter_by(code=f'NEU-HACK-{date.today().year}').first()
            s_job = AttendanceSession.query.filter_by(event_id=e_job.id, is_active=True).first()
            s_hack = AttendanceSession.query.filter_by(event_id=e_hack.id, is_active=True).first()
            
            # Assert QR tokens and PINs are completely distinct across different events
            self.assertNotEqual(s_job.session_pin, s_hack.session_pin)
            self.assertNotEqual(s_job.qr_token, s_hack.qr_token)
            job_id = e_job.id
            hack_qr = s_hack.qr_token

        # Student logs in
        self.login('11240123', '123')

        # Try to check in to JOB event using HACK event's QR code -> Must be rejected
        cross_res = self.client.post('/checkin/submit', data={
            'event_id': str(job_id),
            'qr_code': hack_qr
        }, follow_redirects=True)
        self.assertEqual(cross_res.status_code, 200)
        self.assertIn('thuộc về sự kiện'.encode('utf-8'), cross_res.data)
        self.assertIn('Mỗi sự kiện có mã QR điểm danh riêng biệt'.encode('utf-8'), cross_res.data)
        self.logout()

    def test_14_student_cannot_manual_checkin_others(self):
        """Test student is forbidden from manually checking in other students"""
        self.login('11244035', '123')
        with app.app_context():
            reg = Registration.query.first()
            reg_id = reg.id

        res = self.client.post(f'/checkin/manual/{reg_id}', follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn('Bạn không có quyền xác nhận điểm danh thủ công'.encode('utf-8'), res.data)
        self.logout()

    def test_15_role_based_navigation_isolation(self):
        """Test sidebar navigation strictly isolates Student, Organizer, and Manager"""
        # 1. Student navigation
        self.login('11244035', '123')
        std_events = self.client.get('/events')
        self.assertIn(b'href="/my-events"', std_events.data)
        self.assertIn(b'href="/checkin"', std_events.data)
        self.assertNotIn(b'href="/organizer/events"', std_events.data)
        self.assertNotIn(b'href="/moderation"', std_events.data)
        self.assertNotIn(b'href="/analytics"', std_events.data)
        self.logout()

        # 2. Organizer navigation
        self.login('vieclam@neu.edu.vn', '123')
        org_events = self.client.get('/events')
        self.assertIn(b'href="/organizer/events"', org_events.data)
        self.assertIn(b'href="/checkin"', org_events.data)
        self.assertIn(b'href="/feedback"', org_events.data)
        self.assertIn(b'href="/analytics"', org_events.data)
        self.assertNotIn(b'href="/my-events"', org_events.data)
        self.assertNotIn(b'href="/moderation"', org_events.data)
        self.logout()

        # 3. Manager navigation
        self.login('quanly@neu.edu.vn', '123')
        mgr_events = self.client.get('/events')
        self.assertIn(b'href="/moderation"', mgr_events.data)
        self.assertIn(b'href="/analytics"', mgr_events.data)
        self.assertNotIn(b'href="/my-events"', mgr_events.data)
        self.assertNotIn(b'href="/organizer/events"', mgr_events.data)
        self.assertNotIn(b'href="/checkin"', mgr_events.data)
        self.assertNotIn(b'href="/feedback"', mgr_events.data)
        self.logout()

    def test_16_organizer_cross_access_isolation(self):
        """Test Organizer 1 cannot edit or view feedback of events belonging to Organizer 2"""
        with app.app_context():
            it_event = Event.query.filter_by(code=f'NEU-HACK-{date.today().year}').first()
            it_event_id = it_event.id

        # Login as Organizer 1 (Career Center)
        self.login('vieclam@neu.edu.vn', '123')

        # Attempt to edit Organizer 2's event -> Blocked
        edit_res = self.client.get(f'/organizer/events?edit_id={it_event_id}', follow_redirects=True)
        self.assertIn('không có quyền truy cập hoặc chỉnh sửa sự kiện của Ban tổ chức khác'.encode('utf-8'), edit_res.data)

        # Attempt to view feedback of Organizer 2's event -> Blocked
        fb_res = self.client.get(f'/feedback?event_id={it_event_id}', follow_redirects=True)
        self.assertIn('không có quyền xem đánh giá của sự kiện do Ban tổ chức khác'.encode('utf-8'), fb_res.data)

        self.logout()

    def test_17_manager_moderation_workflow(self):
        """Test manager can approve a pending event"""
        self.login('quanly@neu.edu.vn', '123')
        with app.app_context():
            ai_event = Event.query.filter_by(code=f'NEU-AI-{date.today().year}').first()
            ai_event_id = ai_event.id
            self.assertEqual(ai_event.status, 'PENDING')

        # Manager approves event
        appr_res = self.client.post(f'/moderation/approve/{ai_event_id}', follow_redirects=True)
        self.assertEqual(appr_res.status_code, 200)
        self.assertIn('Đã phê duyệt sự kiện'.encode('utf-8'), appr_res.data)

        # Verify status is now APPROVED
        with app.app_context():
            ai_event = Event.query.get(ai_event_id)
            self.assertEqual(ai_event.status, 'APPROVED')

        self.logout()

    def test_18_cannot_cancel_attended_or_completed_event(self):
        """Test that attended or completed events cannot be cancelled by student or organizer"""
        # 1. Student attempts to cancel an event they already attended / completed
        self.login('11244035', '123')
        with app.app_context():
            skill_event = Event.query.filter_by(code=f'NEU-SKILL-{date.today().year}').first()
            user = User.query.filter_by(username='11244035').first()
            reg = Registration.query.filter_by(user_id=user.id, event_id=skill_event.id).first()
            reg_id = reg.id
            self.assertEqual(reg.attendance_status, 'ATTENDED')

        cancel_res = self.client.post(f'/registrations/{reg_id}/cancel', follow_redirects=True)
        self.assertEqual(cancel_res.status_code, 200)
        self.assertIn('Bạn đã điểm danh tham gia sự kiện này nên không thể hủy đăng ký!'.encode('utf-8'), cancel_res.data)

        # Verify status is still REGISTERED
        with app.app_context():
            reg_check = Registration.query.get(reg_id)
            self.assertEqual(reg_check.registration_status, 'REGISTERED')

        self.logout()

        # 2. Organizer attempts to cancel a completed event with attendees
        self.login('vieclam@neu.edu.vn', '123')
        with app.app_context():
            skill_event = Event.query.filter_by(code=f'NEU-SKILL-{date.today().year}').first()
            skill_id = skill_event.id
            self.assertEqual(skill_event.status, 'COMPLETED')

        org_cancel_res = self.client.post(f'/organizer/events/{skill_id}/cancel', follow_redirects=True)
        self.assertEqual(org_cancel_res.status_code, 200)
        self.assertIn('Sự kiện đã kết thúc nên không thể hủy!'.encode('utf-8'), org_cancel_res.data)

        # Verify event status is still COMPLETED
        with app.app_context():
            event_check = Event.query.get(skill_id)
            self.assertEqual(event_check.status, 'COMPLETED')

        self.logout()

    def test_22_ticket_api_and_qr_data(self):
        """Test API endpoint returns correct ticket and QR details"""
        with app.app_context():
            reg = Registration.query.filter_by(registration_status='REGISTERED').first()
            ticket_code = reg.ticket_code
            student_id = reg.user.student_id or reg.user.username

        res = self.client.get(f'/api/ticket/{ticket_code}')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['exists'])
        self.assertEqual(data['ticket_code'], ticket_code)
        self.assertEqual(data['student_id'], student_id)

    def test_23_view_ticket_in_my_events(self):
        """Test student can load /my-events and view ticket triggers"""
        self.login('11244035', '123')
        res = self.client.get('/my-events')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn('showTicketModal', html)
        self.assertIn('ticketModal', html)
        self.logout()

if __name__ == '__main__':
    unittest.main()
