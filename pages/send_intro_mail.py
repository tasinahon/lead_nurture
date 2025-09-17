"""
Send Intro Mail Page
Shows all clients with option to send introductory emails
"""

import streamlit as st
import sys
import os

# Add the frontend directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.api_client import api_client, safe_api_call

def send_intro_mail_page(show_header=True):
    """Render the send intro mail page"""
    
    # Check if user is logged in
    current_user = st.session_state.get("current_user")
    if not current_user:
        st.error("Please login first.")
        if show_header:  # Only redirect if not in tab mode
            st.session_state["current_page"] = "user_login"
            st.rerun()
        return
    
    user_id = current_user.get("user_id")
    user_name = current_user.get("name", "User")
    
    # Page header (only show if not in tab mode)
    if show_header:
        st.title("📧 Send Introductory Emails")
        st.markdown(f"**Logged in as:** {user_name}")
        
        # Back to Dashboard button at top
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("⬅️ Back to Dashboard", use_container_width=True):
                st.session_state["current_page"] = "dashboard"
                st.rerun()
        
        st.markdown("---")
    else:
        # For tab mode, just show a simple header
        st.markdown(f"**Logged in as:** {user_name}")
        st.markdown("---")
    
    # Load all clients for the current user
    with st.spinner("Loading your clients..."):
        clients = safe_api_call(api_client.get_clients, user_id)
    
    if not clients:
        st.warning("No clients found.")
        st.info("Create some clients first before sending introductory emails.")
        
        if show_header:
            # In standalone page mode, redirect to client creation
            if st.button("➕ Create New Client"):
                st.session_state["current_page"] = "client_creation"
                st.rerun()
        else:
            # In tab mode, suggest using the Create Client tab
            st.info("💡 **Tip:** Use the 'Create Client' tab above to add new clients, then return to this tab to send emails.")
        return
    
    st.subheader(f"📋 Your Clients ({len(clients)} total)")
    st.markdown("Click 'Send Email' to send an introductory email to any client.")
    
    # Display clients in rows
    for i, client in enumerate(clients):
        with st.container():
            # Create columns for client info and send button
            col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 1])
            
            with col1:
                st.markdown(f"**{client.get('full_name', 'N/A')}**")
                st.caption(f"ID: {client.get('client_id', 'N/A')}")
            
            with col2:
                st.write(f"📧 {client.get('email', 'N/A')}")
            
            with col3:
                st.write(f"🏢 {client.get('company', 'N/A') if client.get('company') else 'No Company'}")
            
            with col4:
                category = client.get('category', 'N/A')
                if category and category != 'N/A':
                    st.write(f"🏷️ {category}")
                else:
                    st.write("🏷️ Uncategorized")
            
            with col5:
                # Send Email button
                button_key = f"send_email_{client.get('client_id', i)}"
                if st.button("📧 Send Email", key=button_key, use_container_width=True, type="primary"):
                    client_id = client.get('client_id')
                    client_name = client.get('full_name', 'Client')
                    
                    if client_id:
                        # Show confirmation
                        with st.spinner(f"Sending introductory email to {client_name}..."):
                            response = safe_api_call(
                                api_client.send_intro_email, 
                                client_id=client_id, 
                                user_id=user_id
                            )
                        
                        if response:
                            st.success(f"✅ Introductory email sent to {client_name}!")
                            
                            # Show response details
                            if response.get("status"):
                                st.info(f"Status: {response.get('status')}")
                            
                            if response.get("draft_id"):
                                st.info(f"Email Draft ID: {response.get('draft_id')}")
                            
                            # Show additional info if available
                            with st.expander("📧 Email Details"):
                                st.json(response)
                        else:
                            st.error(f"❌ Failed to send email to {client_name}")
                    else:
                        st.error("Invalid client ID")
            
            st.markdown("---")
    
    # Summary statistics
    st.markdown("### 📊 Summary")
    
    stats_col1, stats_col2, stats_col3 = st.columns(3)
    
    with stats_col1:
        st.metric("Total Clients", len(clients))
    
    with stats_col2:
        clients_with_email = len([c for c in clients if c.get('email')])
        st.metric("Clients with Email", clients_with_email)
    
    with stats_col3:
        clients_with_company = len([c for c in clients if c.get('company')])
        st.metric("Clients with Company", clients_with_company)
    
    # Bulk actions section
    st.markdown("---")
    st.subheader("🚀 Bulk Actions")
    
    bulk_col1, bulk_col2 = st.columns(2)
    
    with bulk_col1:
        st.markdown("**Send emails to all clients at once:**")
        if st.button("📧 Send to All Clients", type="secondary", use_container_width=True):
            # Confirmation
            st.warning("⚠️ This will send introductory emails to ALL your clients. This action cannot be undone.")
            
            if st.checkbox("I understand and want to proceed"):
                if st.button("✅ Confirm - Send to All", type="primary"):
                    success_count = 0
                    error_count = 0
                    
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    for i, client in enumerate(clients):
                        client_id = client.get('client_id')
                        client_name = client.get('full_name', f'Client {client_id}')
                        
                        status_text.text(f"Sending to {client_name}...")
                        progress_bar.progress((i + 1) / len(clients))
                        
                        if client_id:
                            response = safe_api_call(
                                api_client.send_intro_email, 
                                client_id=client_id, 
                                user_id=user_id
                            )
                            
                            if response:
                                success_count += 1
                            else:
                                error_count += 1
                    
                    status_text.text("Bulk sending completed!")
                    st.success(f"✅ Successfully sent {success_count} emails")
                    
                    if error_count > 0:
                        st.warning(f"⚠️ {error_count} emails failed to send")
    
    with bulk_col2:
        st.markdown("**Filter and send:**")
        
        # Category filter
        categories = list(set([c.get('category', 'Uncategorized') for c in clients if c.get('category')]))
        if categories:
            selected_category = st.selectbox("Filter by Category:", ["All"] + categories)
            
            if selected_category != "All":
                filtered_clients = [c for c in clients if c.get('category') == selected_category]
                
                if st.button(f"📧 Send to {selected_category} clients ({len(filtered_clients)})", use_container_width=True):
                    st.info(f"Feature to send emails to {len(filtered_clients)} clients in '{selected_category}' category - Coming soon!")

def main():
    """Main function to run the send intro mail page"""
    st.set_page_config(
        page_title="Send Intro Mail - Lead Nurturing",
        page_icon="📧",
        layout="wide"
    )
    
    send_intro_mail_page()

if __name__ == "__main__":
    main()