"""
Configuration file for the Lead Nurturing Frontend
Allows easy switching between local development and production backend URLs
"""

import os
from typing import Optional

class Config:
    """Configuration class for frontend settings"""
    
    # Backend URL - can be overridden by environment variable
    BACKEND_URL = os.getenv(
        "BACKEND_URL", 
        "https://lead-nurturing-chdmhca2e2fbauav.eastus-01.azurewebsites.net"
    )
    
    # API endpoints
    API_BASE = f"{BACKEND_URL}/api"
    
    # Specific API endpoints
    ENDPOINTS = {
        # User Management
        "CREATE_USER": f"{API_BASE}/users/",
        "GET_USERS": f"{API_BASE}/users/",
        
        # Client Management  
        "CREATE_CLIENT": f"{API_BASE}/users/{{user_id}}/clients/",
        "GET_CLIENTS": f"{API_BASE}/users/{{user_id}}/clients/",
        "GET_CLIENT": f"{API_BASE}/clients/{{client_id}}/",
        "GET_CLIENT_PROFILE": f"{API_BASE}/clients/{{client_id}}/profiles/",
        "GET_CLIENT_INTRO_EMAIL": f"{API_BASE}/clients/{{client_id}}/introductory-email/",
        "GET_CLIENT_STRATEGY": f"{API_BASE}/clients/{{client_id}}/initial-strategy/",
        "GET_CLIENT_CAMPAIGNS": f"{API_BASE}/clients/{{client_id}}/campaign-executions/",
        "SEND_INTRO_EMAIL": f"{API_BASE}/clients/{{client_id}}/send-intro-email/",
        
        # Campaign Management
        "GET_CLIENT_AUTO_CAMPAIGNS": f"{API_BASE}/clients/{{client_id}}/auto-campaigns/",
        "GET_CAMPAIGN_PLAN": f"{API_BASE}/campaigns/{{campaign_id}}/plan-for-approval/",
        "SUGGEST_IMPROVEMENT": f"{API_BASE}/campaigns/{{campaign_id}}/suggest-improvements",
        "APPROVE_CAMPAIGN": f"{API_BASE}/campaigns/{{campaign_id}}/plan_approve",
        
        # Follow-up Management
        "GET_CAMPAIGN_EXECUTIONS": f"{API_BASE}/campaign-executions/",
        "GET_INTRO_EMAILS": f"{API_BASE}/introductory-emails/",
        
        # Analytics (optional - may not be available in all deployments)
    }
    
    # App Settings
    APP_TITLE = "Lead Nurturing Campaign Manager"
    PAGE_ICON = "📧"
    LAYOUT = "wide"
    
    # Session state keys
    SESSION_KEYS = {
        "CURRENT_USER": "current_user",
        "SELECTED_CLIENT": "selected_client",
        "CURRENT_PAGE": "current_page"
    }

# Create global config instance
config = Config()

def get_endpoint(endpoint_name: str, **kwargs) -> str:
    """
    Get formatted endpoint URL with parameters
    
    Args:
        endpoint_name: Name of the endpoint from Config.ENDPOINTS
        **kwargs: Parameters to format into the URL
        
    Returns:
        Formatted URL string
    """
    if endpoint_name not in config.ENDPOINTS:
        raise ValueError(f"Unknown endpoint: {endpoint_name}")
    
    url = config.ENDPOINTS[endpoint_name]
    return url.format(**kwargs)

def set_backend_url(url: str) -> None:
    """
    Update backend URL at runtime
    
    Args:
        url: New backend URL
    """
    config.BACKEND_URL = url.rstrip("/")
    config.API_BASE = f"{config.BACKEND_URL}/api"
    
    # Update all endpoints
    for key, endpoint in config.ENDPOINTS.items():
        # Replace the old base URL with new one
        old_base = endpoint.split("/api/")[0]
        new_endpoint = endpoint.replace(old_base, config.BACKEND_URL)
        config.ENDPOINTS[key] = new_endpoint

if __name__ == "__main__":
    # Test configuration
    print(f"Backend URL: {config.BACKEND_URL}")
    print(f"API Base: {config.API_BASE}")
    print(f"Create User Endpoint: {get_endpoint('CREATE_USER')}")
    print(f"Get Client Endpoint: {get_endpoint('GET_CLIENT', client_id=123)}")