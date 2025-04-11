import os
import logging

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
            flash('All fields are required')
            return render_template('register.html')
        
        # Check if username or email already exists
        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            flash('Username or email already exists')
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
        
        flash('Account created successfully!')
        return redirect(url_for('index'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login."""
    if request.method == 'POST':
        from models import User
        
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Find the user
        user = User.query.filter_by(username=username).first()
        
        # Verify credentials
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash('Logged in successfully!')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """Handle user logout."""
    logout_user()
    flash('Logged out successfully!')
    return redirect(url_for('index'))

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
            'citations': citations
        })
        
    except Exception as e:
        logger.exception("Error processing chat request")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
