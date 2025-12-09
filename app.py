# app.py
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Log

app = Flask(__name__)
app.config['SECRET_KEY'] = 'super-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

db.init_app(app)
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

with app.app_context():
    db.create_all()

# --- ROUTES ---
@app.route('/')
@login_required
def dashboard():
    # Get logs
    logs = Log.query.filter_by(user_id=current_user.id).order_by(Log.id.desc()).all()
    
    # Calculate stats for the graph
    total_attacks = len(logs)
    unique_devices = len(set([l.device_name for l in logs]))
    
    return render_template('dashboard.html', 
                         user=current_user, 
                         logs=logs, 
                         stats={"total": total_attacks, "devices": unique_devices})

@app.route('/download_agent')
@login_required
def download_agent():
    # Logic is the same for all OS, but the UI handles the "choice"
    with open('client_template.py', 'r') as f:
        content = f.read()
    
    content = content.replace('[[API_KEY_PLACEHOLDER]]', current_user.api_key)
    content = content.replace('[[SERVER_URL_PLACEHOLDER]]', request.host_url.rstrip('/'))
    
    response = make_response(content)
    response.headers['Content-Disposition'] = 'attachment; filename=sentinel_agent.py'
    response.mimetype = 'text/x-python'
    return response

@app.route('/clear_logs', methods=['POST'])
@login_required
def clear_logs():
    Log.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    return redirect(url_for('dashboard'))

# --- AUTH ---
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

# --- API ---
@app.route('/api/report', methods=['POST'])
def report_incident():
    data = request.json
    user = User.query.filter_by(api_key=data.get('api_key')).first()
    if user:
        new_log = Log(
            timestamp=data.get('time'),
            event_type=data.get('event'),
            filename=data.get('file'),
            device_name=data.get('device', 'Unknown'),
            os_info=data.get('os', 'Unknown'),
            user_id=user.id
        )
        db.session.add(new_log)
        db.session.commit()
        return jsonify({"status": "logged"}), 200
    return jsonify({"error": "Invalid Key"}), 403

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
