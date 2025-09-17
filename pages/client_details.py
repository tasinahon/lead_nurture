"""
Client Details Page
Shows detailed client information with options for Profile, Intro Mail, Strategy, Campaign Plan
"""

import streamlit as st
import sys
import os

# Add the frontend directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.api_client import api_client, safe_api_call

def client_details_page():
    """Render the client details page"""
    
    # Check if client is selected
    selected_client = st.session_state.get("selected_client")
    if not selected_client:
        st.error("No client selected. Please select a client from the client list.")
        if st.button("Go to Client List"):
            st.session_state["current_page"] = "client_list"
            st.rerun()
        return
    
    client_id = selected_client["client_id"]
    
    # Page header
    st.title(f"👤 {selected_client.get('full_name', 'Client Details')}")
    
    # Top navigation buttons
    top_col1, top_col2, top_col3, top_col4 = st.columns([2, 2, 2, 6])
    
    with top_col1:
        if st.button("⬅️ Back to Dashboard", use_container_width=True):
            st.session_state["current_page"] = "dashboard"
            st.rerun()
    
    with top_col2:
        if st.button("✏️ Edit Client", use_container_width=True):
            st.info("Edit client feature - Coming Soon!")
    
    with top_col3:
        if st.button("🗑️ Delete Client", use_container_width=True):
            st.error("Delete client feature - Coming Soon!")
    
    st.markdown("---")
    
    # Main client info section
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Basic Information
        st.subheader("📋 Basic Information")
        
        info_col1, info_col2 = st.columns(2)
        
        with info_col1:
            st.write(f"**Full Name:** {selected_client.get('full_name', 'N/A')}")
            st.write(f"**Email:** {selected_client.get('email', 'N/A')}")
            st.write(f"**Phone:** {selected_client.get('phone', 'N/A')}")
            st.write(f"**Category:** {selected_client.get('category', 'N/A')}")
        
        with info_col2:
            st.write(f"**Company:** {selected_client.get('company', 'N/A')}")
            st.write(f"**Website:** {selected_client.get('company_website', 'N/A')}")
            st.write(f"**WhatsApp:** {selected_client.get('whatsapp', 'N/A')}")
            st.write(f"**Created:** {selected_client.get('created_at', 'N/A')[:10] if selected_client.get('created_at') else 'N/A'}")
        
        # Social Media Links
        if any([selected_client.get('linkedin_url'), selected_client.get('facebook'), selected_client.get('instagram')]):
            st.subheader("🌐 Social Media")
            social_col1, social_col2, social_col3 = st.columns(3)
            
            with social_col1:
                if selected_client.get('linkedin_url'):
                    st.markdown(f"[LinkedIn Profile]({selected_client.get('linkedin_url')})")
            
            with social_col2:
                if selected_client.get('facebook'):
                    st.markdown(f"[Facebook Profile]({selected_client.get('facebook')})")
            
            with social_col3:
                if selected_client.get('instagram'):
                    st.markdown(f"[Instagram Profile]({selected_client.get('instagram')})")
    
    with col2:
        # Action buttons panel
        st.subheader("🎯 Actions")
        
        # View Profile button
        if st.button("👤 View Profile", use_container_width=True, type="primary"):
            st.session_state["current_page"] = "profile_view"
            st.rerun()
        
        # Intro Mail button
        if st.button("📧 Intro Mail", use_container_width=True):
            st.session_state["current_page"] = "intro_mail_view"
            st.rerun()
        
        # Strategy button
        if st.button("🎯 Strategy", use_container_width=True):
            st.session_state["current_page"] = "strategy_view"
            st.rerun()
        
        # Campaign Plan button
        if st.button("📋 Campaign Plan", use_container_width=True):
            st.session_state["current_page"] = "campaign_plan"
            st.rerun()
    
    # Quick Stats Section  
    st.markdown("---")
    st.subheader("� Quick Stats")
    
    # Show basic client stats without timeline dependency
    summary = {}
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Activities", summary.get("total_activities", 0))
    
    with col2:
        intro_sent = "✅" if summary.get("intro_email_sent", False) else "❌"
        st.metric("Intro Email Sent", intro_sent)
    
    with col3:
        replied = "✅" if summary.get("replied_to_intro", False) else "❌"
        st.metric("Replied to Intro", replied)
    
    with col4:
        st.metric("Follow-ups Sent", summary.get("follow_ups_sent", 0))
    


def main():
    """Main function to run the client details page"""
    st.set_page_config(
        page_title="Client Details - Lead Nurturing",
        page_icon="👤",
        layout="wide"
    )
    
    client_details_page()

if __name__ == "__main__":
    main()