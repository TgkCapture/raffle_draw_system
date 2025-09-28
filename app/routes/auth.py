from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User, db
from app.utils.security import hash_password, verify_password, audit_log

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and verify_password(user.password_hash, password):
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('draws.management'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('auth.login'))

@auth_bp.route('/api/create-admin', methods=['POST'])
def create_admin():
    """Endpoint to create initial admin user (for setup)"""
    username = request.json.get('username')
    password = request.json.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    
    # Check if admin already exists
    if User.query.filter_by(role='admin').first():
        return jsonify({'error': 'Admin user already exists'}), 400
    
    user = User(
        username=username,
        password_hash=hash_password(password),
        role='admin'
    )
    
    db.session.add(user)
    db.session.commit()
    
    return jsonify({'message': 'Admin user created successfully'})