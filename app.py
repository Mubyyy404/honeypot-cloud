from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Log

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-key-change-in-prod'
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

@app.route('/')
@login_required
def dashboard():
    logs = Log.query.filter_by(user_id=current_user.id).order_by(Log.id.desc()).all()
    return render_template('dashboard.html', user=current_user, logs=logs)

@app.route('/download_agent')
@login_required
def download_agent():
    with open('client_template.py', 'r') as f:
        content = f.read()
    
    # Inject User Identity and Live Server URL
    content = content.replace('[[API_KEY_PLACEHOLDER]]', current_user.api_key)
    content = content.replace('[[SERVER_URL_PLACEHOLDER]]', request.host_url.rstrip('/'))
    
    response = make_response(content)
    response.headers['Content-Disposition'] = 'attachment; filename=my_monitor.py'
    response.mimetype = 'text/x-python'
    return response

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if User.query.filter_by(username=username).first():
            flash('Username taken')
        else:
            new_user = User(username=username, password=generate_password_hash(password, method='scrypt'))
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
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/api/report', methods=['POST'])
def report_incident():
    data = request.json
    user = User.query.filter_by(api_key=data.get('api_key')).first()
    if user:
        new_log = Log(timestamp=data.get('time'), event_type=data.get('event'), filename=data.get('file'), user_id=user.id)
        db.session.add(new_log)
        db.session.commit()
        return jsonify({"status": "logged"}), 200
    return jsonify({"error": "Invalid API Key"}), 403

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
