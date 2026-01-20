from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, StreetIssue
from config import Config
import os
from werkzeug.utils import secure_filename
from functools import wraps

app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Admin required decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('You need admin privileges to access this page.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        
        # Check if user already exists
        if User.query.filter_by(username=username).first():
            return jsonify({'success': False, 'message': 'Username already exists'}), 400
        
        if User.query.filter_by(email=email).first():
            return jsonify({'success': False, 'message': 'Email already exists'}), 400
        
        # Create new user
        user = User(username=username, email=email)
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Registration successful! Please login.'}), 201
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            
            if user.is_admin:
                return jsonify({'success': True, 'redirect': url_for('admin_dashboard')}), 200
            else:
                return jsonify({'success': True, 'redirect': url_for('user_dashboard')}), 200
        
        return jsonify({'success': False, 'message': 'Invalid username or password'}), 401
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_admin:
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('user_dashboard'))

@app.route('/user/dashboard')
@login_required
def user_dashboard():
    return render_template('user_dashboard.html')

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    return render_template('admin_dashboard.html')

# API Routes
@app.route('/api/reports', methods=['GET'])
@login_required
def get_reports():
    if current_user.is_admin:
        # Admin can see all reports
        reports = StreetIssue.query.all()
    else:
        # Regular user can only see their own reports
        reports = StreetIssue.query.filter_by(user_id=current_user.id).all()
    
    return jsonify([report.to_dict() for report in reports])

@app.route('/api/reports/all', methods=['GET'])
@admin_required
def get_all_reports():
    reports = StreetIssue.query.all()
    return jsonify([report.to_dict() for report in reports])

@app.route('/api/reports', methods=['POST'])
@login_required
def create_report():
    try:
        data = request.form
        
        # Handle file upload
        image_path = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                filename = secure_filename(file.filename)
                # Create uploads directory if it doesn't exist
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(image_path)
        
        # Create new report
        report = StreetIssue(
            user_id=current_user.id,
            title=data.get('title'),
            description=data.get('description'),
            latitude=float(data.get('latitude')),
            longitude=float(data.get('longitude')),
            issue_type=data.get('issue_type'),
            severity=data.get('severity', 'medium'),
            image_path=image_path
        )
        
        db.session.add(report)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Report submitted successfully', 'report': report.to_dict()}), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/reports/<int:report_id>', methods=['PUT'])
@login_required
def update_report(report_id):
    report = StreetIssue.query.get_or_404(report_id)
    
    # Only admin or the report owner can update
    if not current_user.is_admin and report.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    data = request.get_json()
    
    if 'status' in data and current_user.is_admin:
        report.status = data['status']
    
    if 'severity' in data and current_user.is_admin:
        report.severity = data['severity']
    
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Report updated successfully', 'report': report.to_dict()})

@app.route('/api/reports/<int:report_id>', methods=['DELETE'])
@login_required
def delete_report(report_id):
    report = StreetIssue.query.get_or_404(report_id)
    
    # Only admin or the report owner can delete
    if not current_user.is_admin and report.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    db.session.delete(report)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Report deleted successfully'})

@app.route('/api/user/stats')
@login_required
def user_stats():
    total_reports = StreetIssue.query.filter_by(user_id=current_user.id).count()
    pending = StreetIssue.query.filter_by(user_id=current_user.id, status='pending').count()
    resolved = StreetIssue.query.filter_by(user_id=current_user.id, status='resolved').count()
    
    return jsonify({
        'total_reports': total_reports,
        'pending': pending,
        'resolved': resolved
    })

@app.route('/api/admin/stats')
@admin_required
def admin_stats():
    total_reports = StreetIssue.query.count()
    total_users = User.query.count()
    pending = StreetIssue.query.filter_by(status='pending').count()
    in_progress = StreetIssue.query.filter_by(status='in-progress').count()
    resolved = StreetIssue.query.filter_by(status='resolved').count()
    
    return jsonify({
        'total_reports': total_reports,
        'total_users': total_users,
        'pending': pending,
        'in_progress': in_progress,
        'resolved': resolved
    })

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # Create default admin user if not exists
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(username='admin', email='admin@example.com', is_admin=True)
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("Default admin created - username: admin, password: admin123")
    
    app.run(debug=True)