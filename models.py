# models.py
import uuid
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    api_key = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    logs = db.relationship('Log', backref='owner', lazy=True)

class Log(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.String(50))
    event_type = db.Column(db.String(50))
    filename = db.Column(db.String(200))
    
    # New Fields for V2.0
    device_name = db.Column(db.String(100), default="Unknown")
    os_info = db.Column(db.String(100), default="Unknown")
    
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
