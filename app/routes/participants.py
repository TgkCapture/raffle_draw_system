# app/routes/participants.py
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
from app import db
from app.models import Participant, Draw, APIConfig
from app.utils.file_processing import process_csv_file, process_excel_file, get_allowed_extensions
from app.utils.security import audit_log, admin_required
from app.utils.api_service import api_service
import requests
from flask import current_app

participants_bp = Blueprint('participants', __name__)

@participants_bp.route('/participants')
@login_required
def manage_participants():
    draws = Draw.query.all()
    api_config = APIConfig.query.first()
    return render_template('participants.html', draws=draws, api_config=api_config)

@participants_bp.route('/api/participants/upload', methods=['POST'])
@login_required
@audit_log('Upload participants')
def upload_participants():
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No file selected'})
    
    file = request.files['file']
    draw_id = request.form.get('draw_id')
    
    if not draw_id:
        return jsonify({'success': False, 'message': 'No draw selected'})
    
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected'})
    
    # Check file extension
    if '.' not in file.filename or file.filename.rsplit('.', 1)[1].lower() not in get_allowed_extensions():
        return jsonify({'success': False, 'message': 'Invalid file type. Allowed: CSV, Excel'})
    
    # Save file
    filename = secure_filename(file.filename)
    file_path = os.path.join('uploads', 'participants', filename)
    file.save(file_path)
    
    # Process file based on extension
    file_ext = filename.rsplit('.', 1)[1].lower()
    
    if file_ext == 'csv':
        success, message = process_csv_file(file_path, int(draw_id))
    else:  # Excel files
        success, message = process_excel_file(file_path, int(draw_id))
    
    # Clean up uploaded file
    try:
        os.remove(file_path)
    except:
        pass
    
    return jsonify({'success': success, 'message': message})

@participants_bp.route('/api/participants/<int:draw_id>')
@login_required
def get_participants(draw_id):
    participants = Participant.query.filter_by(draw_id=draw_id).all()
    return jsonify([{
        'id': p.id,
        'phone_number': p.phone_number,
        'source': p.source,
        'added_at': p.added_at.isoformat() if p.added_at else None,
        'is_verified': p.is_verified
    } for p in participants])

@participants_bp.route('/api/participants/count/<int:draw_id>')
def get_participant_count(draw_id):
    count = Participant.query.filter_by(draw_id=draw_id, is_verified=True).count()
    return jsonify({'count': count})

@participants_bp.route('/api/api-config', methods=['POST'])
@login_required
@admin_required
@audit_log('Update API configuration')
def update_api_config():
    data = request.get_json()
    
    api_config = APIConfig.query.first()
    if not api_config:
        api_config = APIConfig()
        db.session.add(api_config)
    
    api_config.endpoint_url = data.get('endpoint_url')
    api_config.auth_method = data.get('auth_method', 'none')
    api_config.api_key = data.get('api_key')
    api_config.refresh_interval = data.get('refresh_interval', 5)
    api_config.is_active = data.get('is_active', False)
    api_config.default_draw_id = data.get('default_draw_id')  
    
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'API configuration updated'})

@participants_bp.route('/api/api-config/status', methods=['GET'])
@login_required
def get_api_status():
    """Get current API service status"""
    return jsonify({
        'is_running': api_service.is_running,
        'is_active': api_service.is_running
    })

@participants_bp.route('/api/api-config/start', methods=['POST'])
@login_required
@admin_required
@audit_log('Start API service')
def start_api_service():
    """Start the API polling service"""
    try:
        success = api_service.start_polling()
        if success:
            return jsonify({'success': True, 'message': 'API service started'})
        else:
            return jsonify({'success': False, 'message': 'API service is already running'})
    except Exception as e:
        current_app.logger.error(f"Error starting API service: {e}")
        return jsonify({'success': False, 'message': f'Error starting API service: {str(e)}'})

@participants_bp.route('/api/api-config/stop', methods=['POST'])
@login_required
@admin_required
@audit_log('Stop API service')
def stop_api_service():
    """Stop the API polling service"""
    try:
        api_service.stop_polling()
        return jsonify({'success': True, 'message': 'API service stopped'})
    except Exception as e:
        current_app.logger.error(f"Error stopping API service: {e}")
        return jsonify({'success': False, 'message': f'Error stopping API service: {str(e)}'})

@participants_bp.route('/api/api-config/test', methods=['POST'])
@login_required
@admin_required
@audit_log('Test API connection')
def test_api_connection():
    """Test the API connection"""
    try:
        api_config = APIConfig.query.first()
        if not api_config or not api_config.endpoint_url:
            return jsonify({'success': False, 'message': 'No API endpoint configured'})
        
        headers = {}
        if api_config.auth_method == 'api_key' and api_config.api_key:
            headers['Authorization'] = f'Bearer {api_config.api_key}'
        elif api_config.auth_method == 'basic_auth' and api_config.api_key:
            headers['Authorization'] = f'Basic {api_config.api_key}'
        
        response = requests.get(api_config.endpoint_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            return jsonify({
                'success': True, 
                'message': f'API connection successful. Status: {response.status_code}'
            })
        else:
            return jsonify({
                'success': False, 
                'message': f'API returned status code: {response.status_code}'
            })
            
    except requests.exceptions.RequestException as e:
        return jsonify({'success': False, 'message': f'API connection failed: {str(e)}'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error testing API: {str(e)}'})