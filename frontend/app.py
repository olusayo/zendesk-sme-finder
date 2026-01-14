"""
Zendesk FDE Finder - Streamlit Chat Interface

A conversational AI interface for finding Field Development Engineers (FDEs)
for complex support tickets.
"""

import streamlit as st
import requests
import json
import re
from datetime import datetime
import os

# Configuration
API_ENDPOINT = os.getenv('API_ENDPOINT', 'https://api.example.com/find-fde')
API_KEY = os.getenv('API_KEY', '')

# Page configuration
st.set_page_config(
    page_title="Zendesk FDE Finder",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS - Professional Masculine Design
st.markdown("""
<style>
    /* Import Professional Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

    /* Global Styling */
    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Main Container */
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
    }

    /* Main Content Area */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1200px;
    }

    /* Header Styling */
    .main-header {
        font-size: 3rem;
        font-weight: 800;
        background: linear-gradient(135deg, #3b82f6 0%, #06b6d4 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 0.5rem;
        letter-spacing: -0.02em;
        line-height: 1.2;
    }

    .sub-header {
        font-size: 1.25rem;
        color: #94a3b8;
        font-weight: 500;
        margin-bottom: 2.5rem;
        letter-spacing: -0.01em;
    }

    /* Chat Messages */
    .stChatMessage {
        background: rgba(30, 41, 59, 0.6) !important;
        border: 1px solid rgba(59, 130, 246, 0.2);
        border-radius: 1rem !important;
        padding: 1.5rem !important;
        margin-bottom: 1rem !important;
        backdrop-filter: blur(10px);
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    }

    /* User Messages */
    [data-testid="stChatMessageContent"] {
        color: #e2e8f0 !important;
        font-size: 1rem;
        line-height: 1.6;
    }

    /* Assistant Messages - Enhanced */
    .stChatMessage[data-testid*="assistant"] {
        background: linear-gradient(135deg, rgba(30, 58, 138, 0.4) 0%, rgba(30, 41, 59, 0.6) 100%) !important;
        border-left: 4px solid #3b82f6;
    }

    /* Chat Input */
    .stChatInputContainer {
        background: rgba(30, 41, 59, 0.8);
        border: 2px solid rgba(59, 130, 246, 0.3);
        border-radius: 1rem;
        padding: 0.5rem;
        backdrop-filter: blur(10px);
    }

    .stChatInput input {
        background: transparent !important;
        color: #e2e8f0 !important;
        font-size: 1rem;
        font-weight: 500;
        border: none !important;
    }

    .stChatInput input::placeholder {
        color: #64748b !important;
        font-weight: 400;
    }

    /* Markdown in Messages */
    .stChatMessage h3 {
        color: #60a5fa;
        font-weight: 700;
        font-size: 1.25rem;
        margin-top: 1rem;
        margin-bottom: 0.75rem;
        letter-spacing: -0.01em;
    }

    .stChatMessage h1, .stChatMessage h2 {
        color: #3b82f6;
        font-weight: 700;
    }

    .stChatMessage strong {
        color: #cbd5e1;
        font-weight: 700;
    }

    .stChatMessage a {
        color: #06b6d4;
        font-weight: 600;
        text-decoration: none;
        border-bottom: 2px solid rgba(6, 182, 212, 0.3);
        transition: all 0.2s ease;
    }

    .stChatMessage a:hover {
        color: #22d3ee;
        border-bottom-color: #22d3ee;
    }

    /* Code Blocks */
    .stChatMessage code {
        background: rgba(15, 23, 42, 0.8) !important;
        color: #22d3ee !important;
        padding: 0.25rem 0.5rem;
        border-radius: 0.375rem;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.9rem;
        border: 1px solid rgba(6, 182, 212, 0.2);
    }

    /* Lists */
    .stChatMessage ul, .stChatMessage ol {
        color: #cbd5e1;
        line-height: 1.8;
    }

    .stChatMessage li {
        margin-bottom: 0.5rem;
    }

    /* Divider */
    hr {
        border-color: rgba(59, 130, 246, 0.2) !important;
        margin: 1.5rem 0;
    }

    /* Sidebar */
    .css-1d391kg, [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
        border-right: 1px solid rgba(59, 130, 246, 0.2);
    }

    .css-1d391kg h3, [data-testid="stSidebar"] h3 {
        color: #3b82f6;
        font-weight: 700;
        font-size: 1.25rem;
        margin-bottom: 1rem;
    }

    /* Info Box */
    .stAlert {
        background: rgba(30, 58, 138, 0.3) !important;
        border: 1px solid rgba(59, 130, 246, 0.3);
        border-radius: 0.75rem;
        color: #cbd5e1 !important;
    }

    /* Buttons */
    .stButton button {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
        color: white;
        font-weight: 600;
        border: none;
        border-radius: 0.75rem;
        padding: 0.75rem 1.5rem;
        font-size: 1rem;
        transition: all 0.3s ease;
        box-shadow: 0 4px 6px rgba(59, 130, 246, 0.3);
    }

    .stButton button:hover {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
        box-shadow: 0 6px 12px rgba(59, 130, 246, 0.4);
        transform: translateY(-2px);
    }

    /* Spinner */
    .stSpinner > div {
        border-top-color: #3b82f6 !important;
    }

    /* Success/Error Messages */
    .element-container .stMarkdown p {
        color: #cbd5e1;
    }

    /* Caption Text */
    .css-1629p8f, .css-10trblm {
        color: #64748b !important;
        font-size: 0.875rem;
    }

    /* Scrollbar */
    ::-webkit-scrollbar {
        width: 10px;
        height: 10px;
    }

    ::-webkit-scrollbar-track {
        background: rgba(15, 23, 42, 0.5);
    }

    ::-webkit-scrollbar-thumb {
        background: rgba(59, 130, 246, 0.5);
        border-radius: 5px;
    }

    ::-webkit-scrollbar-thumb:hover {
        background: rgba(59, 130, 246, 0.7);
    }
</style>
""", unsafe_allow_html=True)

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": """⚡ **Welcome to the Zendesk FDE Finder**

I'm your AI-powered assistant for connecting engineers with the right Field Development Experts.

### How can I help you?

**Try these commands:**
- `Find FDEs for ticket 12345`
- `Who can help with ticket 789?`
- `Customer experiencing PostgreSQL performance issues with timeouts`

**Two ways to get help:**
- 📋 **With Ticket ID**: Get full Zendesk integration (fetch ticket, update, create Slack)
- 📝 **Description Only**: Get FDE recommendations based on your description

**What I provide:**
- 🎯 Top 3 expert matches with expertise reasoning
- 📊 Similar ticket resolutions from Knowledge Base
- 💬 Direct Slack conversation links (when ticket ID provided)
- ⚡ Lightning-fast AI-powered analysis

Enter a ticket ID or describe your issue below to get started."""
        }
    ]

def extract_ticket_id(message: str) -> str:
    """Extract ticket ID from natural language message"""
    # Look for patterns like "ticket 12345", "#12345", or just numbers
    patterns = [
        r'ticket\s+(\d+)',
        r'#(\d+)',
        r'\b(\d{4,})\b'  # 4 or more digits
    ]

    for pattern in patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            return match.group(1)

    return None

def call_api(ticket_id: str = None, ticket_description: str = None) -> dict:
    """Call the FDE Finder API with either ticket ID or description"""
    try:
        headers = {
            'Content-Type': 'application/json',
            'x-api-key': API_KEY
        }

        # Build payload based on what's provided
        payload = {}
        if ticket_id:
            payload['ticket_id'] = ticket_id
        if ticket_description:
            payload['ticket_description'] = ticket_description

        response = requests.post(
            API_ENDPOINT,
            headers=headers,
            json=payload,
            timeout=120  # Allow up to 2 minutes for Bedrock Agent
        )

        response.raise_for_status()
        return response.json()

    except requests.exceptions.Timeout:
        return {"error": "Request timed out. The system is taking longer than expected."}
    except requests.exceptions.RequestException as e:
        return {"error": f"API Error: {str(e)}"}
    except json.JSONDecodeError:
        return {"error": "Invalid response from API"}

def format_fde_response(result: dict, ticket_id: str) -> str:
    """Format API response into conversational message"""
    if "error" in result:
        return f"❌ {result['error']}\n\nPlease try again or contact support if the issue persists."

    message = f"✅ **Found FDEs for ticket #{ticket_id}**\n\n"

    # Display recommended FDEs
    if result.get('recommended_fdes'):
        message += "### 👥 Recommended Field Development Engineers\n\n"
        for i, fde in enumerate(result['recommended_fdes'], 1):
            confidence = fde.get('confidence', 0) * 100
            message += f"**{i}. {fde.get('name', 'Unknown')}** - {confidence:.0f}% Match\n"
            message += f"- 📧 Email: {fde.get('email', 'N/A')}\n"
            message += f"- 🎯 Expertise: {', '.join(fde.get('expertise', []))}\n"
            message += f"- 💬 Slack: @{fde.get('slack_id', 'N/A')}\n\n"
    else:
        message += "⚠️ No FDEs found for this ticket.\n\n"

    # Display similar tickets
    if result.get('similar_tickets'):
        message += "### 🎫 Similar Resolved Tickets\n\n"
        for ticket in result['similar_tickets'][:3]:  # Show top 3
            message += f"**Ticket #{ticket.get('ticket_id', 'N/A')}**: {ticket.get('subject', 'No subject')}\n"
            message += f"Resolution: {ticket.get('resolution', 'No resolution details')[:100]}...\n\n"

    # Display action links
    message += "### 🔗 Next Steps\n\n"

    if result.get('slack_conversation_url'):
        message += f"✅ [Open Slack Conversation]({result['slack_conversation_url']})\n"

    if result.get('zendesk_url'):
        message += f"✅ [View Zendesk Ticket]({result['zendesk_url']})\n"

    message += "\n---\n\nNeed help with another ticket? Just let me know the ticket number!"

    return message

def main():
    """Main application"""

    # Header
    st.markdown('<div class="main-header">⚡ Zendesk FDE Finder</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">AI-Powered Expert Matching for Support Engineers</div>', unsafe_allow_html=True)

    st.markdown("---")

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("⚡ Enter ticket ID or ask for help... (e.g., 'Find FDEs for ticket 12345')"):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)

        # Extract ticket ID from user message
        ticket_id = extract_ticket_id(prompt)

        # Display assistant thinking message
        with st.chat_message("assistant"):
            if ticket_id:
                # Has ticket ID - try full flow first
                with st.spinner(f"🔍 Searching for FDEs for ticket #{ticket_id}... This may take up to 2 minutes."):
                    # Call API with both ticket_id and description (for fallback)
                    result = call_api(ticket_id=ticket_id, ticket_description=prompt)

                    # Format response
                    response = format_fde_response(result, ticket_id)

                    # Display response
                    st.markdown(response)

                    # Add to chat history
                    st.session_state.messages.append({"role": "assistant", "content": response})
            else:
                # No ticket ID - use description-only flow
                with st.spinner(f"🔍 Analyzing your description and searching for matching FDEs... This may take up to 2 minutes."):
                    # Call API with description only
                    result = call_api(ticket_description=prompt)

                    # Format response (use "Description" instead of ticket_id)
                    response = format_fde_response(result, "Description")

                    # Display response
                    st.markdown(response)

                    # Add to chat history
                    st.session_state.messages.append({"role": "assistant", "content": response})

    # Sidebar
    with st.sidebar:
        st.markdown("### 💡 About")
        st.info("""
        **AI-Powered Expert Matching**

        This system analyzes:
        - 🎯 Ticket complexity and technical requirements
        - 📊 Historical resolution patterns
        - 🏆 FDE expertise and certifications
        - ✅ Success rates and specializations
        """)

        st.markdown("### 🚀 Quick Start")
        st.markdown("""
        1. **Enter** a ticket ID OR describe your issue
        2. **Wait** 30-60 seconds for AI analysis
        3. **Review** top 3 expert matches
        4. **Connect** via Slack (if ticket ID provided)
        """)

        st.markdown("### 📝 Example Requests")
        st.code("""
# With Ticket ID (full integration)
Find FDEs for ticket 12345
Who can help with #789?

# Description Only (FDE recommendations)
PostgreSQL performance issues with timeouts
Customer needs help with GCP BigQuery
Python API integration failing
        """)

        # Clear chat button
        if st.button("🗑️ Clear Chat History", use_container_width=True):
            st.session_state.messages = [
                {
                    "role": "assistant",
                    "content": """⚡ **Welcome to the Zendesk FDE Finder**

I'm your AI-powered assistant for connecting engineers with the right Field Development Experts.

### How can I help you?

**Try these commands:**
- `Find FDEs for ticket 12345`
- `Who can help with ticket 789?`
- `Customer experiencing PostgreSQL performance issues with timeouts`

**Two ways to get help:**
- 📋 **With Ticket ID**: Get full Zendesk integration (fetch ticket, update, create Slack)
- 📝 **Description Only**: Get FDE recommendations based on your description

**What I provide:**
- 🎯 Top 3 expert matches with expertise reasoning
- 📊 Similar ticket resolutions from Knowledge Base
- 💬 Direct Slack conversation links (when ticket ID provided)
- ⚡ Lightning-fast AI-powered analysis

Enter a ticket ID or describe your issue below to get started."""
                }
            ]
            st.rerun()

        st.markdown("---")
        st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
