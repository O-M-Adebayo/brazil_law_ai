import json
import logging
from typing import Dict, List, Any
from utils.local_knowledge_base import get_response_from_knowledge_base

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def get_chat_response(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Get a response for the chat messages using the local knowledge base.
    
    Args:
        messages: A list of message dictionaries with 'role' and 'content' keys.
        
    Returns:
        A dictionary containing the response and citations.
    """
    try:
        # Extract the user's query (the last user message)
        user_query = ""
        for msg in reversed(messages):
            if msg["role"] == "user":
                user_query = msg["content"]
                break
        
        if not user_query:
            return {
                "choices": [
                    {
                        "message": {
                            "content": "I didn't receive a question. How can I help you with Brazilian housing laws today?"
                        }
                    }
                ],
                "citations": []
            }
        
        logger.debug(f"Processing query: {user_query}")
        
        # Use our local knowledge base to get a response
        response_data = get_response_from_knowledge_base(user_query)
        logger.debug(f"Generated response from local knowledge base")
        
        return response_data
        
    except Exception as e:
        logger.exception(f"Error in get_chat_response: {str(e)}")
        return {
            "choices": [
                {
                    "message": {
                        "content": "I apologize, but I encountered an error while processing your request. Could you please try asking your question again, perhaps with different wording?"
                    }
                }
            ],
            "citations": []
        }
