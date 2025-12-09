import smtplib
from email.mime.text import MIMEText
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Log

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sentinel-enterprise-key-v3'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

# --- EMAIL CONFIGURATION ---
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
# REPLACE THESE WITH YOUR REAL DETAILS:
SMTP_EMAIL = "mohamedmubeen576@gmail.com" 
SMTP_PASSWORD = "qyod ymow fksy rssr" 

db.init_app(app)
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

with app.app_context():
    db.create_all()

# --- EMAIL LOGIC ---
def send_email_alert(user_email, event, filename, device):
    if not user_email: return
    try:
        subject = f"🚨 THREAT DETECTED: {event} on {device}"
        body = f"""
        SENTINEL SECURITY ALERT SYSTEM
        ================================
        WARNING: A file modification was detected.
        
        - Event Type: {event}
        - File Name:  {filename}
        - Device ID:  {device}
        
        Please check your dashboard immediately.
        """
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = SMTP_EMAIL
        msg['To'] = user_email

        print(f"[*] Connecting to Gmail as {SMTP_EMAIL}...")
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.sendmail(SMTP_EMAIL, user_email, msg.as_string())
        
        print(f"[+] Email sent to {user_email}")
        return True
    except Exception as e:
        print(f"[!] Email Failed: {e}")
        return False

# --- ROUTES ---

@app.route('/')
@login_required
def dashboard():
    # Show last 15 logs
    logs = Log.query.filter_by(user_id=current_user.id).order_by(Log.id.desc()).limit(15).all()
    stats = {
        "total": Log.query.filter_by(user_id=current_user.id).count(),
        "devices": db.session.query(Log.device_name).filter_by(user_id=current_user.id).distinct().count()
    }
    return render_template('dashboard.html', user=current_user, logs=logs, stats=stats, page="dashboard")

@app.route('/devices')
@login_required
def devices():
    # Logic to show unique devices
    logs = Log.query.filter_by(user_id=current_user.id).order_by(Log.id.desc()).all()
    seen = set()
    unique_devices = []
    for log in logs:
        if log.device_name not in seen:
            unique_devices.append(log)
            seen.add(log.device_name)
    return render_template('dashboard.html', user=current_user, devices=unique_devices, page="devices")

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        current_user.alert_email = request.form.get('email')
        current_user.email_enabled = 'enabled' in request.form
        db.session.commit()
        flash('Settings saved successfully.')
    return render_template('dashboard.html', user=current_user, page="settings")

@app.route('/download_agent')
@login_required
def download_agent():
    with open('client_template.py', 'r') as f:
        content = f.read()
    content = content.replace('[[API_KEY_PLACEHOLDER]]', current_user.api_key)
    content = content.replace('[[SERVER_URL_PLACEHOLDER]]', request.host_url.rstrip('/'))
    response = make_response(content)
    response.headers['Content-Disposition'] = 'attachment; filename=sentinel_guard.py'
    response.mimetype = 'text/x-python'
    return response

# --- THIS IS THE ROUTE THAT WAS MISSING ---
@app.route('/download_installer')
@login_required
def download_installer():
    batch_script = """
@echo off
echo [*] SENTINEL AUTO-INSTALLER
echo --------------------------------
echo [*] Step 1: Installing Python Libraries...
pip install requests watchdog

echo [*] Step 2: Configuring Startup...
set "STARTUP=%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\Startup"
set "SOURCE=%~dp0sentinel_guard.py"
set "DEST=%STARTUP%\\sentinel_service.pyw"

if not exist "%SOURCE%" (
    echo [!] ERROR: sentinel_guard.py not found!
    echo Please keep this .bat file in the SAME folder as the .py agent.
    pause
    exit
)

copy "%SOURCE%" "%DEST%" /Y

echo [*] Step 3: Starting Service...
start "" "%DEST%"

echo --------------------------------
echo [+] SUCCESS! Monitoring is active 24/7.
echo You can close this window.
pause
"""
    response = make_response(batch_script)
    response.headers['Content-Disposition'] = 'attachment; filename=install_windows.bat'
    response.mimetype = 'text/plain'
    return response
# ------------------------------------------

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
        
        if user.email_enabled and user.alert_email:
            send_email_alert(user.alert_email, data.get('event'), data.get('file'), data.get('device'))
            
        return jsonify({"status": "logged"}), 200
    return jsonify({"error": "Invalid Key"}), 403

# --- AUTH ROUTES ---
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
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
