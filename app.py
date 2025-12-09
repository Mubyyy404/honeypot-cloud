import smtplib
from email.mime.text import MIMEText
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Log

app = Flask(__name__)
app.config['SECRET_KEY'] = 'enterprise-key-v3'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

# --- EMAIL CONFIG (Use a real Gmail or SMTP for production) ---
# For this demo, we will just PRINT the email to console to avoid errors if you don't have SMTP setup.
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_EMAIL = "your_email@gmail.com" 
SMTP_PASSWORD = "your_app_password"

db.init_app(app)
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

with app.app_context():
    db.create_all()

# --- HELPER: Send Email ---
def send_alert_email(user_email, event, file, device):
    if not user_email: return
    try:
        msg = MIMEText(f"CRITICAL ALERT on {device}\n\nEvent: {event}\nFile: {file}\n\nCheck dashboard immediately.")
        msg['Subject'] = f"Sentinel Alert: {event} detected"
        msg['From'] = "Sentinel Security"
        msg['To'] = user_email
        
        # NOTE: Uncomment below to actually send if you configure SMTP
        # with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        #    server.starttls()
        #    server.login(SMTP_EMAIL, SMTP_PASSWORD)
        #    server.sendmail(SMTP_EMAIL, user_email, msg.as_string())
        
        print(f" [EMAIL SENT] To: {user_email} | Body: {event} on {file}")
    except Exception as e:
        print(f" [EMAIL ERROR] {e}")

# --- ROUTES ---

@app.route('/')
@login_required
def dashboard():
    logs = Log.query.filter_by(user_id=current_user.id).order_by(Log.id.desc()).limit(10).all()
    stats = {
        "total": Log.query.filter_by(user_id=current_user.id).count(),
        "devices": db.session.query(Log.device_name).filter_by(user_id=current_user.id).distinct().count()
    }
    return render_template('dashboard.html', page="dashboard", user=current_user, logs=logs, stats=stats)

@app.route('/devices')
@login_required
def devices():
    # Get unique devices and their last activity
    # SQL alchemy complex query simplified for demo:
    logs = Log.query.filter_by(user_id=current_user.id).order_by(Log.id.desc()).all()
    seen = set()
    unique_devices = []
    for log in logs:
        if log.device_name not in seen:
            unique_devices.append(log)
            seen.add(log.device_name)
    return render_template('dashboard.html', page="devices", user=current_user, devices=unique_devices)

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        email = request.form.get('email')
        enabled = 'enabled' in request.form
        current_user.alert_email = email
        current_user.email_enabled = enabled
        db.session.commit()
        flash('Settings updated successfully')
    return render_template('dashboard.html', page="settings", user=current_user)

@app.route('/download_agent')
@login_required
def download_agent():
    with open('client_template.py', 'r') as f:
        content = f.read()
    content = content.replace('[[API_KEY_PLACEHOLDER]]', current_user.api_key)
    content = content.replace('[[SERVER_URL_PLACEHOLDER]]', request.host_url.rstrip('/'))
    response = make_response(content)
    response.headers['Content-Disposition'] = 'attachment; filename=sentinel_agent.py'
    response.mimetype = 'text/x-python'
    return response

@app.route('/download_installer')
@login_required
def download_installer():
    # Dynamic Batch script for Windows 24/7 Setup
    batch_script = f"""
@echo off
echo [*] Sentinel Auto-Installer (Windows)
echo [*] Installing dependencies...
pip install requests watchdog
echo [*] Creating startup entry...
set "STARTUP_FOLDER=%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\Startup"
copy "sentinel_agent.py" "%STARTUP_FOLDER%\\sentinel_service.pyw"
echo [*] Starting service...
start "" "%STARTUP_FOLDER%\\sentinel_service.pyw"
echo [+] SUCCESS! Monitoring is now active 24/7.
pause
"""
    response = make_response(batch_script)
    response.headers['Content-Disposition'] = 'attachment; filename=install_windows.bat'
    response.mimetype = 'text/plain'
    return response

@app.route('/api/report', methods=['POST'])
def report_incident():
    data = request.json
    user = User.query.filter_by(api_key=data.get('api_key')).first()
    if user:
        new_log = Log(
            timestamp=data.get('time'), event_type=data.get('event'),
            filename=data.get('file'), device_name=data.get('device', 'Unknown'),
            os_info=data.get('os', 'Unknown'), user_id=user.id
        )
        db.session.add(new_log)
        db.session.commit()
        
        # Trigger Email
        if user.email_enabled:
            send_alert_email(user.alert_email, data.get('event'), data.get('file'), data.get('device'))
            
        return jsonify({"status": "logged"}), 200
    return jsonify({"error": "Invalid Key"}), 403

# --- AUTH ROUTES (Keep existing Login/Register/Logout) ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        if User.query.filter_by(username=request.form.get('username')).first():
            flash('Username taken')
        else:
            new_user = User(username=request.form.get('username'), 
                          password=generate_password_hash(request.form.get('password'), method='scrypt'))
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect(url_for('dashboard'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username')).first()
        if user and check_password_hash(user.password, request.form.get('password')):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid login')
    return render_template('login.html')

@app.route('/logout')
def logout(): logout_user(); return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
