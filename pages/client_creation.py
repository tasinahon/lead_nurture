"""
Client Creation Page
Allows users to add new clients to the system
"""

import streamlit as st
import sys
import os

# Add the frontend directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.api_client import api_client, safe_api_call, display_api_response

def client_creation_page():
    """Render the client creation page"""
    st.title("👤 Create New Client")
    st.markdown("---")
    
    # Check if user is logged in
    current_user = st.session_state.get("current_user")
    if not current_user:
        st.error("Please log in first to create clients.")
        return
    
    # Create form for client input
    with st.form("client_creation_form"):
        st.subheader("Client Information")
        
        # Basic information
        col1, col2 = st.columns(2)
        
        with col1:
            full_name = st.text_input("Full Name*", placeholder="John Doe")
            email = st.text_input("Email Address*", placeholder="john@example.com")
            phone = st.text_input("Phone Number", placeholder="+1234567890")
        
        with col2:
            company = st.text_input("Company Name", placeholder="ABC Corporation")
            company_website = st.text_input("Company Website", placeholder="https://example.com")
            category = st.selectbox(
                "Client Category",
                ["Prospect", "Lead", "Customer", "Partner", "Other"],
                help="Select the client category"
            )
        
        # Social media links
        st.subheader("Social Media & Professional Links")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            linkedin_url = st.text_input("LinkedIn URL", placeholder="https://linkedin.com/in/johndoe")
        
        with col2:
            facebook = st.text_input("Facebook URL", placeholder="https://facebook.com/johndoe")
        
        with col3:
            instagram = st.text_input("Instagram URL", placeholder="https://instagram.com/johndoe")
        
        # WhatsApp
        whatsapp = st.text_input("WhatsApp Number", placeholder="+1234567890")
        
        # Form submission
        st.markdown("---")
        submitted = st.form_submit_button("Create Client", type="primary", use_container_width=True)
        
        if submitted:
            # Validate required fields
            if not full_name or not email:
                st.error("Please fill in all required fields (Full Name and Email)")
                return
            
            # Validate email format
            if "@" not in email or "." not in email.split("@")[1]:
                st.error("Please enter a valid email address")
                return
            
            # Prepare client data
            client_data = {
                "user_id": current_user["user_id"],
                "full_name": full_name,
                "email": email,
                "phone": phone or "",
                "company": company or "",  # Empty string is valid
                "company_website": company_website or "",
                "linkedin_url": linkedin_url or "",
                "facebook": facebook or "",
                "instagram": instagram or "",
                "whatsapp": whatsapp or "",
                "category": category
            }
            
            # Create client via API
            with st.spinner("Creating client..."):
                response = safe_api_call(api_client.create_client, current_user["user_id"], client_data)
            
            if response:
                display_api_response(response, "Client created successfully! 🎉")
                
                # Store client in session state and redirect to client details
                if "client_id" in response:
                    st.session_state["selected_client"] = response
                    st.success("Client created! Redirecting to client details...")
    
    # Navigation buttons (outside the form)
    if st.session_state.get("selected_client"):
        st.markdown("### 🎯 Next Steps")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("View Client Details", type="primary"):
                st.session_state["current_page"] = "client_details"
                st.rerun()
        
        with col2:
            if st.button("Create Another Client"):
                st.session_state["selected_client"] = None
                st.rerun()
        
        with col3:
            if st.button("Go to Client List"):
                st.session_state["current_page"] = "client_list"
                st.rerun()
    
    # Additional information section
    st.markdown("---")
    
    with st.expander("ℹ️ Client Creation Tips"):
        st.markdown("""
        **Required Information:**
        - **Full Name**: Client's complete name for personalization
        - **Email Address**: Primary contact method for campaigns
        
        **Optional but Recommended:**
        - **Phone & WhatsApp**: For multi-channel communication
        - **Company Details**: Helps in creating relevant content
        - **Social Media Links**: For research and personalization
        - **Category**: Helps organize and segment your clients
        
        **Next Steps:**
        After creating a client, you can:
        - View and edit their profile
        - Send introductory emails
        - Create personalized campaigns
        - Track engagement and responses
        """)
    
    # Show recent clients
    st.markdown("---")
    st.subheader("📋 Recently Added Clients")
    
    # Get recent clients for current user
    with st.spinner("Loading recent clients..."):
        clients = safe_api_call(api_client.get_clients, current_user["user_id"])
    
    if clients:
        # Show last 5 clients
        recent_clients = sorted(clients, key=lambda x: x.get("created_at", ""), reverse=True)[:5]
        
        for client in recent_clients:
            with st.container():
                col1, col2, col3 = st.columns([2, 2, 1])
                
                with col1:
                    st.write(f"**{client.get('full_name', 'N/A')}**")
                    st.write(f"📧 {client.get('email', 'N/A')}")
                
                with col2:
                    st.write(f"🏢 {client.get('company', 'N/A')}")
                    st.write(f"📅 {client.get('created_at', 'N/A')[:10] if client.get('created_at') else 'N/A'}")
                
                with col3:
                    if st.button("View", key=f"view_{client.get('client_id')}"):
                        st.session_state["selected_client"] = client
                        st.session_state["current_page"] = "client_details"
                        st.rerun()
                
                st.markdown("---")
    
    else:
        st.info("No clients found. Create your first client above! 👆")

def main():
    """Main function to run the client creation page"""
    st.set_page_config(
        page_title="Create Client - Lead Nurturing",
        page_icon="👤",
        layout="wide"
    )
    
    client_creation_page()

if __name__ == "__main__":
    main()