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

    __table_args__ = (
        # Index for role-based queries
        db.Index('ix_user_role_created', 'role', 'created_at'),
    )

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

    __table_args__ = (
        # Composite indexes for common draw queries
        db.Index('ix_draw_status_created', 'status', 'created_at'),
        db.Index('ix_draw_status_scheduled', 'status', 'scheduled_for'),
        db.Index('ix_draw_completed_status', 'completed_at', 'status'),
    )

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
        # Composite indexes for common participant queries
        db.Index('ix_participant_draw_verified', 'draw_id', 'is_verified'),
        db.Index('ix_participant_phone_draw', 'phone_number', 'draw_id'),
        db.Index('ix_participant_source', 'source'),
        db.Index('ix_participant_added_source', 'added_at', 'source'),
        db.Index('ix_participant_draw_added', 'draw_id', 'added_at'),
        db.Index('ix_participant_verified_draw', 'is_verified', 'draw_id', 'added_at'),
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
        # Composite indexes for common winner queries
        db.Index('ix_winner_draw_position', 'draw_id', 'position'),
        db.Index('ix_winner_draw_participant', 'draw_id', 'participant_id'),
        db.Index('ix_winner_draw_won_at', 'draw_id', 'won_at'),
        db.Index('ix_winner_position_won_at', 'position', 'won_at'),
        db.Index('ix_winner_participant_draw', 'participant_id', 'draw_id'),
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

    __table_args__ = (
        # Index for active configurations
        db.Index('ix_api_config_active_sync', 'is_active', 'last_sync'),
        db.Index('ix_api_config_auth_active', 'auth_method', 'is_active'),
    )

class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    action = db.Column(db.String(100), nullable=False, index=True)
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # Relationship
    user = db.relationship('User', backref='audit_logs')

    __table_args__ = (
        # Composite indexes for audit log queries
        db.Index('ix_audit_log_timestamp', 'timestamp'),
        db.Index('ix_audit_log_user_action', 'user_id', 'action'),
        db.Index('ix_audit_log_action_timestamp', 'action', 'timestamp'),
        db.Index('ix_audit_log_user_timestamp', 'user_id', 'timestamp'),
        db.Index('ix_audit_log_ip_timestamp', 'ip_address', 'timestamp'),
    )

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

    __table_args__ = (
        # Composite indexes for API log analysis
        db.Index('ix_api_log_timestamp', 'timestamp'),
        db.Index('ix_api_log_success', 'success'),
        db.Index('ix_api_log_config', 'api_config_id', 'timestamp'),
        db.Index('ix_api_log_status_timestamp', 'response_status', 'timestamp'),
        db.Index('ix_api_log_success_timestamp', 'success', 'timestamp'),
        db.Index('ix_api_log_config_success', 'api_config_id', 'success', 'timestamp'),
        db.Index('ix_api_log_participants_added', 'participants_added', 'timestamp'),
    )

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))