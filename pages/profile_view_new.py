"""
Profile View Page
Displays detailed client profile information from API
"""

import streamlit as st
import sys
import os

# Add the frontend directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.api_client import api_client, safe_api_call

def profile_view_page():
    """Render the profile view page"""
    
    # Check if client is selected
    selected_client = st.session_state.get("selected_client")
    if not selected_client:
        st.error("No client selected. Please select a client first.")
        if st.button("Go to Client List"):
            st.session_state["current_page"] = "client_list"
            st.rerun()
        return
    
    client_id = selected_client["client_id"]
    client_name = selected_client.get("full_name", "Client")
    
    # Back button at the top
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("⬅️ Back to Client Details"):
            st.session_state["current_page"] = "client_details"
            st.rerun()
    
    # Page header
    st.title(f"👤 Profile - {client_name}")
    st.markdown("---")
    
    # Load client profile
    with st.spinner("Loading client profile..."):
        profile_data = safe_api_call(api_client.get_client_profile, client_id)
    
    if not profile_data:
        st.warning("No detailed profile found for this client.")
        st.info("Profile information will be available after the initial scraping and analysis process.")
        
        # Show basic client information from session state
        st.subheader("📋 Basic Client Information")
        st.write(f"**Full Name:** {selected_client.get('full_name', 'N/A')}")
        st.write(f"**Email:** {selected_client.get('email', 'N/A')}")
        st.write(f"**Company:** {selected_client.get('company', 'N/A')}")
        st.write(f"**Status:** {selected_client.get('status', 'N/A')}")
        return
    
    # Display profile data from the API  
    st.success("✅ Profile data loaded successfully!")
    
    # Basic Information Section
    st.subheader("👤 Client Information")
    info_col1, info_col2 = st.columns(2)
    
    with info_col1:
        st.write(f"**Full Name:** {selected_client.get('full_name', 'N/A')}")
        st.write(f"**Email:** {selected_client.get('email', 'N/A')}")
        st.write(f"**Company:** {selected_client.get('company', 'N/A')}")
    
    with info_col2:
        st.write(f"**Client ID:** {profile_data.get('client_id', 'N/A')}")
        st.write(f"**Preferred Language:** {profile_data.get('preferred_language', 'N/A')}")
        st.write(f"**Preferred Contact:** {profile_data.get('preferred_contact', 'N/A')}")
    
    # Profile Summary
    st.markdown("---")
    st.subheader("📝 Profile Summary")
    if profile_data.get('summary'):
        st.write(profile_data.get('summary'))
    else:
        st.info("No summary available")
    
    # Interests Section
    st.markdown("---")
    st.subheader("🎯 Interests & Expertise")
    if profile_data.get('interests'):
        interests = profile_data.get('interests', '').split(',')
        
        # Display interests as styled tags
        st.write("**Key Areas of Interest:**")
        cols = st.columns(3)
        for i, interest in enumerate(interests):
            if interest.strip():
                with cols[i % 3]:
                    st.markdown(f"🔸 `{interest.strip()}`")
    else:
        st.info("No interests data available")
    
    # Engagement Times
    st.markdown("---")
    st.subheader("⏰ Engagement Information")
    engagement_times = profile_data.get('engagement_times')
    if engagement_times and engagement_times.strip():
        st.write(f"**Best Contact Times:** {engagement_times}")
    else:
        st.info("No engagement times specified")
    
    # Full Profile Text
    st.markdown("---")
    st.subheader("📄 Detailed Profile Analysis")
    if profile_data.get('full_text'):
        with st.expander("View Full Profile Analysis"):
            st.write(profile_data.get('full_text'))
    else:
        st.info("No detailed analysis available")
    
    # Navigation section at bottom
    st.markdown("---")
    st.subheader("🔗 Related Information")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🎯 View Strategy", use_container_width=True):
            st.session_state["current_page"] = "strategy_view"
            st.rerun()
    
    with col2:
        if st.button("📧 View Intro Mail", use_container_width=True):
            st.session_state["current_page"] = "intro_mail_view"
            st.rerun()
    
    with col3:
        if st.button("📋 View Campaign Plan", use_container_width=True):
            st.session_state["current_page"] = "campaign_plan"
            st.rerun()
    
    # Debug section
    with st.expander("🔍 Debug - Raw Profile Data"):
        st.json(profile_data)

def main():
    """Main function to run the profile view page"""
    st.set_page_config(
        page_title="Profile View - Lead Nurturing",
        page_icon="👤",
        layout="wide"
    )
    
    profile_view_page()

if __name__ == "__main__":
    main()