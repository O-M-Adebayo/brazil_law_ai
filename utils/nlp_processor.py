import re
import json
import logging
import os
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load the knowledge base
KNOWLEDGE_BASE_PATH = 'knowledge_base/brazilian_housing_laws.json'

def load_knowledge_base() -> Dict[str, Any]:
    """Load the knowledge base from the JSON file."""
    try:
        if os.path.exists(KNOWLEDGE_BASE_PATH):
            with open(KNOWLEDGE_BASE_PATH, 'r', encoding='utf-8') as file:
                return json.load(file)
        else:
            logger.warning(f"Knowledge base file not found at {KNOWLEDGE_BASE_PATH}")
            return {}
    except Exception as e:
        logger.exception(f"Error loading knowledge base: {str(e)}")
        return {}

# Load knowledge base at module import time
knowledge_base = load_knowledge_base()

def preprocess_query(query: str) -> str:
    """
    Preprocess the user query to enhance NLP understanding.
    
    Args:
        query: The user's original query text
        
    Returns:
        The preprocessed query
    """
    # Convert to lowercase
    processed = query.lower()
    
    # Normalize common terms related to Brazilian housing law
    term_mappings = {
        "apartment": "property",
        "flat": "property",
        "house": "property",
        "apt": "property",
        "landlord": "landlord",
        "proprietário": "landlord",
        "dono": "landlord",
        "renter": "tenant", 
        "inquilino": "tenant",
        "locatário": "tenant",
        "contract": "rental contract",
        "contrato": "rental contract",
        "deposit": "security deposit",
        "caução": "security deposit",
        "guarantor": "fiador",
        "garantidor": "fiador"
    }
    
    for term, replacement in term_mappings.items():
        processed = re.sub(r'\b' + term + r'\b', replacement, processed)
    
    # Expand common acronyms and Brazilian-specific terms
    acronym_mappings = {
        "iptu": "Imposto Predial e Territorial Urbano (property tax)",
        "igpm": "Índice Geral de Preços do Mercado (market price index)",
        "ipca": "Índice Nacional de Preços ao Consumidor Amplo (consumer price index)"
    }
    
    for acronym, expansion in acronym_mappings.items():
        processed = re.sub(r'\b' + acronym + r'\b', expansion, processed)
    
    # Add context to the query if it's very short
    if len(processed.split()) < 3:
        processed = f"In the context of Brazilian housing laws and tenant rights, {processed}"
    
    # Check for specific law references
    law_references = [
        "lei do inquilinato", "lei 8245", "lei nº 8.245", 
        "codigo civil", "código civil", "lei 10406",
        "cdc", "codigo de defesa do consumidor"
    ]
    
    for law in law_references:
        if law in processed:
            # If a specific law is mentioned, note that in the query
            if "lei do inquilinato" in processed or "lei 8245" in processed or "lei nº 8.245" in processed:
                processed += " according to the Lei do Inquilinato (Lei nº 8.245/91), the main Brazilian rental law"
            elif "codigo civil" in processed or "código civil" in processed or "lei 10406" in processed:
                processed += " according to the Brazilian Civil Code (Código Civil)"
            elif "cdc" in processed or "codigo de defesa do consumidor" in processed:
                processed += " according to the Brazilian Consumer Protection Code"
            break
    
    # Enhance query with a reminder to cite Brazilian laws
    processed += ". Please cite specific Brazilian laws and articles when applicable."
    
    logger.debug(f"Preprocessed query: {processed}")
    return processed
