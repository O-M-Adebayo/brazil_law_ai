import json
import logging
import re
from typing import Dict, List, Any
from utils.nlp_processor import load_knowledge_base

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load knowledge base
knowledge_base = load_knowledge_base()

def get_relevant_info(query: str) -> str:
    """
    Get relevant information from the knowledge base for the user query.
    
    Args:
        query: The user's query
        
    Returns:
        A formatted response string
    """
    query = query.lower()
    response = ""
    
    # Check for tenant rights related queries
    if any(term in query for term in ["tenant", "rights", "inquilino", "direitos"]):
        if "tenant_rights" in knowledge_base:
            tenant_rights = knowledge_base["tenant_rights"]
            rights = tenant_rights.get("basic_rights", [])
            
            response = "As a tenant in Brazil, you have these rights under the Lei do Inquilinato (Lei nº 8.245/91):\n\n"
            for right in rights:
                response += f"- {right}\n"
            
            # Add rent adjustment info
            rent_info = tenant_rights.get("rent_adjustments", {})
            if rent_info:
                response += f"\nRegarding rent: {rent_info.get('description', '')}"
            
            # Add security deposit info
            deposit_info = tenant_rights.get("security_deposits", {})
            if deposit_info:
                response += f"\n\nRegarding deposits: {deposit_info.get('description', '')}"
    
    # Check for landlord obligation queries
    elif any(term in query for term in ["landlord", "obligations", "proprietário", "dono"]):
        if "landlord_obligations" in knowledge_base:
            landlord_info = knowledge_base["landlord_obligations"]
            duties = landlord_info.get("main_duties", [])
            
            response = "In Brazil, landlords have these obligations under the Lei do Inquilinato (Lei nº 8.245/91):\n\n"
            for duty in duties:
                response += f"- {duty}\n"
            
            # Add illegal practices
            illegal = landlord_info.get("illegal_practices", [])
            if illegal:
                response += "\nLandlords are prohibited from:\n"
                for practice in illegal:
                    response += f"- {practice}\n"
    
    # Check for contract related queries
    elif any(term in query for term in ["contract", "contrato", "lease", "agreement"]):
        if "rental_contracts" in knowledge_base:
            contract_info = knowledge_base["rental_contracts"]
            types = contract_info.get("types", {})
            
            response = "In Brazil, rental contracts are governed by the Lei do Inquilinato (Lei nº 8.245/91):\n\n"
            
            if "fixed_term" in types:
                fixed = types["fixed_term"]
                response += f"Fixed-term contracts: {fixed.get('description', '')}\n\n"
            
            if "indefinite_term" in types:
                indef = types["indefinite_term"]
                response += f"Indefinite-term contracts: {indef.get('description', '')}\n\n"
            
            # Add document requirements
            docs = contract_info.get("required_documents", {}).get("for_tenants", [])
            if docs:
                response += "Required documents typically include:\n"
                for doc in docs:
                    response += f"- {doc}\n"
    
    # Check for eviction related queries
    elif any(term in query for term in ["eviction", "despejo", "removal", "kicked out"]):
        if "eviction_process" in knowledge_base:
            eviction_info = knowledge_base["eviction_process"]
            grounds = eviction_info.get("grounds", [])
            
            response = "In Brazil, eviction (despejo) can only occur on these grounds under the Lei do Inquilinato (Lei nº 8.245/91):\n\n"
            for ground in grounds:
                response += f"- {ground}\n"
            
            # Add procedure info
            procedure = eviction_info.get("procedure", {})
            if procedure:
                steps = procedure.get("steps", [])
                if steps:
                    response += "\nThe eviction process follows these steps:\n"
                    for i, step in enumerate(steps, 1):
                        response += f"{i}. {step}\n"
    
    # Check for dispute related queries
    elif any(term in query for term in ["dispute", "conflict", "problem", "issue"]):
        if "common_disputes" in knowledge_base:
            dispute_info = knowledge_base["common_disputes"]
            
            response = "Common disputes between landlords and tenants in Brazil include:\n\n"
            
            if "repair_issues" in dispute_info:
                repairs = dispute_info["repair_issues"]
                response += f"Repairs: {repairs.get('description', '')} "
                response += f"Resolution: {repairs.get('resolution', '')}\n\n"
            
            if "rent_increases" in dispute_info:
                rent = dispute_info["rent_increases"]
                response += f"Rent increases: {rent.get('description', '')} "
                response += f"Resolution: {rent.get('resolution', '')}\n\n"
            
            if "security_deposit" in dispute_info:
                deposit = dispute_info["security_deposit"]
                response += f"Security deposits: {deposit.get('description', '')} "
                response += f"Resolution: {deposit.get('resolution', '')}\n\n"
    
    # General response if no specific match
    else:
        response = "Brazilian housing laws, particularly the Lei do Inquilinato (Lei nº 8.245/91), cover various aspects of the landlord-tenant relationship including:\n\n"
        response += "- Tenant rights and protections\n"
        response += "- Landlord obligations and responsibilities\n"
        response += "- Rental contract requirements and terms\n"
        response += "- Eviction procedures and tenant protections\n"
        response += "- Common dispute resolution mechanisms\n\n"
        response += "Could you please specify which aspect of Brazilian housing laws you're interested in?"
    
    return response

def get_citations() -> List[str]:
    """Get standard citations for Brazilian housing laws"""
    return [
        "http://www.planalto.gov.br/ccivil_03/leis/l8245.htm",  # Lei do Inquilinato
        "http://www.planalto.gov.br/ccivil_03/leis/2002/l10406.htm"  # Código Civil
    ]

def get_response_from_knowledge_base(query: str) -> Dict[str, Any]:
    """
    Get a response from the local knowledge base.
    
    Args:
        query: The user's query
        
    Returns:
        A dictionary with the response text and citations
    """
    try:
        response_text = get_relevant_info(query)
        citations = get_citations()
        
        return {
            "choices": [
                {
                    "message": {
                        "content": response_text
                    }
                }
            ],
            "citations": citations
        }
    except Exception as e:
        logger.exception(f"Error processing query: {str(e)}")
        return {
            "choices": [
                {
                    "message": {
                        "content": "I apologize, but I encountered an error processing your request. Could you please try asking your question in a different way?"
                    }
                }
            ],
            "citations": []
        }