"""
Main Dashboard for Lead Nurturing Campaign Manager
Central hub with navigation to all features
"""

import streamlit as st
import sys
import os

# Add the frontend directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from pages.user_creation import user_creation_page
from pages.user_login import user_login_page
from pages.client_creation import client_creation_page
from pages.client_list import client_list_page
from pages.send_intro_mail import send_intro_mail_page
from pages.follow_up_dashboard import follow_up_dashboard_page
from pages.client_details import client_details_page
from pages.profile_view import profile_view_page
from pages.strategy_view import strategy_view_page
from pages.intro_mail_view import intro_mail_view_page
from pages.campaign_plan import campaign_plan_page
from utils.api_client import api_client, safe_api_call
from config import config

def initialize_session_state():
    """Initialize session state variables"""
    if "current_page" not in st.session_state:
        st.session_state["current_page"] = "user_login"
    if "current_user" not in st.session_state:
        st.session_state["current_user"] = None
    if "selected_client" not in st.session_state:
        st.session_state["selected_client"] = None

def render_header():
    """Render the main header and navigation"""
    st.title(f"{config.PAGE_ICON} {config.APP_TITLE}")
    
    # Check if user is logged in
    if st.session_state.get("current_user"):
        user = st.session_state["current_user"]
        st.success(f"Welcome back, {user.get('name', 'User')}! 👋")
        
        # Navigation tabs
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "🏠 Dashboard", 
            "👤 Create Client", 
            "📋 Show All Clients", 
            "📧 Send Intro Mail", 
            "📬 Follow-up Mails"
        ])
        
        with tab1:
            dashboard_content()
        
        with tab2:
            client_creation_page()
            
        with tab3:
            client_list_page()
            
        with tab4:
            send_intro_mail_page(show_header=False)
            
        with tab5:
            follow_up_dashboard_page()
    else:
        st.info("Please create a user account to get started.")
        st.session_state["current_page"] = "user_login"

def dashboard_content():
    """Render the main dashboard content"""
    st.subheader("📊 Campaign Overview")
    
    # Simple dashboard without external API calls
    st.info("📊 Welcome to your Lead Nurturing Campaign Manager!")
    
    # Quick actions (always available)
    st.subheader("🚀 Quick Actions")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("➕ Add New Client", use_container_width=True):
            st.session_state["current_page"] = "create_client"
            st.rerun()
    
    with col2:
        if st.button("📧 Send Intro Email", use_container_width=True):
            st.session_state["current_page"] = "send_intro_mail"
            st.rerun()
    
    with col3:
        if st.button("📋 View All Clients", use_container_width=True):
            st.session_state["current_page"] = "client_list"
            st.rerun()
    
    with col4:
        if st.button("📬 Follow-up Status", use_container_width=True):
            st.session_state["current_page"] = "follow_up_dashboard"
            st.rerun()
    
    # Simple instructions
    st.markdown("---")
    st.markdown("""
    ### 📋 Getting Started:
    1. **Create Client** - Add new clients to your system
    2. **View All Clients** - See and manage existing clients
    3. **Follow-up Mails** - Monitor your follow-up email campaigns
    
    Navigate using the tabs above to access all features.
    """)

def render_sidebar():
    """Render the sidebar with user info and settings"""
    with st.sidebar:
        st.title("⚙️ Settings")
        
        # User info
        if st.session_state.get("current_user"):
            user = st.session_state["current_user"]
            st.markdown("### 👤 Current User")
            st.write(f"**Name:** {user.get('name', 'N/A')}")
            st.write(f"**Email:** {user.get('email', 'N/A')}")
            
            # Navigation buttons
            st.markdown("---")
            if st.button("🏠 Main Page", use_container_width=True):
                st.session_state["current_page"] = "dashboard"
                st.session_state["selected_client"] = None  # Clear selected client
                st.rerun()
            
            if st.button("� Send Intro Mail", use_container_width=True):
                st.session_state["current_page"] = "send_intro_mail"
                st.session_state["selected_client"] = None  # Clear selected client
                st.rerun()
            
            if st.button("�🚪 Switch User", use_container_width=True):
                st.session_state["current_user"] = None
                st.session_state["current_page"] = "user_login"
                st.rerun()
        
        # Backend URL configuration
        st.markdown("---")
        st.markdown("### 🔗 Backend Configuration")
        
        current_url = config.BACKEND_URL
        st.write(f"**Current URL:** {current_url}")
        
        with st.expander("Change Backend URL"):
            new_url = st.text_input(
                "Backend URL", 
                value=current_url,
                help="Enter the backend URL (without /api suffix)"
            )
            if st.button("Update URL"):
                from config import set_backend_url
                set_backend_url(new_url)
                st.success("Backend URL updated!")
                st.rerun()
        
        # API status
        st.markdown("---")
        st.markdown("### 🔍 API Status")
        
        current_url = config.BACKEND_URL
        if "azurewebsites.net" in current_url:
            st.success("✅ Connected to Azure Backend")
        else:
            st.info("🔗 Custom Backend URL configured")

def route_pages():
    """Route to appropriate page based on current_page state"""
    current_page = st.session_state.get("current_page", "user_creation")
    
    if current_page == "user_login":
        user_login_page()
    
    elif current_page == "user_creation":
        user_creation_page()
    
    elif current_page == "create_client":
        client_creation_page()
    
    elif current_page == "client_list":
        client_list_page()
    
    elif current_page == "follow_up_dashboard":
        follow_up_dashboard_page()
    
    elif current_page == "client_details":
        client_details_page()
    
    elif current_page == "profile_view":
        profile_view_page()
    
    elif current_page == "strategy_view":
        strategy_view_page()
    
    elif current_page == "intro_mail_view":
        intro_mail_view_page()
    
    elif current_page == "campaign_plan":
        campaign_plan_page()
    
    elif current_page == "send_intro_mail":
        send_intro_mail_page()
    
    else:
        st.error(f"Unknown page: {current_page}")

def main():
    """Main application function"""
    # Set page config
    st.set_page_config(
        page_title=config.APP_TITLE,
        page_icon=config.PAGE_ICON,
        layout=config.LAYOUT,
        initial_sidebar_state="expanded"
    )
    
    # Initialize session state
    initialize_session_state()
    
    # Render sidebar
    render_sidebar()
    
    # Check if user is logged in
    if not st.session_state.get("current_user"):
        # Show user login page if no user is logged in
        user_login_page()
    else:
        # Check if we need to show a specific detail page
        current_page = st.session_state.get("current_page", "dashboard")
        
        if current_page in ["client_details", "profile_view", "strategy_view", "intro_mail_view", "campaign_plan"]:
            # Show detail pages directly
            route_pages()
        elif current_page in ["dashboard", "create_client", "client_list", "follow_up_dashboard", "send_intro_mail"]:
            # Show main dashboard with tabs navigation
            render_header()
        else:
            # Route to specific pages
            route_pages()

if __name__ == "__main__":
    main()