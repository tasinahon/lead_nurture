"""
Strategy View Page
Displays client strategy details
"""

import streamlit as st
import sys
import os

# Add the frontend directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.api_client import api_client, safe_api_call

def strategy_view_page():
    """Render the strategy view page"""
    
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
    
    # Page header
    st.title(f"🎯 Strategy - {client_name}")
    
    # Back to Client Details button at the top
    if st.button("⬅️ Back to Client Details", key="strategy_back_top"):
        st.session_state["current_page"] = "client_details"
        st.rerun()
    
    st.markdown("---")
    
    # Load strategy details
    with st.spinner("Loading strategy details..."):
        strategy_data = safe_api_call(api_client.get_client_strategy, client_id)
    
    if not strategy_data:
        st.warning("No strategy found for this client.")
        st.info("The strategy may not have been created yet. Please ensure the client has gone through the initial strategy generation process.")
        
        if st.button("⬅️ Back to Client Details", key="strategy_back_error"):
            st.session_state["current_page"] = "client_details"
            st.rerun()
        return
    
    # Main strategy content
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Strategy Details
        st.subheader("📋 Initial Strategy Details")
        
        # Engagement Channel
        if strategy_data.get("engagement_channel"):
            st.markdown("**🎯 Engagement Channel:**")
            st.write(strategy_data.get("engagement_channel"))
        
        # Tone & Style
        if strategy_data.get("tone_style"):
            st.markdown("**🎨 Tone & Style:**")
            st.write(strategy_data.get("tone_style"))
        
        # Communication Frequency
        if strategy_data.get("communication_frequency"):
            st.markdown("**� Communication Frequency:**")
            st.write(strategy_data.get("communication_frequency"))
        
        # General Advice
        if strategy_data.get("general_advice"):
            st.subheader("� General Advice")
            st.write(strategy_data.get("general_advice"))
    
    with col2:
        # Strategy metadata
        st.subheader("📊 Strategy Info")
        
        # Strategy ID
        if strategy_data.get("strategy_id"):
            st.write(f"**ID:** {strategy_data.get('strategy_id')}")
        
        # Client ID
        if strategy_data.get("client_id"):
            st.write(f"**Client ID:** {strategy_data.get('client_id')}")
        
        # Generated timestamp
        if strategy_data.get("generated_at"):
            try:
                from datetime import datetime
                generated_date = datetime.fromisoformat(strategy_data.get("generated_at").replace("Z", "+00:00"))
                st.write(f"**Generated:** {generated_date.strftime('%Y-%m-%d %H:%M')}")
            except:
                st.write(f"**Generated:** {strategy_data.get('generated_at')}")
        
        # Client context
        st.subheader("👤 Client Context")
        st.write(f"**Name:** {selected_client.get('full_name', 'N/A')}")
        st.write(f"**Company:** {selected_client.get('company', 'N/A')}")
        st.write(f"**Category:** {selected_client.get('category', 'N/A')}")
    
    # Strategy Summary
    st.markdown("---")
    st.subheader("📋 Strategy Summary")
    
    summary_col1, summary_col2 = st.columns(2)
    
    with summary_col1:
        st.markdown("**📞 Preferred Channel:**")
        st.info(strategy_data.get("engagement_channel", "Not specified"))
        
        st.markdown("**� Communication Style:**")
        st.info(strategy_data.get("tone_style", "Not specified"))
    
    with summary_col2:
        st.markdown("**⏰ Contact Frequency:**")
        st.info(strategy_data.get("communication_frequency", "Not specified"))
        
        # Calculate strategy age
        if strategy_data.get("generated_at"):
            try:
                from datetime import datetime
                created_date = datetime.fromisoformat(strategy_data.get("generated_at").replace("Z", "+00:00"))
                days_active = (datetime.now().replace(tzinfo=created_date.tzinfo) - created_date).days
                st.markdown("**📅 Strategy Age:**")
                st.info(f"{days_active} days old")
            except:
                st.markdown("**📅 Strategy Age:**")
                st.info("Unknown")
    
    # Strategy Performance Metrics
    st.markdown("---")
    st.subheader("📊 Strategy Metrics")
    
    performance_col1, performance_col2, performance_col3 = st.columns(3)
    
    with performance_col1:
        st.metric("Strategy ID", strategy_data.get("strategy_id", "N/A"))
    
    with performance_col2:
        st.metric("Client ID", strategy_data.get("client_id", "N/A"))
    
    with performance_col3:
        # Status (derived)
        status = "Active" if strategy_data.get("strategy_id") else "Unknown"
        st.metric("Status", status)
    
    # Actions section
    st.markdown("---")
    st.subheader("🎯 Actions")
    
    action_col1, action_col2, action_col3 = st.columns(3)
    
    with action_col1:
        if st.button("✏️ Edit Strategy", use_container_width=True):
            st.info("Edit strategy feature - Coming Soon!")
            st.markdown("This will allow you to modify the strategy details.")
    
    with action_col2:
        if st.button("📋 View Campaign Plan", use_container_width=True):
            st.session_state["current_page"] = "campaign_plan"
            st.rerun()
    
    with action_col3:
        if st.button("📊 Strategy Analytics", use_container_width=True):
            st.info("Strategy analytics feature - Coming Soon!")
            st.markdown("This will show detailed performance metrics for this strategy.")
    
    # Navigation buttons
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("⬅️ Back to Client Details", key="strategy_back_bottom"):
            st.session_state["current_page"] = "client_details"
            st.rerun()
    
    with col2:
        if st.button("👤 View Profile"):
            st.session_state["current_page"] = "profile_view"
            st.rerun()
    
    with col3:
        if st.button("📧 View Intro Mail"):
            st.session_state["current_page"] = "intro_mail_view"
            st.rerun()
    
    with col4:
        if st.button("📋 View Campaign Plan"):
            st.session_state["current_page"] = "campaign_plan"
            st.rerun()
    
    # Debug section
    with st.expander("🔍 Debug - Raw Strategy Data"):
        st.json(strategy_data)

def main():
    """Main function to run the strategy view page"""
    st.set_page_config(
        page_title="Strategy View - Lead Nurturing",
        page_icon="🎯",
        layout="wide"
    )
    
    strategy_view_page()

if __name__ == "__main__":
    main()