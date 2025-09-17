"""
API Client for Lead Nurturing Frontend
Handles all API communications with the backend
"""

import requests
import streamlit as st
from typing import Dict, Any, List, Optional
import json
from config import config, get_endpoint

class APIClient:
    """Centralized API client for all backend communications"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def _make_request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """
        Make HTTP request with error handling
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            url: Request URL
            **kwargs: Additional arguments for requests
            
        Returns:
            Response data as dictionary
            
        Raises:
            Exception: If request fails
        """
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            
            # Handle empty responses
            if response.status_code == 204 or not response.content:
                return {"success": True}
                
            return response.json()
            
        except requests.exceptions.RequestException as e:
            error_msg = f"API request failed: {str(e)}"
            if hasattr(e.response, 'text'):
                error_msg += f" - {e.response.text}"
            st.error(error_msg)
            raise Exception(error_msg)
    
    # User Management
    def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new user"""
        url = get_endpoint("CREATE_USER")
        return self._make_request("POST", url, json=user_data)
    
    def get_users(self) -> List[Dict[str, Any]]:
        """Get all users"""
        url = get_endpoint("GET_USERS")
        return self._make_request("GET", url)
    
    # Client Management
    def create_client(self, user_id: int, client_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new client for a specific user"""
        url = get_endpoint("CREATE_CLIENT", user_id=user_id)
        return self._make_request("POST", url, json=client_data)
    
    def get_clients(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all clients for a specific user"""
        url = get_endpoint("GET_CLIENTS", user_id=user_id)
        return self._make_request("GET", url)
    
    def get_client(self, client_id: int) -> Dict[str, Any]:
        """Get specific client details"""
        url = get_endpoint("GET_CLIENT", client_id=client_id)
        return self._make_request("GET", url)
    
    def get_client_profile(self, client_id: int) -> Dict[str, Any]:
        """Get client profile information"""
        url = get_endpoint("GET_CLIENT_PROFILE", client_id=client_id)
        return self._make_request("GET", url)
    
    def get_client_intro_email(self, client_id: int) -> Dict[str, Any]:
        """Get client's introductory email details"""
        url = get_endpoint("GET_CLIENT_INTRO_EMAIL", client_id=client_id)
        return self._make_request("GET", url)
    
    def get_client_strategy(self, client_id: int) -> Dict[str, Any]:
        """Get client's strategy details"""
        url = get_endpoint("GET_CLIENT_STRATEGY", client_id=client_id)
        return self._make_request("GET", url)
    
    def get_client_campaigns(self, client_id: int) -> List[Dict[str, Any]]:
        """Get client's campaign executions"""
        url = get_endpoint("GET_CLIENT_CAMPAIGNS", client_id=client_id)
        return self._make_request("GET", url)
    
    def send_intro_email(self, client_id: int, user_id: int) -> Dict[str, Any]:
        """Send introductory email to a client"""
        url = get_endpoint("SEND_INTRO_EMAIL", client_id=client_id)
        params = {"user_id": user_id}
        return self._make_request("POST", url, params=params)
    
    # Campaign Management
    def get_client_auto_campaigns(self, client_id: int) -> List[Dict[str, Any]]:
        """Get auto campaigns for a client"""
        url = get_endpoint("GET_CLIENT_AUTO_CAMPAIGNS", client_id=client_id)
        return self._make_request("GET", url)
    
    def get_campaign_plan(self, campaign_id: int) -> Dict[str, Any]:
        """Get campaign plan for approval"""
        url = get_endpoint("GET_CAMPAIGN_PLAN", campaign_id=campaign_id)
        return self._make_request("GET", url)
    
    def suggest_improvement(self, campaign_id: int, improvement_data: Dict[str, Any]) -> Dict[str, Any]:
        """Submit campaign improvement suggestion"""
        url = get_endpoint("SUGGEST_IMPROVEMENT", campaign_id=campaign_id)
        return self._make_request("POST", url, json=improvement_data)
    
    def approve_campaign(self, campaign_id: int, approval_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Approve a campaign"""
        url = get_endpoint("APPROVE_CAMPAIGN", campaign_id=campaign_id)
        # Simple approval endpoint doesn't require request body
        return self._make_request("POST", url)
    
    # Follow-up Management
    def get_campaign_executions(self) -> List[Dict[str, Any]]:
        """Get all campaign executions (follow-up emails) without parameters"""
        url = get_endpoint("GET_CAMPAIGN_EXECUTIONS")
        return self._make_request("GET", url)
    
    def get_intro_emails(self, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get introductory emails"""
        url = get_endpoint("GET_INTRO_EMAILS")
        params = {"user_id": user_id} if user_id else {}
        return self._make_request("GET", url, params=params)
    
    # Analytics
    
    # Database Management
    def get_database_counts(self) -> Dict[str, Any]:
        """Get database statistics (if available)"""
        try:
            # This endpoint may not exist in all deployments
            url = f"{get_endpoint('GET_USERS').replace('/users/', '/stats/')}"
            return self._make_request("GET", url)
        except:
            # Return basic counts from available data
            return {
                "users": len(self.get_users() or []),
                "message": "Basic stats only"
            }

# Create global API client instance
api_client = APIClient()

# Utility functions for common operations
def handle_api_error(func):
    """Decorator to handle API errors gracefully"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            st.error(f"API Error: {str(e)}")
            return None
    return wrapper

@handle_api_error
def safe_api_call(api_method, *args, **kwargs):
    """Safely call API method with error handling"""
    return api_method(*args, **kwargs)

def display_api_response(response: Dict[str, Any], success_message: str = "Operation completed successfully!"):
    """Display API response with appropriate styling"""
    if response:
        if "error" in response:
            st.error(f"Error: {response['error']}")
        else:
            st.success(success_message)
            if st.checkbox("Show response details"):
                st.json(response)
    else:
        st.error("No response received from API")

if __name__ == "__main__":
    # Test API client
    client = APIClient()
    try:
        counts = client.get_database_counts()
        print("Database counts:", counts)
    except Exception as e:
        print(f"Error testing API client: {e}")