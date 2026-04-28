from flask import Blueprint, request, jsonify, session
from auth.auth_handler import (
    create_user, 
    authenticate_user, 
    get_user,
    generate_token
)

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@auth_bp.route('/signup', methods=['POST'])
def signup():
    """User signup endpoint"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'No JSON data provided'}), 400
        
        firstName = data.get('firstName', '').strip()
        lastName = data.get('lastName', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        
        # Validation
        if not all([firstName, lastName, email, password]):
            return jsonify({
                'success': False, 
                'message': 'First Name, Last Name, Email, and Password are required'
            }), 400
        
        if len(firstName) < 2:
            return jsonify({
                'success': False,
                'message': 'First Name must be at least 2 characters'
            }), 400
        
        if len(lastName) < 2:
            return jsonify({
                'success': False,
                'message': 'Last Name must be at least 2 characters'
            }), 400
        
        if len(password) < 6:
            return jsonify({
                'success': False,
                'message': 'Password must be at least 6 characters'
            }), 400
        
        if '@' not in email:
            return jsonify({
                'success': False,
                'message': 'Invalid email format'
            }), 400
        
        # Create user with firstName and lastName
        result = create_user(email, password, firstName, lastName)
        
        if result['success']:
            session['user_id'] = result['user_id']
            return jsonify(result), 201
        else:
            return jsonify(result), 409
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    """User login endpoint"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'No JSON data provided'}), 400
        
        email = data.get('email', '').strip()
        password = data.get('password', '')
        
        if not email or not password:
            return jsonify({
                'success': False,
                'message': 'Email and password are required'
            }), 400
        
        # Authenticate
        result = authenticate_user(email, password)
        
        if result['success']:
            session['user_id'] = result['user_id']
            return jsonify(result), 200
        else:
            return jsonify(result), 401
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500


@auth_bp.route('/logout', methods=['POST'])
def logout():
    """User logout endpoint"""
    try:
        session.clear()
        return jsonify({
            'success': True,
            'message': 'Logged out successfully'
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500


@auth_bp.route('/profile', methods=['GET'])
def get_profile():
    """Get current user profile"""
    try:
        user_id = session.get('user_id')
        
        # For testing - allow demo user
        if not user_id:
            user_id = 'demo_user_testing'
            session['user_id'] = user_id
        
        # Return demo user profile for development
        if user_id == 'demo_user_testing':
            return jsonify({
                'success': True,
                'user': {
                    'user_id': 'demo_user_testing',
                    'email': 'demo@test.com',
                    'firstName': 'Demo',
                    'lastName': 'User'
                }
            }), 200
        
        user = get_user(user_id)
        
        if user:
            return jsonify({
                'success': True,
                'user': user
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'User not found'
            }), 404
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Server error: {str(e)}'
        }), 500
