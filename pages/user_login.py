"""
User Login/Selection Page
Allows users to select existing user or create new one
"""

import streamlit as st
import sys
import os

# Add the frontend directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.api_client import api_client, safe_api_call, display_api_response

def user_login_page():
    """Render the user login/selection page"""
    st.title("👋 Welcome to Lead Nurturing System")
    st.markdown("---")
    
    # Load existing users
    with st.spinner("Loading users..."):
        users = safe_api_call(api_client.get_users)
    
    if users:
        # Show existing users section
        st.subheader("🔐 Login as Existing User")
        
        # Create user options for selectbox
        user_options = {}
        for user in users:
            user_display = f"{user.get('name', 'Unknown')} ({user.get('email', 'No email')})"
            if user.get('company_name'):
                user_display += f" - {user.get('company_name')}"
            user_options[user_display] = user
        
        # User selection
        selected_user_display = st.selectbox(
            "Select your account:",
            options=list(user_options.keys()),
            help="Choose your existing account to continue"
        )
        
        # Login button
        col1, col2 = st.columns([1, 2])
        
        with col1:
            if st.button("🚀 Login", type="primary", use_container_width=True):
                selected_user = user_options[selected_user_display]
                st.session_state["current_user"] = selected_user
                st.session_state["current_page"] = "dashboard"
                st.success(f"Welcome back, {selected_user.get('name', 'User')}!")
                st.rerun()
        
        with col2:
            # Show selected user details
            if selected_user_display:
                selected_user = user_options[selected_user_display]
                st.info(f"**User ID:** {selected_user.get('user_id')}\n"
                       f"**Email:** {selected_user.get('email')}\n"
                       f"**Company:** {selected_user.get('company_name', 'Not specified')}")
        
        # Divider
        st.markdown("---")
        st.markdown("### OR")
        st.markdown("---")
    
    # Create new user section
    st.subheader("🆕 Create New Account")
    
    if not users:
        st.info("No existing users found. Please create your first account.")
    
    # Quick create form
    with st.form("quick_user_creation"):
        st.markdown("**Quick Account Creation**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("Full Name*", placeholder="Enter your full name")
            email = st.text_input("Email Address*", placeholder="user@example.com")
            company_name = st.text_input("Company Name", placeholder="Your company (optional)")
        
        with col2:
            job_title = st.text_input("Job Title", placeholder="Your role (optional)")
            company_website = st.text_input("Company Website", placeholder="https://example.com (optional)")
            company_description = st.text_area("Company Description", placeholder="Brief description of your company (optional)", height=100)
        
        # Submit button
        create_submitted = st.form_submit_button("Create New Account", type="secondary", use_container_width=True)
        
        if create_submitted:
            # Validate required fields
            if not name or not email:
                st.error("Please fill in Name and Email (required fields)")
                return
            
            # Validate email format
            if "@" not in email or "." not in email.split("@")[1]:
                st.error("Please enter a valid email address")
                return
            
            # Prepare user data
            user_data = {
                "name": name,
                "email": email,
                "auth_provider": "email",
                "job_title": job_title or "",
                "company_name": company_name or "",
                "company_website": company_website or "",
                "company_description": company_description or ""
            }
            
            # Create user via API
            with st.spinner("Creating new account..."):
                response = safe_api_call(api_client.create_user, user_data)
            
            if response:
                display_api_response(response, "Account created successfully! 🎉")
                
                # Auto-login the new user
                if "user_id" in response:
                    st.session_state["current_user"] = response
                    st.session_state["current_page"] = "dashboard"
                    st.success(f"Welcome, {response.get('name')}! Redirecting to dashboard...")
                    st.rerun()
    
    # Advanced creation option
    if st.button("🔧 Advanced Account Setup"):
        st.session_state["current_page"] = "user_creation"
        st.rerun()
    
    # System info
    st.markdown("---")
    
    with st.expander("ℹ️ About This System"):
        st.markdown("""
        **Lead Nurturing Campaign Manager**
        
        This system helps you:
        - **Manage Clients**: Add and organize your prospects and customers
        - **Create Campaigns**: Build personalized email sequences
        - **Track Performance**: Monitor email opens, replies, and engagement
        - **Automate Follow-ups**: Set up automatic follow-up sequences
        - **Analyze Results**: Get insights on campaign effectiveness
        
        **Getting Started:**
        1. Login with existing account or create new one
        2. Add your first client
        3. Create a campaign strategy
        4. Start your email sequences
        """)
    
    # Database stats (if users exist)
    if users:
        with st.expander("📊 System Statistics"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Users", len(users))
            
            with col2:
                # Note: Client count requires specific user_id, so showing N/A for now
                st.metric("Total Clients", "N/A")
            
            with col3:
                try:
                    campaigns = safe_api_call(api_client.get_campaign_executions)
                    campaign_count = len(campaigns) if campaigns else 0
                    st.metric("Active Campaigns", campaign_count)
                except:
                    st.metric("Active Campaigns", "N/A")

def main():
    """Main function to run the user login page"""
    st.set_page_config(
        page_title="Login - Lead Nurturing",
        page_icon="👋",
        layout="wide"
    )
    
    user_login_page()

if __name__ == "__main__":
    main()