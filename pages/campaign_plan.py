"""
Campaign Plan Page
Shows day-wise campaign plans with editing capability, suggestion improvements, and approval functionality
"""

import streamlit as st
import sys
import os

# Add the frontend directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.api_client import api_client, safe_api_call, display_api_response

def campaign_plan_page():
    """Render the campaign plan page"""
    
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
    st.title(f"📋 Campaign Plan - {client_name}")
    st.markdown("---")
    
    # First, get the client's campaigns
    with st.spinner("Loading client campaigns..."):
        client_campaigns_response = safe_api_call(api_client.get_client_auto_campaigns, client_id)
    
    if not client_campaigns_response:
        st.error("No campaigns found for this client.")
        st.info("Make sure the client has a campaign strategy created first.")
        
        if st.button("⬅️ Back to Client Details", key="campaign_back_error1"):
            st.session_state["current_page"] = "client_details"
            st.rerun()
        return
    
    # Extract the campaigns list from the API response
    client_campaigns = client_campaigns_response.get("auto_campaigns", [])
    
    if not client_campaigns:
        st.error("No active campaigns found for this client.")
        st.info("The client may not have any auto-generated campaigns yet.")
        
        if st.button("⬅️ Back to Client Details", key="campaign_back_error1a"):
            st.session_state["current_page"] = "client_details"
            st.rerun()
        return
    
    # Get the first campaign (or let user select)
    campaign = client_campaigns[0] if client_campaigns else None
    if not campaign:
        st.error("No active campaign found for this client.")
        return
    
    campaign_id = campaign.get("campaign_id")
    
    # Load campaign plan
    with st.spinner("Loading campaign plan..."):
        campaign_plan = safe_api_call(api_client.get_campaign_plan, campaign_id)
    
    if not campaign_plan:
        st.error("Unable to load campaign plan for this client.")
        st.info("The campaign plan may not have been generated yet.")
        
        if st.button("⬅️ Back to Client Details", key="campaign_back_error2"):
            st.session_state["current_page"] = "client_details"
            st.rerun()
        return
    
    # Campaign plan overview
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader("📋 Campaign Overview")
        st.write(f"**Campaign Name:** {campaign_plan.get('campaign_name', 'N/A')}")
        st.write(f"**Description:** {campaign_plan.get('campaign_description', 'N/A')[:200]}{'...' if len(campaign_plan.get('campaign_description', '')) > 200 else ''}")
        st.write(f"**Status:** {campaign_plan.get('approval_status', 'N/A')}")
        st.write(f"**Total Days:** {campaign_plan.get('total_days', 'N/A')}")
    
    with col2:
        st.subheader("🎯 Quick Actions")
        if st.button("🔄 Refresh Plan", use_container_width=True):
            st.rerun()
    
    # Day-wise campaign plan
    st.markdown("---")
    st.subheader("📅 Day-wise Campaign Plan")
    
    campaign_days = campaign_plan.get("daily_breakdown", [])
    
    if not campaign_days:
        st.warning("No campaign days found.")
        return
    
    # Initialize session state for edits
    if "campaign_edits" not in st.session_state:
        st.session_state["campaign_edits"] = {}
    
    # Display each day with editing capability
    for day_info in campaign_days:
        day_number = day_info.get("day", 0)
        
        with st.container():
            st.markdown(f"### 📅 Day {day_number}")
            
            # Create columns for day content and edit controls
            content_col, edit_col = st.columns([3, 1])
            
            with content_col:
                # Display current content
                current_title = day_info.get("title", "No Title")
                current_subject = day_info.get("subject_line", "No Subject")
                current_objective = day_info.get("objective", "No Objective")
                current_content = day_info.get("content_idea", "No Content")
                
                st.markdown(f"**Title:** {current_title}")
                st.markdown(f"**Subject Line:** {current_subject}")
                st.markdown(f"**Objective:** {current_objective}")
                st.markdown("**Content Idea:**")
                st.text_area("", value=current_content, height=120, disabled=True, 
                           key=f"display_day_{day_number}")
            
            with edit_col:
                # Edit mode toggle
                edit_key = f"edit_day_{day_number}"
                is_editing = st.checkbox("✏️ Edit", key=edit_key)
                
                if is_editing:
                    # Show edit fields
                    with st.form(f"edit_form_day_{day_number}"):
                        st.markdown("**Edit Day Content:**")
                        
                        new_title = st.text_input(
                            "Title", 
                            value=current_title,
                            key=f"title_day_{day_number}"
                        )
                        
                        new_subject = st.text_input(
                            "Subject Line", 
                            value=current_subject,
                            key=f"subject_day_{day_number}"
                        )
                        
                        new_objective = st.text_area(
                            "Objective", 
                            value=current_objective,
                            height=80,
                            key=f"objective_day_{day_number}"
                        )
                        
                        new_content = st.text_area(
                            "Content Idea", 
                            value=current_content,
                            height=120,
                            key=f"content_day_{day_number}"
                        )
                        
                        # Submit suggestion
                        if st.form_submit_button("💡 Suggest Improvement"):
                            # Prepare improvement data for AI agent
                            suggestion_text = f"For day {day_number}:"
                            if new_title != current_title:
                                suggestion_text += f" change title to '{new_title}'"
                            if new_subject != current_subject:
                                suggestion_text += f" change subject to '{new_subject}'"
                            if new_objective != current_objective:
                                suggestion_text += f" change objective to '{new_objective}'"
                            if new_content != current_content:
                                suggestion_text += f" change content to '{new_content}'"
                            
                            improvement_data = {
                                "suggestion": suggestion_text,
                                "day": day_number,
                                "field": "multiple"
                            }
                            
                            # Call suggest improvement API with campaign_id
                            with st.spinner("Submitting suggestion..."):
                                response = safe_api_call(api_client.suggest_improvement, campaign_id, improvement_data)
                            
                            if response:
                                display_api_response(response, "Improvement suggestion submitted successfully!")
                                st.success("Your suggestions have been noted. The plan will be updated.")
                                
                                # Store the edit for local display
                                st.session_state["campaign_edits"][day_number] = {
                                    "title": new_title,
                                    "subject_line": new_subject,
                                    "objective": new_objective,
                                    "content_idea": new_content
                                }
                                
                                # Refresh the plan
                                st.rerun()
            
            st.markdown("---")
    
    # Approve Campaign Section
    st.markdown("### ✅ Campaign Approval")
    
    campaign_status = campaign_plan.get('approval_status', 'pending_review')
    
    if campaign_status == 'approved':
        st.success("✅ This campaign has been approved!")
        st.write(f"**Approved At:** {campaign_plan.get('approved_at', 'N/A')}")
    
    elif campaign_status == 'rejected':
        st.error("❌ This campaign has been rejected.")
        st.write(f"**Feedback:** {campaign_plan.get('user_feedback', 'No feedback provided')}")
    
    else:
        # Show approval interface
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.info("📋 Review the campaign plan above and approve when ready.")
            
            # Optional feedback before approval
            approval_feedback = st.text_area(
                "Optional Feedback (will be saved with approval)",
                placeholder="Any additional notes or feedback about this campaign...",
                height=100
            )
        
        with col2:
            st.markdown("**Approval Actions:**")
            
            # Approve button
            if st.button("✅ Approve Campaign", type="primary", use_container_width=True):
                # Call approve API with campaign_id
                with st.spinner("Approving campaign..."):
                    response = safe_api_call(api_client.approve_campaign, campaign_id)
                
                if response:
                    display_api_response(response, "Campaign approved successfully! 🎉")
                    st.success("The campaign is now approved and ready for execution!")
                    
                    # Refresh the page to show updated status
                    st.rerun()
            
            # Note: Use the "Suggest Improvement" feature above to request changes instead of rejecting
    
    # Navigation and additional actions
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("⬅️ Back to Client Details", key="campaign_back_bottom"):
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
    
    # Debug information (expandable)
    with st.expander("🔍 Debug Information"):
        st.markdown("**Campaign Plan Data:**")
        st.json(campaign_plan)
        
        st.markdown("**Client Campaigns Response:**")
        st.json(client_campaigns_response)
        
        if st.session_state.get("campaign_edits"):
            st.markdown("**Local Edits:**")
            st.json(st.session_state["campaign_edits"])

def main():
    """Main function to run the campaign plan page"""
    st.set_page_config(
        page_title="Campaign Plan - Lead Nurturing",
        page_icon="📋",
        layout="wide"
    )
    
    campaign_plan_page()

if __name__ == "__main__":
    main()