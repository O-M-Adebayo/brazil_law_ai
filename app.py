import os
import logging

from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
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

# Configure the database, using SQLite for simplicity
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///chatbot.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
# initialize the app with the extension
db.init_app(app)

with app.app_context():
    # Make sure to import the models here
    import models  # noqa: F401
    db.create_all()

@app.route('/')
def index():
    """Render the main chat interface."""
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    """Process chat messages and return responses."""
    try:
        data = request.json
        user_message = data.get('message', '')
        chat_history = data.get('history', [])
        
        if not user_message:
            return jsonify({'error': 'No message provided'}), 400
        
        # Preprocess the query
        processed_query = preprocess_query(user_message)
        logger.debug(f"Processed query: {processed_query}")
        
        # Build the message history for the Perplexity API
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
        
        # Get response from Perplexity API
        response_data = get_chat_response(messages)
        
        # Extract the assistant's message and citations
        assistant_message = response_data.get('choices', [{}])[0].get('message', {}).get('content', '')
        citations = response_data.get('citations', [])
        
        return jsonify({
            'response': assistant_message,
            'citations': citations
        })
        
    except Exception as e:
        logger.exception("Error processing chat request")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
