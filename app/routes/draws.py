# app/routes/draws.py
from flask import Blueprint, request, jsonify, render_template
from flask_login import login_required, current_user
from app.models import Draw, Winner, Participant, AuditLog, db
from app.utils.draw_engine import draw_engine
from app.utils.security import audit_log
from datetime import datetime

draws_bp = Blueprint('draws', __name__)

@draws_bp.route('/')
@login_required
def management():
    try:
        draws = Draw.query.order_by(Draw.created_at.desc()).all()
        # Convert to list of dictionaries to avoid detached instance issues
        draws_data = []
        for draw in draws:
            draws_data.append({
                'id': draw.id,
                'name': draw.name,
                'prize_amount': draw.prize_amount,
                'number_of_winners': draw.number_of_winners,
                'status': draw.status,
                'participant_count': Participant.query.filter_by(draw_id=draw.id, is_verified=True).count()
            })
        return render_template('management.html', draws=draws_data)
    except Exception as e:
        current_app.logger.error(f"Error in management route: {e}")
        return render_template('management.html', draws=[])

@draws_bp.route('/api/draws', methods=['GET'])
@login_required
def get_draws():
    try:
        draws = Draw.query.all()
        return jsonify([{
            'id': draw.id,
            'name': draw.name,
            'prize_amount': draw.prize_amount,
            'currency': draw.currency,
            'number_of_winners': draw.number_of_winners,
            'status': draw.status,
            'participant_count': Participant.query.filter_by(draw_id=draw.id, is_verified=True).count(),
            'created_at': draw.created_at.isoformat() if draw.created_at else None
        } for draw in draws])
    except Exception as e:
        current_app.logger.error(f"Error getting draws: {e}")
        return jsonify([])

@draws_bp.route('/api/draws/<int:draw_id>')
@login_required
def get_draw(draw_id):
    try:
        draw = Draw.query.get_or_404(draw_id)
        return jsonify({
            'id': draw.id,
            'name': draw.name,
            'prize_amount': draw.prize_amount,
            'currency': draw.currency,
            'number_of_winners': draw.number_of_winners,
            'status': draw.status
        })
    except Exception as e:
        current_app.logger.error(f"Error getting draw {draw_id}: {e}")
        return jsonify({'error': 'Draw not found'}), 404

@draws_bp.route('/api/draws/<int:draw_id>/start', methods=['POST'])
@login_required
@audit_log('Start draw')
def start_draw(draw_id):
    try:
        success, message = draw_engine.start_draw(draw_id)
        return jsonify({'success': success, 'message': message})
    except Exception as e:
        current_app.logger.error(f"Error starting draw: {e}")
        return jsonify({'success': False, 'message': f'Error starting draw: {str(e)}'})

@draws_bp.route('/api/draws/stop', methods=['POST'])
@login_required
@audit_log('Stop draw')
def stop_draw():
    try:
        success, message = draw_engine.stop_draw()
        return jsonify({'success': success, 'message': message})
    except Exception as e:
        current_app.logger.error(f"Error stopping draw: {e}")
        return jsonify({'success': False, 'message': f'Error stopping draw: {str(e)}'})

@draws_bp.route('/api/draws/draw-winner', methods=['POST'])
@login_required
@audit_log('Draw winner')
def draw_winner_route():
    try:
        if not draw_engine.is_running:
            return jsonify({'success': False, 'message': 'No active draw'})
        
        winner = draw_engine.draw_next_winner()
        if winner:
            return jsonify({'success': True, 'winner': winner})
        else:
            return jsonify({'success': False, 'message': 'No more winners to draw'})
    except Exception as e:
        current_app.logger.error(f"Error drawing winner: {e}")
        return jsonify({'success': False, 'message': f'Error drawing winner: {str(e)}'})

@draws_bp.route('/api/draws/status')
def draw_status():
    try:
        current_draw_id = draw_engine.current_draw['id'] if draw_engine.current_draw else None
        return jsonify({
            'is_running': draw_engine.is_running,
            'current_draw': current_draw_id,
            'winners_drawn': draw_engine.winners_drawn,
            'total_winners': draw_engine.total_winners
        })
    except Exception as e:
        current_app.logger.error(f"Error getting draw status: {e}")
        return jsonify({
            'is_running': False,
            'current_draw': None,
            'winners_drawn': 0,
            'total_winners': 0
        })

@draws_bp.route('/api/draws/animation')
def get_animation():
    try:
        if not draw_engine.is_running:
            return jsonify({'success': False, 'sequence': []})
        
        sequence = draw_engine.get_animation_sequence()
        return jsonify({'success': True, 'sequence': sequence})
    except Exception as e:
        current_app.logger.error(f"Error getting animation: {e}")
        return jsonify({'success': False, 'sequence': []})

@draws_bp.route('/api/winners')
@login_required
def get_winners():
    try:
        winners = Winner.query.join(Participant).join(Draw).order_by(Winner.won_at.desc()).limit(10).all()
        return jsonify([{
            'phone_number': winner.participant.phone_number,
            'prize_amount': winner.draw.prize_amount,
            'draw_name': winner.draw.name,
            'position': winner.position,
            'won_at': winner.won_at.isoformat() if winner.won_at else None
        } for winner in winners])
    except Exception as e:
        current_app.logger.error(f"Error getting winners: {e}")
        return jsonify([])

@draws_bp.route('/tv')
def tv_display():
    try:
        current_draw_data = None
        if draw_engine.current_draw:
            # Get fresh draw data from database
            current_draw = Draw.query.get(draw_engine.current_draw['id'])
            if current_draw:
                current_draw_data = {
                    'id': current_draw.id,
                    'name': current_draw.name,
                    'prize_amount': current_draw.prize_amount,
                    'number_of_winners': current_draw.number_of_winners,
                    'status': current_draw.status
                }
        return render_template('tv_display.html', current_draw=current_draw_data)
    except Exception as e:
        current_app.logger.error(f"Error in TV display route: {e}")
        return render_template('tv_display.html', current_draw=None)