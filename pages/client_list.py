"""
Client List Page
Shows all clients with filtering and navigation to client details
"""

import streamlit as st
import sys
import os

# Add the frontend directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.api_client import api_client, safe_api_call

def client_list_page():
    """Render the client list page"""
    st.title("📋 All Clients")
    st.markdown("---")
    
    # Check if user is logged in
    current_user = st.session_state.get("current_user")
    if not current_user:
        st.error("Please log in first to view clients.")
        return
    
    # Get all clients for current user
    with st.spinner("Loading clients..."):
        clients = safe_api_call(api_client.get_clients, current_user["user_id"])
    
    if not clients:
        st.info("No clients found. Create your first client!")
        if st.button("➕ Create Client", type="primary"):
            st.session_state["current_page"] = "create_client"
            st.rerun()
        return
    
    # Filter and search controls
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        search_term = st.text_input("🔍 Search clients...", placeholder="Enter name, email, or company")
    
    with col2:
        # Get unique categories
        categories = list(set([client.get("category", "Other") for client in clients]))
        selected_category = st.selectbox("Filter by Category", ["All"] + categories)
    
    with col3:
        sort_by = st.selectbox("Sort by", ["Name", "Company", "Created Date", "Email"])
    
    # Filter clients based on search and category
    filtered_clients = clients
    
    if search_term:
        search_lower = search_term.lower()
        filtered_clients = [
            client for client in filtered_clients
            if (search_lower in client.get("full_name", "").lower() or
                search_lower in client.get("email", "").lower() or
                search_lower in client.get("company", "").lower())
        ]
    
    if selected_category != "All":
        filtered_clients = [
            client for client in filtered_clients
            if client.get("category") == selected_category
        ]
    
    # Sort clients
    sort_key_map = {
        "Name": "full_name",
        "Company": "company",
        "Created Date": "created_at",
        "Email": "email"
    }
    
    sort_key = sort_key_map[sort_by]
    filtered_clients = sorted(filtered_clients, key=lambda x: x.get(sort_key, "") or "")
    
    # Display summary
    st.markdown(f"**Showing {len(filtered_clients)} of {len(clients)} clients**")
    
    # Display clients in a grid layout
    st.markdown("---")
    
    for i, client in enumerate(filtered_clients):
        with st.container():
            # Client card
            col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
            
            with col1:
                st.markdown(f"**{client.get('full_name', 'N/A')}**")
                st.write(f"📧 {client.get('email', 'N/A')}")
                if client.get("phone"):
                    st.write(f"📱 {client.get('phone')}")
            
            with col2:
                if client.get("company"):
                    st.write(f"🏢 **{client.get('company')}**")
                if client.get("category"):
                    st.write(f"🏷️ {client.get('category')}")
                if client.get("created_at"):
                    st.write(f"📅 {client.get('created_at')[:10]}")
            
            with col3:
                # Social links (if available)
                if client.get("linkedin_url"):
                    st.markdown(f"[LinkedIn]({client.get('linkedin_url')})")
                if client.get("company_website"):
                    st.markdown(f"[Website]({client.get('company_website')})")
            
            with col4:
                # Action button
                if st.button("View Details", key=f"view_client_{client.get('client_id')}"):
                    st.session_state["selected_client"] = client
                    st.session_state["current_page"] = "client_details"
                    st.rerun()
            
            st.markdown("---")
    
    # Pagination (if needed for large lists)
    if len(filtered_clients) > 20:
        st.info(f"Showing first 20 clients. Use search to find specific clients.")
    
    # Bulk actions section
    st.markdown("### 🔄 Bulk Actions")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📧 Send Intro Email to All", help="Send intro emails to filtered clients"):
            st.info("Bulk intro email feature - Coming Soon!")
    
    with col2:
        if st.button("📊 Export Client List", help="Export filtered clients to CSV"):
            if filtered_clients:
                # Create CSV data manually
                import csv
                import io
                
                output = io.StringIO()
                if filtered_clients:
                    writer = csv.DictWriter(output, fieldnames=filtered_clients[0].keys())
                    writer.writeheader()
                    writer.writerows(filtered_clients)
                    csv_data = output.getvalue()
                    
                    st.download_button(
                        label="Download CSV",
                        data=csv_data,
                        file_name="clients.csv",
                        mime="text/csv"
                    )
                else:
                    st.warning("No clients to export")
            else:
                st.warning("No clients to export")
    
    with col3:
        if st.button("➕ Add New Client"):
            st.session_state["current_page"] = "create_client"
            st.rerun()

def main():
    """Main function to run the client list page"""
    st.set_page_config(
        page_title="Client List - Lead Nurturing",
        page_icon="📋",
        layout="wide"
    )
    
    client_list_page()

if __name__ == "__main__":
    main()