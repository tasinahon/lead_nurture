"""
Profile View Page
Displays client    
    # Load profile details from the API
    with st.spinner("Loading profile details..."):
        profile_response = safe_api_call(api_client.get_client_profile, client_id)
    
    if not profile_response:
        st.warning("No profile found for this client.")
        st.info("The client profile may not have been created yet. Please ensure the client has gone through the profile building process.")
        return
    
    # The API returns a list, so get the first profile
    profiles = profile_response if isinstance(profile_response, list) else [profile_response]
    
    if not profiles:
        st.warning("No profile data available for this client.")
        return
    
    # Use the first profile
    profile_data = profiles[0]including summary, interests, and communication preferences
"""

import streamlit as st
import sys
import os
from datetime import datetime

# Add the frontend directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.api_client import api_client, safe_api_call

def profile_view_page():
    """Render the profile view page"""
    
    # Back to Client Details button at the top
    if st.button("⬅️ Back to Client Details", key="profile_back_top"):
        st.session_state["current_page"] = "client_details"
        st.rerun()
    
    st.markdown("---")
    
    # Check if client is selected
    selected_client = st.session_state.get("selected_client")
    if not selected_client:
        st.error("No client selected. Please select a client first.")
        if st.button("Go to Dashboard"):
            st.session_state["current_page"] = "dashboard"
            st.rerun()
        return
    
    client_id = selected_client["client_id"]
    client_name = selected_client.get("full_name", "Client")
    
    # Page header
    st.title(f"👤 Profile - {client_name}")
    st.markdown("---")
    
    # Load client profile and client details
    with st.spinner("Loading client profile..."):
        profile_response = safe_api_call(api_client.get_client_profile, client_id)
    
    if not profile_response or not profile_response.get('profiles'):
        st.warning("No detailed profile found for this client.")
        st.info("Profile information will be available after the initial scraping and analysis process.")
        
        # Show basic client information from session state
        st.subheader("� Basic Client Information")
        st.write(f"**Full Name:** {selected_client.get('full_name', 'N/A')}")
        st.write(f"**Email:** {selected_client.get('email', 'N/A')}")
        st.write(f"**Company:** {selected_client.get('company', 'N/A')}")
        st.write(f"**Status:** {selected_client.get('status', 'N/A')}")
        
        return
    
    # Extract the first profile from the profiles array
    profile_data = profile_response['profiles'][0] if profile_response['profiles'] else {}
    
    # Profile sections - Display actual profile data
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Client Basic Info (from session state)
        st.subheader("👤 Client Information")
        
        info_col1, info_col2 = st.columns(2)
        
        with info_col1:
            st.write(f"**Full Name:** {selected_client.get('full_name', 'N/A')}")
            st.write(f"**Email:** {selected_client.get('email', 'N/A')}")
            st.write(f"**Company:** {selected_client.get('company', 'N/A')}")
        
        with info_col2:
            st.write(f"**Status:** {selected_client.get('status', 'N/A')}")
            st.write(f"**Language:** {profile_data.get('preferred_language', 'N/A')}")
            st.write(f"**Contact Method:** {profile_data.get('preferred_contact', 'N/A')}")
        
        # Profile Summary
        if profile_data.get('summary'):
            st.subheader("� Profile Summary")
            st.write(profile_data.get('summary'))
        
        # Interests
        if profile_data.get('interests'):
            st.subheader("🎯 Interests & Expertise")
            interests = profile_data.get('interests', '').split(',')
            
            # Display interests as tags
            st.write("**Key Interests:**")
            cols = st.columns(3)
            for i, interest in enumerate(interests):
                if interest.strip():
                    with cols[i % 3]:
                        st.markdown(f"`{interest.strip()}`")
        
        # Full Profile Text
        if profile_data.get('full_text'):
            st.subheader("📄 Detailed Profile")
            with st.expander("View Full Profile Analysis"):
                st.write(profile_data.get('full_text'))
        
        # Engagement Times
        if profile_data.get('engagement_times'):
            st.subheader("⏰ Best Engagement Times")
            st.write(profile_data.get('engagement_times'))
    
    with col2:
        # Communication Preferences
        st.subheader("📞 Communication Preferences")
        
        st.write(f"**Preferred Contact:** {profile_data.get('preferred_contact', 'Email')}")
        st.write(f"**Language:** {profile_data.get('preferred_language', 'English')}")
        
        if profile_data.get('engagement_times'):
            st.write(f"**Best Times:** {profile_data.get('engagement_times')}")
        
        # Profile Statistics
        st.subheader("📊 Profile Statistics")
        
        # Calculate profile richness
        profile_fields = ['summary', 'interests', 'preferred_language', 'preferred_contact', 'engagement_times', 'full_text']
        filled_fields = sum(1 for field in profile_fields if profile_data.get(field))
        completeness_score = (filled_fields / len(profile_fields)) * 100
        
        st.progress(completeness_score / 100)
        st.write(f"**{completeness_score:.1f}% Complete**")
        
        # Profile insights
        if profile_data.get('interests'):
            interests_count = len([i.strip() for i in profile_data.get('interests', '').split(',') if i.strip()])
            st.write(f"**Interest Areas:** {interests_count}")
        
        if profile_data.get('summary'):
            summary_words = len(profile_data.get('summary', '').split())
            st.write(f"**Summary Length:** {summary_words} words")
        
        # Profile actions
        st.subheader("🔧 Profile Actions")
        
        if st.button("🔄 Refresh Profile"):
            st.rerun()
        
        if st.button("📝 Update Profile"):
            st.info("Profile update feature coming soon!")
        
        if completeness_score < 80:
            st.info("💡 Consider running additional profile analysis to improve personalization")
    
    # Profile Metadata
    st.markdown("---")
    st.subheader("📈 Profile Metadata")
    
    activity_col1, activity_col2 = st.columns(2)
    
    with activity_col1:
        st.write(f"**Client ID:** {profile_data.get('client_id', selected_client.get('client_id', 'N/A'))}")
        st.write(f"**Client Created:** {selected_client.get('created_at', 'N/A')[:10] if selected_client.get('created_at') else 'N/A'}")
    
    with activity_col2:
        st.write(f"**Profile Status:** {'Available' if profile_data else 'Not Generated'}")
        st.write(f"**Last Viewed:** {datetime.now().strftime('%Y-%m-%d %H:%M') if profile_data else 'N/A'}")
    
    # Additional Notes Section
    st.markdown("---")
    st.subheader("📝 Additional Information")
    
    if not profile_data.get('engagement_times'):
        st.info("💡 Engagement timing analysis will be available after more interaction data is collected.")
    
    if selected_client.get('status') == 'pending':
        st.warning("⏳ This client is still being processed. Complete profile information will be available soon.")
    
    # Navigation buttons
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("⬅️ Back to Client Details", key="profile_back_bottom"):
            st.session_state["current_page"] = "client_details"
            st.rerun()
    
    with col2:
        if st.button("📧 View Intro Mail"):
            st.session_state["current_page"] = "intro_mail_view"
            st.rerun()
    
    with col3:
        if st.button("🎯 View Strategy"):
            st.session_state["current_page"] = "strategy_view"
            st.rerun()
    
    with col4:
        if st.button("📋 View Campaign Plan"):
            st.session_state["current_page"] = "campaign_plan"
            st.rerun()
    
    # Debug section
    with st.expander("🔍 Debug - Raw Profile Data"):
        if profile_data:
            st.json(profile_data)
        else:
            st.write("No profile data available")

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