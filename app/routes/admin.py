from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Draw, AuditLog, Winner
from app.utils.security import admin_required, audit_log
from datetime import datetime, timedelta

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin')
@login_required
@admin_required
def admin_panel():
    draws = Draw.query.order_by(Draw.created_at.desc()).all()
    return render_template('admin.html', draws=draws)

@admin_bp.route('/admin/draws', methods=['POST'])
@login_required
@admin_required
@audit_log('Create draw')
def create_draw():
    data = request.get_json()
    
    draw = Draw(
        name=data['name'],
        description=data.get('description', ''),
        prize_amount=float(data['prize_amount']),
        number_of_winners=int(data['number_of_winners']),
        scheduled_for=datetime.fromisoformat(data['scheduled_for']) if data.get('scheduled_for') else None
    )
    
    db.session.add(draw)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Draw created successfully', 'draw_id': draw.id})

@admin_bp.route('/admin/draws/<int:draw_id>', methods=['DELETE'])
@login_required
@admin_required
@audit_log('Delete draw')
def delete_draw(draw_id):
    draw = Draw.query.get_or_404(draw_id)
    
    # Delete related records
    Winner.query.filter_by(draw_id=draw_id).delete()
    Participant.query.filter_by(draw_id=draw_id).delete()
    
    db.session.delete(draw)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Draw deleted successfully'})

@admin_bp.route('/admin/settings')
@login_required
@admin_required
def settings():
    return render_template('settings.html')

@admin_bp.route('/admin/audit-logs')
@login_required
@admin_required
def audit_logs():
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(100).all()
    return render_template('audit_logs.html', logs=logs)

@admin_bp.route('/api/stats')
@login_required
def get_stats():
    total_draws = Draw.query.count()
    completed_draws = Draw.query.filter_by(status='completed').count()
    total_winners = Winner.query.count()
    
    # Calculate total prizes
    completed_draws_obj = Draw.query.filter_by(status='completed').all()
    total_prizes = sum(draw.prize_amount for draw in completed_draws_obj)
    
    return jsonify({
        'total_draws': total_draws,
        'completed_draws': completed_draws,
        'total_winners': total_winners,
        'total_prizes': total_prizes
    })