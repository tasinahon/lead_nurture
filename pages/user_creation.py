"""
User Creation Page
Allows new users to register in the system
"""

import streamlit as st
import sys
import os

# Add the frontend directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.api_client import api_client, safe_api_call, display_api_response

def user_creation_page():
    """Render the user creation page"""
    st.title("🆕 Create New User")
    st.markdown("---")
    
    # Create form for user input
    with st.form("user_creation_form"):
        st.subheader("User Information")
        
        # User input fields
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("Full Name*", placeholder="Enter your full name")
            email = st.text_input("Email Address*", placeholder="user@example.com")
            auth_provider = st.selectbox(
                "Authentication Provider*", 
                ["google", "microsoft", "email"],
                help="Choose your preferred login method"
            )
        
        with col2:
            job_title = st.text_input("Job Title", placeholder="e.g., Sales Manager")
            company_name = st.text_input("Company Name", placeholder="Your company name")
            company_website = st.text_input("Company Website", placeholder="https://example.com")
        
        # Company description
        company_description = st.text_area(
            "Company Description", 
            placeholder="Brief description of your company and services...",
            height=100
        )
        
        # Form submission
        st.markdown("---")
        submitted = st.form_submit_button("Create User", type="primary", use_container_width=True)
        
        if submitted:
            # Validate required fields
            if not name or not email:
                st.error("Please fill in all required fields (marked with *)")
                return
            
            # Validate email format
            if "@" not in email or "." not in email.split("@")[1]:
                st.error("Please enter a valid email address")
                return
            
            # Prepare user data
            user_data = {
                "name": name,
                "email": email,
                "auth_provider": auth_provider,
                "job_title": job_title or "",
                "company_name": company_name or "",
                "company_website": company_website or "",
                "company_description": company_description or ""
            }
            
            # Create user via API
            with st.spinner("Creating user..."):
                response = safe_api_call(api_client.create_user, user_data)
            
            if response:
                display_api_response(response, "User created successfully! 🎉")
                
                # Store user in session state for immediate use
                if "user_id" in response:
                    st.session_state["current_user"] = response
                    st.success("You can now proceed to the main dashboard!")
    
    # Navigation button (outside the form)
    if st.session_state.get("current_user"):
        if st.button("Go to Dashboard", type="primary"):
            st.session_state["current_page"] = "dashboard"
            st.rerun()
    
    # Additional information section
    st.markdown("---")
    
    with st.expander("ℹ️ Information"):
        st.markdown("""
        **About User Creation:**
        
        - **Name & Email**: Required for identification and communication
        - **Auth Provider**: Choose how you'll log in to the system
        - **Company Details**: Optional but recommended for better personalization
        - **Company Description**: Helps in creating better email campaigns
        
        **Next Steps:**
        After creating your account, you'll be able to:
        - Add and manage clients
        - Create personalized email campaigns  
        - Track email performance and replies
        - Manage follow-up sequences
        """)
    
    # Debug section (only show in development)
    if st.sidebar.checkbox("Show Debug Info"):
        st.sidebar.markdown("### Debug Information")
        
        # Test API connection
        if st.sidebar.button("Test API Connection"):
            with st.spinner("Testing connection..."):
                try:
                    counts = safe_api_call(api_client.get_database_counts)
                    if counts:
                        st.sidebar.success("✅ API connection successful!")
                        st.sidebar.json(counts)
                    else:
                        st.sidebar.error("❌ API connection failed")
                except Exception as e:
                    st.sidebar.error(f"❌ Connection error: {str(e)}")

def main():
    """Main function to run the user creation page"""
    st.set_page_config(
        page_title="Create User - Lead Nurturing",
        page_icon="🆕",
        layout="wide"
    )
    
    user_creation_page()

if __name__ == "__main__":
    main()