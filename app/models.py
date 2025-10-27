# app/models.py
from app import db, login_manager
from flask_login import UserMixin
from datetime import datetime
import json

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), default='admin')  # admin, operator
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Draw(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    prize_amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default='MWK')
    number_of_winners = db.Column(db.Integer, default=1)
    status = db.Column(db.String(20), default='draft')  # draft, active, completed, cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    scheduled_for = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    
    # Relationships
    participants = db.relationship('Participant', backref='draw', lazy=True)
    winners = db.relationship('Winner', backref='draw', lazy=True)

class Participant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone_number = db.Column(db.String(20), nullable=False)
    source = db.Column(db.String(20), default='manual')  # manual, api
    draw_id = db.Column(db.Integer, db.ForeignKey('draw.id'), nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_verified = db.Column(db.Boolean, default=True)

class Winner(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    draw_id = db.Column(db.Integer, db.ForeignKey('draw.id'), nullable=False)
    participant_id = db.Column(db.Integer, db.ForeignKey('participant.id'), nullable=False)
    position = db.Column(db.Integer)  # 1st, 2nd, 3rd winner etc.
    won_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    participant = db.relationship('Participant', backref='wins')

class APIConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    endpoint_url = db.Column(db.String(500))
    auth_method = db.Column(db.String(20), default='none')
    api_key = db.Column(db.String(200))
    refresh_interval = db.Column(db.Integer, default=1)  # minutes
    is_active = db.Column(db.Boolean, default=False)
    last_sync = db.Column(db.DateTime)
    default_draw_id = db.Column(db.Integer, db.ForeignKey('draw.id'), nullable=True)

class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', backref='audit_logs')

class APIResponseLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    api_config_id = db.Column(db.Integer, db.ForeignKey('api_config.id'), nullable=False)
    request_url = db.Column(db.String(500), nullable=False)
    request_method = db.Column(db.String(10), nullable=False, default='GET')
    response_status = db.Column(db.Integer)
    response_headers = db.Column(db.Text)
    response_body = db.Column(db.Text)
    error_message = db.Column(db.Text)
    participants_added = db.Column(db.Integer, default=0)
    success = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationship
    api_config = db.relationship('APIConfig', backref=db.backref('response_logs', lazy=True))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))