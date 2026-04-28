import json
import hashlib
import os
from datetime import datetime, timedelta
import secrets

USER_DATABASE_FILE = "credentials_of_users.json"

def get_user_db_path():
    """Get the path to users database"""
    return os.path.join(os.path.dirname(__file__), '..', USER_DATABASE_FILE)

def load_users():
    """Load all users from JSON file"""
    db_path = get_user_db_path()
    try:
        if os.path.exists(db_path):
            with open(db_path, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading users: {e}")
    return {}

def save_users(users):
    """Save users to JSON file"""
    db_path = get_user_db_path()
    try:
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        with open(db_path, 'w') as f:
            json.dump(users, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving users: {e}")
        return False

def hash_password(password):
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def generate_token():
    """Generate a secure token for session"""
    return secrets.token_urlsafe(32)

def verify_password(password, hashed):
    """Verify password against hash"""
    return hash_password(password) == hashed

def create_user(email, password, firstName, lastName):
    """Create a new user account"""
    users = load_users()
    
    # Check if user exists
    if email in users:
        return {
            'success': False,
            'message': 'Email already registered'
        }
    
    # Create new user
    users[email] = {
        'firstName': firstName,
        'lastName': lastName,
        'email': email,
        'password': hash_password(password),
        'created_at': datetime.now().isoformat(),
        'reports': []
    }
    
    if save_users(users):
        return {
            'success': True,
            'message': 'User created successfully',
            'user_id': email,
            'user': {
                'email': email,
                'firstName': firstName,
                'lastName': lastName
            }
        }
    else:
        return {
            'success': False,
            'message': 'Error creating user'
        }

def authenticate_user(email, password):
    """Authenticate user credentials"""
    users = load_users()
    
    if email not in users:
        return {
            'success': False,
            'message': 'User not found'
        }
    
    user = users[email]
    if not verify_password(password, user['password']):
        return {
            'success': False,
            'message': 'Invalid password'
        }
    
    # Generate token
    token = generate_token()
    return {
        'success': True,
        'message': 'Login successful',
        'user_id': email,
        'user': {
            'email': email,
            'firstName': user.get('firstName', ''),
            'lastName': user.get('lastName', '')
        },
        'token': token
    }

def get_user(email):
    """Get user information"""
    users = load_users()
    if email in users:
        user = users[email].copy()
        user.pop('password', None)  # Don't return password hash
        return user
    return None

def add_report_to_user(email, report_info):
    """Add a generated report to user's report list"""
    users = load_users()
    
    if email not in users:
        return False
    
    users[email]['reports'].append({
        'report_id': report_info.get('report_id'),
        'file_id': report_info.get('file_id'),
        'created_at': datetime.now().isoformat(),
        'file_path': report_info.get('file_path'),
        'md_file_path': report_info.get('md_file_path') or report_info.get('file_path'),
        'html_file_path': report_info.get('html_file_path'),
        'pdf_file_path': report_info.get('pdf_file_path'),
        'dataset_name': report_info.get('dataset_name')
    })
    
    return save_users(users)
