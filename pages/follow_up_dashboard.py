"""
Follow-up Mail Dashboard
Shows all scheduled follow-up emails with client info and campaign details
"""

import streamlit as st
import sys
import os

# Add the frontend directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.api_client import api_client, safe_api_call

def follow_up_dashboard_page():
    """Render the follow-up mail dashboard page"""
    st.title("📬 Follow-up Mail Dashboard")
    st.markdown("---")
    
    # Check if user is logged in
    current_user = st.session_state.get("current_user")
    if not current_user:
        st.error("Please log in first to view follow-up emails.")
        return
    
    # Filter controls
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        search_term = st.text_input("🔍 Search by client name or email...", placeholder="Enter client name or email")
    
    with col2:
        status_filter = st.selectbox("Filter by Status", ["All", "scheduled", "sent", "not_generated", "generated"])
    
    with col3:
        show_only_scheduled = st.checkbox("Show only scheduled emails", value=True)
    
    # Get campaign executions (follow-up emails)
    with st.spinner("Loading follow-up emails..."):
        executions = safe_api_call(api_client.get_campaign_executions)
    
    if not executions:
        st.info("No follow-up emails found.")
        st.markdown("""
        Follow-up emails are automatically created when:
        - A client doesn't reply to the introductory email
        - The no-reply workflow is triggered
        - Campaign sequences are activated
        """)
        return
    
    # Filter executions
    filtered_executions = executions
    
    # Filter by status
    if status_filter != "All":
        filtered_executions = [ex for ex in filtered_executions if ex.get("status") == status_filter]
    
    # Filter to show only scheduled emails if checkbox is checked
    if show_only_scheduled:
        filtered_executions = [ex for ex in filtered_executions 
                             if ex.get("scheduled_at") and not ex.get("sent_at")]
    
    # Filter by search term
    if search_term:
        search_lower = search_term.lower()
        filtered_executions = [
            ex for ex in filtered_executions
            if (search_lower in ex.get("client_name", "").lower() or
                search_lower in ex.get("client_email", "").lower())
        ]
    
    # Display summary
    st.markdown(f"**Showing {len(filtered_executions)} of {len(executions)} follow-up emails**")
    
    if not filtered_executions:
        st.warning("No follow-up emails match your filters.")
        return
    
    # Display follow-up emails
    st.markdown("---")
    
    for i, execution in enumerate(filtered_executions):
        with st.container():
            # Email card
            col1, col2, col3 = st.columns([3, 2, 1])
            
            with col1:
                # Client information
                st.markdown(f"**👤 {execution.get('client_name', 'Unknown Client')}**")
                st.write(f"📧 {execution.get('client_email', 'N/A')}")
                
                if execution.get('client_company'):
                    st.write(f"🏢 {execution.get('client_company')}")
                
                # Email subject and campaign
                st.markdown(f"**📋 Campaign:** {execution.get('campaign_name', 'N/A')}")
                st.markdown(f"**✉️ Subject:** {execution.get('subject', 'No Subject')}")
            
            with col2:
                # Status and timing
                status = execution.get('status', 'Unknown')
                status_color = {
                    'scheduled': '🟡',
                    'sent': '✅',
                    'not_generated': '⚪',
                    'generated': '🔵'
                }.get(status, '⚫')
                
                st.write(f"**Status:** {status_color} {status.title()}")
                
                # Timing information
                if execution.get('scheduled_at'):
                    st.write(f"**⏰ Scheduled:** {execution.get('scheduled_at')[:16].replace('T', ' ')}")
                
                if execution.get('sent_at'):
                    st.write(f"**📤 Sent:** {execution.get('sent_at')[:16].replace('T', ' ')}")
                
                if execution.get('day'):
                    st.write(f"**📅 Campaign Day:** {execution.get('day')}")
            
            with col3:
                # Action buttons
                if st.button("👁️ View", key=f"view_exec_{execution.get('execution_id')}"):
                    # Show detailed view in expander
                    st.session_state[f"show_details_{execution.get('execution_id')}"] = True
                    st.rerun()
                
                if execution.get('client_id'):
                    if st.button("👤 Client", key=f"client_exec_{execution.get('execution_id')}"):
                        # Navigate to client details
                        st.session_state["selected_client"] = {"client_id": execution.get('client_id')}
                        st.session_state["current_page"] = "client_details"
                        st.rerun()
            
            # Expandable email content section
            if st.session_state.get(f"show_details_{execution.get('execution_id')}", False):
                with st.expander("📝 Email Content", expanded=True):
                    # Email subject
                    st.markdown(f"**Subject:** {execution.get('subject', 'No Subject')}")
                    
                    # Email content
                    content = execution.get('personalized_content', 'No content available')
                    if content and content != 'No content available':
                        st.markdown("**Content:**")
                        st.text_area("", value=content, height=200, disabled=True, key=f"content_{execution.get('execution_id')}")
                    else:
                        st.info("Email content not yet generated or not available")
                    
                    # Additional details
                    st.markdown("**Campaign Details:**")
                    details_col1, details_col2 = st.columns(2)
                    
                    with details_col1:
                        st.write(f"Execution ID: {execution.get('execution_id')}")
                        st.write(f"Campaign ID: {execution.get('campaign_id')}")
                    
                    with details_col2:
                        st.write(f"Client ID: {execution.get('client_id')}")
                        st.write(f"Created: {execution.get('created_at', 'N/A')[:10] if execution.get('created_at') else 'N/A'}")
                    
                    # Close button
                    if st.button("Close Details", key=f"close_{execution.get('execution_id')}"):
                        st.session_state[f"show_details_{execution.get('execution_id')}"] = False
                        st.rerun()
            
            st.markdown("---")
    
    # Statistics section
    st.markdown("### 📊 Follow-up Statistics")
    
    # Calculate statistics
    total_scheduled = len([ex for ex in executions if ex.get("scheduled_at") and not ex.get("sent_at")])
    total_sent = len([ex for ex in executions if ex.get("sent_at")])
    total_pending = len([ex for ex in executions if ex.get("status") == "not_generated"])
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Follow-ups", len(executions))
    
    with col2:
        st.metric("Scheduled", total_scheduled)
    
    with col3:
        st.metric("Sent", total_sent)
    
    with col4:
        st.metric("Pending Generation", total_pending)
    
    # Export functionality
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📊 Export to CSV"):
            # Create CSV data manually
            import csv
            import io
            
            output = io.StringIO()
            if filtered_executions:
                writer = csv.DictWriter(output, fieldnames=filtered_executions[0].keys())
                writer.writeheader()
                writer.writerows(filtered_executions)
                csv_data = output.getvalue()
                
                st.download_button(
                    label="Download CSV",
                    data=csv_data,
                    file_name="follow_up_emails.csv",
                    mime="text/csv"
                )
            else:
                st.warning("No data to export")
    
    with col2:
        if st.button("🔄 Refresh Data"):
            st.rerun()

def main():
    """Main function to run the follow-up dashboard page"""
    st.set_page_config(
        page_title="Follow-up Dashboard - Lead Nurturing",
        page_icon="📬",
        layout="wide"
    )
    
    follow_up_dashboard_page()

if __name__ == "__main__":
    main()