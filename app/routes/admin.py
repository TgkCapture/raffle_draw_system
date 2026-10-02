# app/routes/admin.py
from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from app import db
from app.models import Draw, AuditLog, Winner, Participant
from app.utils.security import admin_required, audit_log
from datetime import datetime, time, timedelta

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin')
@login_required
@admin_required
def admin_panel():
    try:
        draws = Draw.query.order_by(Draw.created_at.desc()).all()
        # Convert to list to avoid detached instance issues in templates
        draws_data = []
        for draw in draws:
            draws_data.append({
                'id': draw.id,
                'name': draw.name,
                'prize_amount': draw.prize_amount,
                'number_of_winners': draw.number_of_winners,
                'status': draw.status,
                'participants': Participant.query.filter_by(draw_id=draw.id).all()
            })
        return render_template('admin.html', draws=draws_data)
    except Exception as e:
        current_app.logger.error(f"Error in admin panel: {e}")
        return render_template('admin.html', draws=[])

@admin_bp.route('/admin/draws', methods=['POST'])
@login_required
@admin_required
@audit_log('Create draw')
def create_draw_route():
    try:
        data = request.get_json()
        
        draw = Draw(
            name=data['name'],
            description=data.get('description', ''),
            prize_amount=float(data['prize_amount']),
            number_of_winners=int(data['number_of_winners']),
            scheduled_for=datetime.fromisoformat(data['scheduled_for'].replace('Z', '+00:00')) if data.get('scheduled_for') else None
        )
        
        db.session.add(draw)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Draw created successfully', 'draw_id': draw.id})
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating draw: {e}")
        return jsonify({'success': False, 'message': f'Error creating draw: {str(e)}'})

@admin_bp.route('/admin/draws/<int:draw_id>', methods=['DELETE'])
@login_required
@admin_required
@audit_log('Delete draw')
def delete_draw(draw_id):
    try:
        draw = Draw.query.get_or_404(draw_id)
        
        # Delete related records
        Winner.query.filter_by(draw_id=draw_id).delete()
        Participant.query.filter_by(draw_id=draw_id).delete()
        
        db.session.delete(draw)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Draw deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting draw: {e}")
        return jsonify({'success': False, 'message': f'Error deleting draw: {str(e)}'})

@admin_bp.route('/admin/settings')
@login_required
@admin_required
def settings():
    return render_template('settings.html')

@admin_bp.route('/admin/audit-logs')
@login_required
@admin_required
def audit_logs():
    try:
        logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(100).all()
        # Convert to list to avoid detached instance issues
        logs_data = []
        for log in logs:
            logs_data.append({
                'timestamp': log.timestamp,
                'user': log.user.username if log.user else 'System',
                'action': log.action,
                'details': log.details,
                'ip_address': log.ip_address
            })
        return render_template('audit_logs.html', logs=logs_data)
    except Exception as e:
        current_app.logger.error(f"Error getting audit logs: {e}")
        return render_template('audit_logs.html', logs=[])

@admin_bp.route('/api/stats')
@login_required
def get_stats():
    try:
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
    except Exception as e:
        current_app.logger.error(f"Error getting stats: {e}")
        return jsonify({
            'total_draws': 0,
            'completed_draws': 0,
            'total_winners': 0,
            'total_prizes': 0
        })

@admin_bp.route('/api/health/database')
def database_health():
    """Check database connectivity and performance"""
    try:
        from app import db
        from sqlalchemy import text
        
        # Test connection
        start_time = time.time()
        result = db.session.execute(text('SELECT 1')).scalar()
        query_time = time.time() - start_time
        
        # Get basic stats
        table_counts = {}
        tables = ['draw', 'participant', 'winner', 'user', 'api_config', 'audit_log', 'api_response_log']
        
        for table in tables:
            try:
                count = db.session.execute(text(f'SELECT COUNT(*) FROM {table}')).scalar()
                table_counts[table] = count
            except Exception as e:
                table_counts[table] = f"Error: {str(e)}"
        
        return jsonify({
            'status': 'healthy',
            'database_connected': True,
            'query_response_time': round(query_time, 4),
            'table_counts': table_counts,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"Database health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'database_connected': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500    