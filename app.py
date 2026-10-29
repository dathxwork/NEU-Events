"""
NEU Events - Cổng Quản lý và Tổ chức Sự kiện Đại học Kinh tế Quốc dân
Main Application Entry Point & Flask Server Configuration
"""
import os
from datetime import datetime, date
from flask import Flask, request, session
from flask_login import LoginManager, current_user
from werkzeug.routing import Rule

from models import db, User, Event, Feedback
from routes import (
    auth_bp,
    student_bp,
    organizer_bp,
    manager_bp,
    admin_bp,
    get_period_date_range,
    get_user_notifications,
    get_pending_count,
    format_event_time
)

# Initialize Flask application
app = Flask(__name__)
app.config['SECRET_KEY'] = 'neu-events-super-secret-key-2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///neu_events.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads', 'publications')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize Database
db.init_app(app)

# Initialize Login Manager
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

# Global Context Processors for Templates
@app.context_processor
def inject_global_data():
    today = date.today()
    now = datetime.now()

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

# Register Blueprints for the 4 distinct user roles + Auth
app.register_blueprint(auth_bp)
app.register_blueprint(student_bp)
app.register_blueprint(organizer_bp)
app.register_blueprint(manager_bp)
app.register_blueprint(admin_bp)

# Route Aliasing: Support both url_for('endpoint') and url_for('blueprint.endpoint')
# to ensure 100% backward-compatibility across all templates and test suites.
for rule in list(app.url_map.iter_rules()):
    if '.' in rule.endpoint:
        short_endpoint = rule.endpoint.split('.', 1)[1]
        if short_endpoint not in app.view_functions:
            app.view_functions[short_endpoint] = app.view_functions[rule.endpoint]
        if short_endpoint not in app.url_map._rules_by_endpoint:
            alias_rule = Rule(rule.rule, endpoint=short_endpoint, methods=rule.methods)
            app.url_map.add(alias_rule)

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
