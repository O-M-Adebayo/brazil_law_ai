import os
import logging
from functools import wraps
from datetime import datetime

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from utils.perplexity_client import get_chat_response
from utils.nlp_processor import preprocess_query

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
# create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # needed for url_for to generate with https

# Configure the database using PostgreSQL
database_url = os.environ.get("DATABASE_URL")
logger.info(f"Database URL: {database_url}")
if not database_url:
    logger.error("DATABASE_URL environment variable is not set")
    database_url = "sqlite:///chatbot.db"  # Fallback to SQLite

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
# initialize the app with the extension
db.init_app(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

with app.app_context():
    # Make sure to import the models here
    import models  # noqa: F401
    db.create_all()

@app.route('/')
def index():
    """Render the main chat interface."""
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Handle user registration."""
    if request.method == 'POST':
        from models import User
        
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Validate input data
        if not username or not email or not password:
            flash('All fields are required', 'danger')
            return render_template('register.html')
        
        # Validate username length
        if len(username) < 3 or len(username) > 20:
            flash('Username must be between 3 and 20 characters', 'danger')
            return render_template('register.html')
        
        # Validate email format
        if '@' not in email or '.' not in email:
            flash('Please enter a valid email address', 'danger')
            return render_template('register.html')
        
        # Validate password strength
        if len(password) < 8:
            flash('Password must be at least 8 characters long', 'danger')
            return render_template('register.html')
        
        # Check if username or email already exists
        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            if existing_user.username == username:
                flash('Username already exists', 'danger')
            else:
                flash('Email already exists', 'danger')
            return render_template('register.html')
        
        # Create new user
        new_user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password)
        )
        
        # Add to database
        db.session.add(new_user)
        db.session.commit()
        
        # Log in the new user
        login_user(new_user)
        
        flash('Account created successfully! You are now logged in.', 'success')
        return redirect(url_for('index'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login."""
    if request.method == 'POST':
        from models import User
        
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Validate input data
        if not username or not password:
            flash('Both username and password are required', 'danger')
            return render_template('login.html')
        
        # Find the user
        user = User.query.filter_by(username=username).first()
        
        # Verify credentials
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash('Logged in successfully! Welcome back.', 'success')
            
            # Redirect to the page the user was trying to access, or index
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password. Please try again.', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """Handle user logout."""
    logout_user()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/profile')
@login_required
def profile():
    """Display user profile and chat history."""
    from models import ChatQuery
    
    # Get user's chat history, ordered by most recent
    chat_history = ChatQuery.query.filter_by(user_id=current_user.id).order_by(ChatQuery.timestamp.desc()).all()
    
    return render_template('profile.html', chat_history=chat_history)

def admin_required(f):
    """Decorator for routes that require admin access."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('You need admin privileges to access this page.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    """Admin dashboard for system analytics."""
    from models import User, ChatQuery
    from sqlalchemy import func
    
    # Get basic stats
    total_users = User.query.count()
    total_queries = ChatQuery.query.count()
    
    # Get recent queries for analytics
    recent_queries = ChatQuery.query.order_by(ChatQuery.timestamp.desc()).limit(20).all()
    
    # Get most active users
    active_users = db.session.query(
        User, func.count(ChatQuery.id).label('query_count')
    ).join(User.queries).group_by(User).order_by(func.count(ChatQuery.id).desc()).limit(5).all()
    
    # Get common query terms (simplified)
    # In a real system, you might want to use NLP or more sophisticated analysis
    
    return render_template(
        'admin/dashboard.html',
        total_users=total_users,
        total_queries=total_queries,
        recent_queries=recent_queries,
        active_users=active_users
    )

@app.route('/api/feedback', methods=['POST'])
def submit_feedback():
    """Handle feedback submission for chat responses."""
    try:
        data = request.json
        query_id = data.get('query_id')
        rating = data.get('rating')
        comments = data.get('comments', '')
        
        if not query_id or not rating:
            return jsonify({'error': 'Query ID and rating are required'}), 400
        
        # Validate rating (1-5)
        try:
            rating = int(rating)
            if rating < 1 or rating > 5:
                return jsonify({'error': 'Rating must be between 1 and 5'}), 400
        except ValueError:
            return jsonify({'error': 'Rating must be a number'}), 400
        
        # Get the chat query
        from models import ChatQuery
        query = ChatQuery.query.get(query_id)
        
        if not query:
            return jsonify({'error': 'Chat query not found'}), 404
        
        # Update feedback
        query.has_feedback = True
        query.feedback_rating = rating
        query.feedback_comments = comments
        query.feedback_timestamp = datetime.utcnow()
        
        # Save to database
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Feedback submitted successfully'})
        
    except Exception as e:
        logger.exception("Error submitting feedback")
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    """Process chat messages and return responses."""
    try:
        data = request.json
        user_message = data.get('message', '')
        chat_history = data.get('history', [])
        
        # Get user_id from current_user if logged in
        user_id = None
        if current_user.is_authenticated:
            user_id = current_user.id
        
        if not user_message:
            return jsonify({'error': 'No message provided'}), 400
        
        # Preprocess the query
        processed_query = preprocess_query(user_message)
        logger.debug(f"Processed query: {processed_query}")
        
        # Build the message history for the knowledge base
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a helpful assistant specializing in Brazilian housing laws, tenant rights, "
                    "and rental obligations. Provide accurate, concise information based on current Brazilian "
                    "legal frameworks. Always provide references to relevant laws when possible. "
                    "If you're unsure about something, admit it rather than providing incorrect information. "
                    "Remember that your responses should not be considered professional legal advice."
                )
            }
        ]
        
        # Add chat history (maintaining alternating user/assistant pattern)
        for i, msg in enumerate(chat_history):
            role = "user" if i % 2 == 0 else "assistant"
            messages.append({"role": role, "content": msg})
            
        # Add the current user query
        messages.append({"role": "user", "content": processed_query})
        
        # Get response from knowledge base
        response_data = get_chat_response(messages)
        
        # Extract the assistant's message and citations
        assistant_message = response_data.get('choices', [{}])[0].get('message', {}).get('content', '')
        citations = response_data.get('citations', [])
        
        # Store the query in the database for analytics
        from models import ChatQuery
        
        # Create a new ChatQuery
        chat_query = ChatQuery(
            user_id=user_id,  # This will be None for anonymous users
            query_text=processed_query,
            response_text=assistant_message
        )
        
        # Add to the database
        db.session.add(chat_query)
        db.session.commit()
        logger.info(f"Stored chat query with ID: {chat_query.id}")
        
        return jsonify({
            'response': assistant_message,
            'citations': citations,
            'query_id': chat_query.id  # Include the query ID for feedback
        })
        
    except Exception as e:
        logger.exception("Error processing chat request")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
