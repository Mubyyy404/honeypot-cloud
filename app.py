import smtplib
from email.mime.text import MIMEText
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Log

app = Flask(__name__)
app.config['SECRET_KEY'] = 'final-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

# --- EMAIL CONFIGURATION (REQUIRED FOR ALERTS) ---
# 1. Use a Gmail account.
# 2. Go to Google Account > Security > 2-Step Verification > App Passwords.
# 3. Generate a password and paste it below.
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_EMAIL = "YOUR_GMAIL@gmail.com"      # <--- REPLACE THIS
SMTP_PASSWORD = "YOUR_APP_PASSWORD"      # <--- REPLACE THIS (16 chars)

db.init_app(app)
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

with app.app_context():
    db.create_all()

def send_email_alert(user_email, event, filename, device):
    if not user_email: return
    try:
        subject = f"🚨 SECURITY ALERT: {event} on {device}"
        body = f"""
        SENTINEL SECURITY ALERT
        -----------------------------------
        Event:   {event}
        File:    {filename}
        Device:  {device}
        -----------------------------------
        This is an automated warning. Check your dashboard immediately.
        """
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = SMTP_EMAIL
        msg['To'] = user_email

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.sendmail(SMTP_EMAIL, user_email, msg.as_string())
        print(f"[*] Email sent successfully to {user_email}")
    except Exception as e:
        print(f"[!] Email Failed: {e}")

# --- ROUTES ---
@app.route('/')
@login_required
def dashboard():
    logs = Log.query.filter_by(user_id=current_user.id).order_by(Log.id.desc()).all()
    return render_template('dashboard.html', user=current_user, logs=logs, page="dashboard")

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        current_user.alert_email = request.form.get('email')
        current_user.email_enabled = 'enabled' in request.form
        db.session.commit()
        flash('Email settings saved!')
    return render_template('dashboard.html', user=current_user, page="settings")

@app.route('/download_agent')
@login_required
def download_agent():
    with open('client_template.py', 'r') as f:
        content = f.read()
    content = content.replace('[[API_KEY_PLACEHOLDER]]', current_user.api_key)
    content = content.replace('[[SERVER_URL_PLACEHOLDER]]', request.host_url.rstrip('/'))
    response = make_response(content)
    # .pyw extension hides the black terminal window on Windows (Silent Mode)
    # If you want them to SEE the window, change to .py
    response.headers['Content-Disposition'] = 'attachment; filename=sentinel_guard.py' 
    response.mimetype = 'text/x-python'
    return response

@app.route('/api/report', methods=['POST'])
def report_incident():
    data = request.json
    user = User.query.filter_by(api_key=data.get('api_key')).first()
    if user:
        # Save Log
        new_log = Log(
            timestamp=data.get('time'), event_type=data.get('event'),
            filename=data.get('file'), device_name=data.get('device', 'Unknown'),
            os_info=data.get('os', 'Unknown'), user_id=user.id
        )
        db.session.add(new_log)
        db.session.commit()
        
        # Send Email
        if user.email_enabled and user.alert_email:
            send_email_alert(user.alert_email, data.get('event'), data.get('file'), data.get('device', 'Unknown'))
            
        return jsonify({"status": "logged"}), 200
    return jsonify({"error": "Invalid Key"}), 403

# (Keep Login/Register/Logout routes from previous code)
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
