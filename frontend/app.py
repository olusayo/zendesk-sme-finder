"""
Zendesk FDE Finder - Streamlit Frontend

Find the right Field Development Engineers for your support tickets.
"""

import streamlit as st
import requests
import json
from datetime import datetime
import os

# Configuration
API_ENDPOINT = os.getenv('API_ENDPOINT', 'https://api.example.com/find-fde')
API_KEY = os.getenv('API_KEY', '')

# Page configuration
st.set_page_config(
    page_title="Zendesk FDE Finder",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 600;
        color: #1e88e5;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .fde-card {
        background-color: #f8f9fa;
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        border-left: 4px solid #1e88e5;
    }
    .ticket-card {
        background-color: #fff8e1;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        border-left: 4px solid #ff9800;
    }
</style>
""", unsafe_allow_html=True)

def call_api(ticket_id: str = None, ticket_description: str = None) -> dict:
    """Call the FDE Finder API"""
    try:
        headers = {
            'Content-Type': 'application/json',
            'x-api-key': API_KEY
        }

        payload = {}
        if ticket_id:
            payload['ticket_id'] = ticket_id
        if ticket_description:
            payload['ticket_description'] = ticket_description

        response = requests.post(
            API_ENDPOINT,
            headers=headers,
            json=payload,
            timeout=120
        )

        response.raise_for_status()
        return response.json()

    except requests.exceptions.Timeout:
        return {"error": "Request timed out. Please try again."}
    except requests.exceptions.RequestException as e:
        return {"error": f"API Error: {str(e)}"}
    except json.JSONDecodeError:
        return {"error": "Invalid response from API"}


def main():
    """Main application"""

    # Header
    st.markdown('<div class="main-header">Zendesk FDE Finder</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Find the right Field Development Engineers for your support tickets</div>', unsafe_allow_html=True)

    st.markdown("---")

    # Input Method Selection
    st.markdown("### Input Method")
    st.markdown("Choose your input method:")

    input_method = st.radio(
        "",
        options=["Ticket ID", "Ticket Description"],
        horizontal=True,
        label_visibility="collapsed"
    )

    st.markdown("---")

    # Initialize session state
    if 'result' not in st.session_state:
        st.session_state.result = None
    if 'show_result' not in st.session_state:
        st.session_state.show_result = False

    # Input fields based on selection
    ticket_id = None
    ticket_description = None

    if input_method == "Ticket ID":
        st.markdown("#### Enter Ticket ID")
        ticket_id = st.text_input(
            "Ticket ID",
            placeholder="e.g., 12345",
            label_visibility="collapsed"
        )
    else:
        st.markdown("#### Enter Ticket Description")
        ticket_description = st.text_area(
            "Ticket Description",
            placeholder="PostgreSQL performance issues with high CPU usage",
            height=150,
            label_visibility="collapsed"
        )

    # Buttons
    col1, col2 = st.columns([1, 1])

    with col1:
        find_button = st.button("Find FDEs", type="primary", use_container_width=True)

    with col2:
        clear_button = st.button("Clear", use_container_width=True)

    # Handle clear button
    if clear_button:
        st.session_state.result = None
        st.session_state.show_result = False
        st.rerun()

    # Handle find button
    if find_button:
        if input_method == "Ticket ID" and not ticket_id:
            st.warning("Please enter a ticket ID")
            return

        if input_method == "Ticket Description" and not ticket_description:
            st.warning("Please enter a ticket description")
            return

        # Show loading spinner
        with st.spinner("Finding FDEs... This may take up to 2 minutes."):
            result = call_api(ticket_id=ticket_id, ticket_description=ticket_description)
            st.session_state.result = result
            st.session_state.show_result = True

    # Display results
    if st.session_state.show_result and st.session_state.result:
        result = st.session_state.result

        if "error" in result:
            st.error(result["error"])
        else:
            st.success("Successfully found FDEs for your issue!")

            # Two column layout for results
            col_left, col_right = st.columns([1, 1])

            with col_left:
                st.markdown("### Recommended Field Development Engineers")

                if result.get('recommended_fdes'):
                    for i, fde in enumerate(result['recommended_fdes'], 1):
                        confidence = fde.get('confidence', 0) * 100

                        st.markdown(f"""
                        <div class="fde-card">
                            <h4>{i}. {fde.get('name', 'Unknown')}</h4>
                            <p><strong>Match:</strong> {confidence:.0f}%</p>
                            <p><strong>Email:</strong> {fde.get('email', 'N/A')}</p>
                            <p><strong>Expertise:</strong> {', '.join(fde.get('expertise', []))}</p>
                            <p><strong>Slack:</strong> @{fde.get('slack_id', 'N/A')}</p>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("No FDEs found for this ticket")

            with col_right:
                st.markdown("### Similar Resolved Tickets")

                if result.get('similar_tickets'):
                    for ticket in result['similar_tickets'][:5]:
                        st.markdown(f"""
                        <div class="ticket-card">
                            <h5>Ticket #{ticket.get('ticket_id', 'N/A')}: {ticket.get('subject', 'No subject')}</h5>
                            <p><strong>Resolution:</strong> {ticket.get('resolution', 'No resolution details')[:200]}...</p>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("No similar tickets found")

            # Action links if available
            if result.get('slack_conversation_url') or result.get('zendesk_url'):
                st.markdown("---")
                st.markdown("### Next Steps")

                link_col1, link_col2 = st.columns(2)

                with link_col1:
                    if result.get('slack_conversation_url'):
                        st.markdown(f"[Open Slack Conversation]({result['slack_conversation_url']})")

                with link_col2:
                    if result.get('zendesk_url'):
                        st.markdown(f"[View Zendesk Ticket]({result['zendesk_url']})")


if __name__ == "__main__":
    main()
