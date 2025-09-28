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
    draws = Draw.query.order_by(Draw.created_at.desc()).all()
    return render_template('management.html', draws=draws)

@draws_bp.route('/api/draws', methods=['GET'])
@login_required
def get_draws():
    draws = Draw.query.all()
    return jsonify([{
        'id': draw.id,
        'name': draw.name,
        'prize_amount': draw.prize_amount,
        'currency': draw.currency,
        'number_of_winners': draw.number_of_winners,
        'status': draw.status,
        'participant_count': len(draw.participants),
        'created_at': draw.created_at.isoformat()
    } for draw in draws])

@draws_bp.route('/api/draws', methods=['POST'])
@login_required
@audit_log
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
    
    return jsonify({'message': 'Draw created successfully', 'draw_id': draw.id})

@draws_bp.route('/api/draws/<int:draw_id>/start', methods=['POST'])
@login_required
@audit_log
def start_draw(draw_id):
    success, message = draw_engine.start_draw(draw_id)
    return jsonify({'success': success, 'message': message})

@draws_bp.route('/api/draws/stop', methods=['POST'])
@login_required
@audit_log
def stop_draw():
    success, message = draw_engine.stop_draw()
    return jsonify({'success': success, 'message': message})

@draws_bp.route('/api/draws/draw-winner', methods=['POST'])
@login_required
@audit_log
def draw_winner():
    if not draw_engine.is_running:
        return jsonify({'success': False, 'message': 'No active draw'})
    
    winner = draw_engine.draw_next_winner()
    if winner:
        return jsonify({'success': True, 'winner': winner})
    else:
        return jsonify({'success': False, 'message': 'No more winners to draw'})

@draws_bp.route('/api/draws/status')
def draw_status():
    return jsonify({
        'is_running': draw_engine.is_running,
        'current_draw': draw_engine.current_draw.id if draw_engine.current_draw else None,
        'winners_drawn': draw_engine.winners_drawn,
        'total_winners': draw_engine.total_winners
    })

@draws_bp.route('/api/draws/animation')
def get_animation():
    if not draw_engine.is_running:
        return jsonify({'success': False, 'sequence': []})
    
    sequence = draw_engine.get_animation_sequence()
    return jsonify({'success': True, 'sequence': sequence})

@draws_bp.route('/tv')
def tv_display():
    current_draw = draw_engine.current_draw
    return render_template('tv_display.html', current_draw=current_draw)