import os
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix
from datetime import datetime, timedelta
import jwt
import pandas as pd
import io
import zlib
import base64
from functools import wraps

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgresql"):
    app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///sales_analytics.db"

app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize database
db = SQLAlchemy(app)

# JWT Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Database Models
class User(db.Model):
    __tablename__ = "users"
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # "admin" or "user"
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    sales_uploads = db.relationship('SalesRecord', backref='uploader', lazy=True)

class SalesRecord(db.Model):
    __tablename__ = "sales_records"
    
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Create tables
with app.app_context():
    db.create_all()

# Authentication helpers
def create_access_token(data: dict):
    """Create a JWT access token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def verify_token(token: str):
    """Verify and decode a JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None

def token_required(f):
    """Decorator to require JWT token"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Get token from Authorization header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]  # Bearer <token>
            except IndexError:
                return jsonify({'error': 'Invalid token format'}), 401
        
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        try:
            payload = verify_token(token)
            if payload is None:
                return jsonify({'error': 'Invalid token'}), 401
            
            current_user = User.query.filter_by(username=payload['sub']).first()
            if not current_user:
                return jsonify({'error': 'User not found'}), 401
                
        except Exception as e:
            return jsonify({'error': 'Invalid token'}), 401
        
        return f(current_user, *args, **kwargs)
    
    return decorated

def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated(current_user, *args, **kwargs):
        if current_user.role != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        return f(current_user, *args, **kwargs)
    
    return decorated

# Routes
@app.route('/')
def index():
    """Serve the main application interface"""
    return render_template('index.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    """Serve static files"""
    return send_from_directory('static', filename)

@app.route('/api/register', methods=['POST'])
def register():
    """Register a new user"""
    data = request.get_json()
    
    if not data or not all(k in data for k in ('username', 'password', 'role')):
        return jsonify({'error': 'Missing required fields'}), 400
    
    if data['role'] not in ['admin', 'user']:
        return jsonify({'error': 'Role must be admin or user'}), 400
    
    # Check if user exists
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already exists'}), 400
    
    # Create new user
    password_hash = generate_password_hash(data['password'])
    new_user = User(
        username=data['username'],
        password_hash=password_hash,
        role=data['role']
    )
    
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({'message': 'User registered successfully', 'user_id': new_user.id}), 201

@app.route('/api/login', methods=['POST'])
def login():
    """Login user and return JWT token"""
    data = request.get_json()
    
    if not data or not all(k in data for k in ('username', 'password')):
        return jsonify({'error': 'Missing username or password'}), 400
    
    user = User.query.filter_by(username=data['username']).first()
    
    if not user or not check_password_hash(user.password_hash, data['password']):
        return jsonify({'error': 'Invalid username or password'}), 401
    
    access_token = create_access_token(data={"sub": user.username})
    
    return jsonify({
        'access_token': access_token,
        'token_type': 'bearer',
        'user': {
            'id': user.id,
            'username': user.username,
            'role': user.role
        }
    })

@app.route('/api/profile', methods=['GET'])
@token_required
def get_profile(current_user):
    """Get current user profile"""
    return jsonify({
        'id': current_user.id,
        'username': current_user.username,
        'role': current_user.role,
        'created_at': current_user.created_at.isoformat()
    })

@app.route('/api/upload-sales', methods=['POST'])
@token_required
@admin_required
def upload_sales(current_user):
    """Upload sales data via CSV (admin only)"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '' or not file.filename.endswith('.csv'):
        return jsonify({'error': 'Please provide a CSV file'}), 400
    
    try:
        # Read CSV content
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        df = pd.read_csv(stream)
        
        # Validate CSV structure
        required_columns = ['customer_name', 'amount', 'date']
        if not all(col in df.columns for col in required_columns):
            return jsonify({
                'error': f'CSV must contain columns: {", ".join(required_columns)}'
            }), 400
        
        # Process and save data
        sales_records = []
        for _, row in df.iterrows():
            try:
                # Parse date
                date_obj = pd.to_datetime(row['date']).to_pydatetime()
                
                sales_record = SalesRecord(
                    customer_name=str(row['customer_name']),
                    amount=float(row['amount']),
                    date=date_obj,
                    uploaded_by=current_user.id
                )
                sales_records.append(sales_record)
            except Exception as e:
                return jsonify({'error': f'Error processing row: {str(e)}'}), 400
        
        # Save to database
        db.session.add_all(sales_records)
        db.session.commit()
        
        return jsonify({
            'message': f'Successfully uploaded {len(sales_records)} sales records',
            'records_count': len(sales_records)
        })
        
    except Exception as e:
        return jsonify({'error': f'Error processing CSV: {str(e)}'}), 400

@app.route('/api/analytics/summary', methods=['GET'])
@token_required
@admin_required
def analytics_summary(current_user):
    """Get sales analytics summary (admin only)"""
    total_sales = db.session.query(db.func.sum(SalesRecord.amount)).scalar() or 0
    total_transactions = db.session.query(db.func.count(SalesRecord.id)).scalar() or 0
    avg_order_value = total_sales / total_transactions if total_transactions > 0 else 0
    
    return jsonify({
        'total_sales': round(total_sales, 2),
        'total_transactions': total_transactions,
        'average_order_value': round(avg_order_value, 2)
    })

@app.route('/api/analytics/top-customers', methods=['GET'])
@token_required
@admin_required
def top_customers(current_user):
    """Get top customers by total sales (admin only)"""
    limit = request.args.get('limit', 3, type=int)
    limit = min(max(limit, 1), 100)  # Ensure limit is between 1 and 100
    
    results = db.session.query(
        SalesRecord.customer_name,
        db.func.sum(SalesRecord.amount).label('total_sales'),
        db.func.count(SalesRecord.id).label('transaction_count')
    ).group_by(
        SalesRecord.customer_name
    ).order_by(
        db.func.sum(SalesRecord.amount).desc()
    ).limit(limit).all()
    
    return jsonify([
        {
            'customer_name': result.customer_name,
            'total_sales': round(result.total_sales, 2),
            'transaction_count': result.transaction_count
        }
        for result in results
    ])

@app.route('/api/analytics/by-date', methods=['GET'])
@token_required
@admin_required
def sales_by_date(current_user):
    """Get sales data filtered by date range (admin only)"""
    from_date = request.args.get('from')
    to_date = request.args.get('to')
    
    if not from_date or not to_date:
        return jsonify({'error': 'Both from and to dates are required'}), 400
    
    try:
        # Parse dates
        start_date = datetime.strptime(from_date, "%Y-%m-%d")
        end_date = datetime.strptime(to_date, "%Y-%m-%d") + timedelta(days=1)
        
        # Query sales records
        sales_records = SalesRecord.query.filter(
            SalesRecord.date >= start_date,
            SalesRecord.date < end_date
        ).order_by(SalesRecord.date.desc()).all()
        
        return jsonify([
            {
                'customer_name': record.customer_name,
                'amount': record.amount,
                'date': record.date.isoformat()
            }
            for record in sales_records
        ])
        
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

@app.route('/api/compress-string', methods=['POST'])
def compress_string():
    """Compress a string using zlib compression"""
    data = request.get_json()
    
    if not data or 'text' not in data:
        return jsonify({'error': 'Text field is required'}), 400
    
    try:
        original_text = data['text']
        original_size = len(original_text.encode('utf-8'))
        
        # Compress the string
        compressed_bytes = zlib.compress(original_text.encode('utf-8'))
        compressed_size = len(compressed_bytes)
        
        # Encode to base64 for safe transport
        compressed_data = base64.b64encode(compressed_bytes).decode('utf-8')
        
        # Calculate compression ratio
        compression_ratio = (original_size - compressed_size) / original_size * 100 if original_size > 0 else 0
        
        return jsonify({
            'original_text': original_text,
            'compressed_data': compressed_data,
            'original_size': original_size,
            'compressed_size': compressed_size,
            'compression_ratio': round(compression_ratio, 2)
        })
        
    except Exception as e:
        return jsonify({'error': f'Compression failed: {str(e)}'}), 400

@app.route('/api/decompress-string', methods=['POST'])
def decompress_string():
    """Decompress a base64-encoded compressed string"""
    compressed_data = request.get_json()
    
    if not compressed_data:
        return jsonify({'error': 'Compressed data is required'}), 400
    
    try:
        # Handle both string and object input
        if isinstance(compressed_data, str):
            data_to_decompress = compressed_data
        else:
            return jsonify({'error': 'Invalid input format'}), 400
        
        # Decode from base64
        compressed_bytes = base64.b64decode(data_to_decompress)
        
        # Decompress
        decompressed_bytes = zlib.decompress(compressed_bytes)
        decompressed_text = decompressed_bytes.decode('utf-8')
        
        return jsonify({
            'decompressed_text': decompressed_text,
            'original_size': len(decompressed_text.encode('utf-8'))
        })
        
    except Exception as e:
        return jsonify({'error': f'Decompression failed: {str(e)}'}), 400

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'message': 'Sales Analytics Platform is running'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)