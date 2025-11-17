# app/models.py
from app import db, login_manager
from flask_login import UserMixin
from datetime import datetime
import json

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), default='admin', index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

class Draw(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    prize_amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default='MWK')
    number_of_winners = db.Column(db.Integer, default=1)
    status = db.Column(db.String(20), default='draft', index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    scheduled_for = db.Column(db.DateTime, index=True)
    completed_at = db.Column(db.DateTime, index=True)
    
    # Relationships
    participants = db.relationship('Participant', backref='draw', lazy=True, cascade='all, delete-orphan')
    winners = db.relationship('Winner', backref='draw', lazy=True, cascade='all, delete-orphan')

class Participant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone_number = db.Column(db.String(20), nullable=False, index=True)
    source = db.Column(db.String(20), default='manual', index=True)
    draw_id = db.Column(db.Integer, db.ForeignKey('draw.id'), nullable=False, index=True)
    added_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    is_verified = db.Column(db.Boolean, default=True, index=True)
    
    # same phone can't participate twice in same draw
    __table_args__ = (
        db.UniqueConstraint('draw_id', 'phone_number', name='unique_participant_per_draw'),
    )

class Winner(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    draw_id = db.Column(db.Integer, db.ForeignKey('draw.id'), nullable=False, index=True)
    participant_id = db.Column(db.Integer, db.ForeignKey('participant.id'), nullable=False, index=True)
    position = db.Column(db.Integer, index=True)  # 1st, 2nd, 3rd winner etc.
    won_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # Relationship
    participant = db.relationship('Participant', backref='wins')
    
    # same position can't be awarded twice in same draw
    __table_args__ = (
        db.UniqueConstraint('draw_id', 'position', name='unique_position_per_draw'),
    )

class APIConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    endpoint_url = db.Column(db.String(500))
    auth_method = db.Column(db.String(20), default='none', index=True)
    api_key = db.Column(db.String(200))
    refresh_interval = db.Column(db.Integer, default=1)  # minutes
    is_active = db.Column(db.Boolean, default=False, index=True)
    last_sync = db.Column(db.DateTime, index=True)
    default_draw_id = db.Column(db.Integer, db.ForeignKey('draw.id'), nullable=True)

class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    action = db.Column(db.String(100), nullable=False, index=True)
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # Relationship
    user = db.relationship('User', backref='audit_logs')

class APIResponseLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    api_config_id = db.Column(db.Integer, db.ForeignKey('api_config.id'), nullable=False, index=True)
    request_url = db.Column(db.String(500), nullable=False)
    request_method = db.Column(db.String(10), nullable=False, default='GET')
    response_status = db.Column(db.Integer, index=True)
    response_headers = db.Column(db.Text)
    response_body = db.Column(db.Text)
    error_message = db.Column(db.Text)
    participants_added = db.Column(db.Integer, default=0)
    success = db.Column(db.Boolean, default=False, index=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Relationship
    api_config = db.relationship('APIConfig', backref=db.backref('response_logs', lazy=True))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))