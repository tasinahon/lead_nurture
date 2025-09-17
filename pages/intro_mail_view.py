"""
Intro Mail View Page
Displays introductory email details for a client
"""

import streamlit as st
import sys
import os

# Add the frontend directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.api_client import api_client, safe_api_call

def intro_mail_view_page():
    """Render the intro mail view page"""
    
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
    st.title(f"📧 Introductory Email - {client_name}")
    
    # Back to Client List button at the top
    if st.button("⬅️ Back to Client List", key="intro_mail_back_top"):
        st.session_state["current_page"] = "client_details"
        st.rerun()
    
    st.markdown("---")
    
    # Load intro email details
    with st.spinner("Loading introductory email details..."):
        intro_email = safe_api_call(api_client.get_client_intro_email, client_id)
    
    if not intro_email:
        st.error("⚠️ Unable to load introductory email details")
        st.info("This could be due to:")
        st.markdown("""
        - The introductory email hasn't been sent yet for this client
        - There's a database issue with the email draft record
        - The email draft data is corrupted or missing
        """)
        
        st.markdown("### 🔧 Suggested Actions:")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📧 Send New Intro Email", key="send_new_intro"):
                st.info("This would trigger sending a new introductory email for this client")
                # TODO: Implement new intro email sending
        
        with col2:
            if st.button("🔄 Try Again", key="retry_intro_load"):
                st.rerun()
        
        # Show mock data for development/debugging
        st.markdown("---")
        st.subheader("📊 Expected Data Structure")
        st.info("When the API works correctly, this page will show:")
        st.markdown("""
        - **Email Status:** Sent/Reply status with timestamps
        - **Email Content:** Subject and body of the introductory email  
        - **Follow-up Status:** Any automated follow-up campaigns
        - **Client Context:** Client and sender information
        - **Analytics:** Reply tracking and engagement metrics
        """)
        
        if st.button("⬅️ Back to Client List"):
            st.session_state["current_page"] = "client_list"
            st.rerun()
        return
    
    # Email overview
    intro_data = intro_email.get("intro_email", {})
    client_data = intro_email.get("client", {})
    user_data = intro_email.get("user", {})
    email_draft = intro_email.get("email_draft", {})
    follow_ups = intro_email.get("follow_up_campaigns", [])
    
    # Email status section
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📊 Email Status")
        
        status_col1, status_col2 = st.columns(2)
        
        with status_col1:
            # Reply status
            replied = intro_data.get("replied", False)
            reply_status = "✅ Replied" if replied else "❌ No Reply"
            st.markdown(f"**Reply Status:** {reply_status}")
            
            # Sent status
            sent_at = intro_data.get("sent_at")
            if sent_at:
                st.markdown(f"**Sent At:** {sent_at[:16].replace('T', ' ')}")
            else:
                st.markdown("**Status:** Not sent yet")
        
        with status_col2:
            # Reply checking info
            reply_checks = intro_data.get("reply_check_count", 0)
            st.markdown(f"**Reply Checks:** {reply_checks}")
            
            last_check = intro_data.get("last_reply_check")
            if last_check:
                st.markdown(f"**Last Check:** {last_check[:16].replace('T', ' ')}")
            
            # No-reply workflow status
            workflow_triggered = intro_data.get("no_reply_workflow_triggered", False)
            workflow_status = "✅ Activated" if workflow_triggered else "❌ Not Activated"
            st.markdown(f"**Follow-up Workflow:** {workflow_status}")
    
    with col2:
        st.subheader("⚙️ Email Settings")
        st.write(f"**Time Zone:** {intro_data.get('timezone', 'N/A')}")
        st.write(f"**Language:** {intro_data.get('preferred_language', 'N/A')}")
        st.write(f"**Method:** {intro_data.get('communication_method', 'N/A')}")
    
    # Email content section
    st.markdown("---")
    st.subheader("✉️ Email Content")
    
    if email_draft:
        # Display subject
        subject = email_draft.get("subject", "No Subject")
        st.markdown(f"**Subject:** {subject}")
        
        # Display email body
        st.markdown("**Email Body:**")
        body = email_draft.get("body_markdown", "No content available")
        
        # Create a nice display for the email content
        with st.container():
            st.markdown("---")
            st.markdown(f"**To:** {client_data.get('email', 'N/A')}")
            st.markdown(f"**From:** {user_data.get('email', 'N/A')}")
            st.markdown(f"**Subject:** {subject}")
            st.markdown("---")
            
            # Display the email body in a text area for better formatting
            st.text_area(
                "Email Content:", 
                value=body, 
                height=400,
                disabled=True,
                key="email_body_display"
            )
            st.markdown("---")
    
    else:
        st.warning("Email content not available or not generated yet.")
    
    # Follow-up campaigns section
    if follow_ups:
        st.markdown("---")
        st.subheader("📬 Follow-up Campaigns")
        
        st.info(f"This client has {len(follow_ups)} follow-up email(s) in the pipeline due to no reply.")
        
        for i, follow_up in enumerate(follow_ups, 1):
            with st.container():
                st.markdown(f"**Follow-up {i}:**")
                
                follow_col1, follow_col2 = st.columns(2)
                
                with follow_col1:
                    st.write(f"**Subject:** {follow_up.get('subject', 'N/A')}")
                    st.write(f"**Status:** {follow_up.get('status', 'N/A')}")
                
                with follow_col2:
                    scheduled_at = follow_up.get('scheduled_at')
                    if scheduled_at:
                        st.write(f"**Scheduled:** {scheduled_at[:16].replace('T', ' ')}")
                    
                    sent_at = follow_up.get('sent_at')
                    if sent_at:
                        st.write(f"**Sent:** {sent_at[:16].replace('T', ' ')}")
                
                st.markdown("---")
    
    # Client context section
    st.markdown("---")
    st.subheader("👤 Client Context")
    
    context_col1, context_col2 = st.columns(2)
    
    with context_col1:
        st.markdown("**Client Information:**")
        st.write(f"**Name:** {client_data.get('full_name', 'N/A')}")
        st.write(f"**Email:** {client_data.get('email', 'N/A')}")
        st.write(f"**Company:** {client_data.get('company', 'N/A')}")
    
    with context_col2:
        st.markdown("**Sent By:**")
        st.write(f"**Name:** {user_data.get('name', 'N/A')}")
        st.write(f"**Email:** {user_data.get('email', 'N/A')}")
    
    # Analytics section
    if intro_data.get("sent_at"):
        st.markdown("---")
        st.subheader("📈 Email Analytics")
        
        analytics_col1, analytics_col2, analytics_col3 = st.columns(3)
        
        with analytics_col1:
            st.metric("Reply Status", "Replied" if intro_data.get("replied") else "Pending")
        
        with analytics_col2:
            st.metric("Reply Checks", intro_data.get("reply_check_count", 0))
        
        with analytics_col3:
            workflow_status = "Active" if intro_data.get("no_reply_workflow_triggered") else "Inactive"
            st.metric("Follow-up Workflow", workflow_status)
    
    # Actions section
    st.markdown("---")
    st.subheader("🎯 Actions")
    
    action_col1, action_col2, action_col3 = st.columns(3)
    
    with action_col1:
        if st.button("🔄 Check for Replies", use_container_width=True):
            st.info("Manual reply checking feature - Coming Soon!")
            st.markdown("This will manually trigger a reply check for this email.")
    
    with action_col2:
        if st.button("📧 Resend Email", use_container_width=True):
            st.info("Email resend feature - Coming Soon!")
            st.markdown("This will allow you to resend the introductory email.")
    
    with action_col3:
        if st.button("📬 View Follow-ups", use_container_width=True):
            st.session_state["current_page"] = "follow_up_dashboard"
            st.rerun()
    
    # Navigation buttons
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("⬅️ Back to Client List", key="intro_mail_back_bottom"):
            st.session_state["current_page"] = "client_details"
            st.rerun()
    
    with col2:
        if st.button("👤 View Profile"):
            st.session_state["current_page"] = "profile_view"
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
    with st.expander("🔍 Debug - Raw Email Data"):
        st.json(intro_email)

def main():
    """Main function to run the intro mail view page"""
    st.set_page_config(
        page_title="Intro Mail - Lead Nurturing",
        page_icon="📧",
        layout="wide"
    )
    
    intro_mail_view_page()

if __name__ == "__main__":
    main()