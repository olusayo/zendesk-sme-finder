# Chat Interface - Zendesk FDE Finder

The Streamlit frontend now features a conversational chat interface for finding Field Development Engineers.

---

## Overview

The chat interface allows users to interact with the FDE Finder using natural language instead of a form-based input.

### Key Features

1. **Natural Language Processing**: Extracts ticket IDs from conversational messages
2. **Chat History**: Maintains conversation context across multiple queries
3. **Conversational Responses**: Formatted, easy-to-read recommendations
4. **Multi-Pattern Recognition**: Understands various ways of asking for help

---

## How to Use

### Starting a Conversation

When you open the app, you'll see a welcome message:

```
Hello! I'm the Zendesk FDE Finder assistant. I can help you find
the best Field Development Engineers for your support tickets.

You can ask me things like:
- 'Find FDEs for ticket 12345'
- 'Who can help with ticket 789?'
- 'Get recommendations for ticket 54321'

What ticket would you like help with?
```

### Making Requests

You can ask in various natural language formats:

**Examples**:
- `Find FDEs for ticket 12345`
- `Who can help with ticket 789?`
- `Get recommendations for #54321`
- `I need help with ticket 999`
- `12345` (just the number)

The system automatically extracts the ticket ID and processes your request.

### Getting Results

The assistant responds with:

1. **Recommended FDEs** with confidence scores
2. **Similar Tickets** that were resolved successfully
3. **Action Links** to Slack conversations and Zendesk tickets
4. **Helpful prompts** for next steps

Example response:
```
✅ Found FDEs for ticket #12345

👥 Recommended Field Development Engineers

1. John Doe - 95% Match
   - Email: john.doe@company.com
   - Expertise: Kubernetes, AWS, Python
   - Slack: @johndoe

2. Jane Smith - 87% Match
   - Email: jane.smith@company.com
   - Expertise: Docker, CI/CD, Monitoring
   - Slack: @janesmith

🎫 Similar Resolved Tickets

Ticket #11234: Database connection timeout issue
Resolution: Fixed by updating connection pool settings...

🔗 Next Steps

✅ Open Slack Conversation
✅ View Zendesk Ticket

---

Need help with another ticket? Just let me know the ticket number!
```

---

## Pattern Recognition

The chat interface recognizes ticket IDs in these formats:

| Pattern | Example | Recognized ID |
|---------|---------|---------------|
| `ticket 12345` | "Find FDEs for ticket 12345" | 12345 |
| `#12345` | "Who can help with #12345?" | 12345 |
| Just numbers | "Get recommendations for 12345" | 12345 |
| 4+ digits anywhere | "I need help with 999999" | 999999 |

**Case Insensitive**: Works with any capitalization

---

## Chat Features

### 1. Conversation History

The chat maintains all previous messages in the session:
- Scroll up to see past conversations
- Review previous recommendations
- Context persists until cleared

### 2. Clear Chat Button

Located in the sidebar:
- Click "🗑️ Clear Chat History" to start fresh
- Resets conversation to initial greeting
- Useful for starting a new session

### 3. Sidebar Information

The sidebar provides:
- **About**: How the AI matching works
- **How to Use**: Step-by-step instructions
- **Example Requests**: Copy-paste examples
- **Clear History Button**: Reset conversation

---

## Technical Details

### Session State

The chat uses Streamlit's session state to maintain history:

```python
st.session_state.messages = [
    {"role": "user", "content": "Find FDEs for ticket 12345"},
    {"role": "assistant", "content": "✅ Found FDEs..."}
]
```

### Ticket ID Extraction

Uses regex patterns to extract ticket IDs:

```python
patterns = [
    r'ticket\s+(\d+)',  # "ticket 12345"
    r'#(\d+)',          # "#12345"
    r'\b(\d{4,})\b'     # Any 4+ digit number
]
```

### API Integration

Same backend integration as the form interface:
- POST request to API Gateway
- Includes API key authentication
- 120-second timeout for Bedrock Agent
- Error handling with user-friendly messages

---

## Comparison: Chat vs Form Interface

| Feature | Chat Interface | Form Interface |
|---------|----------------|----------------|
| Input Method | Natural language | Text input field |
| User Experience | Conversational | Direct/formal |
| Learning Curve | Minimal | None |
| History | Maintained | Single query |
| Flexibility | High | Low |
| Mobile-Friendly | Yes | Yes |
| Professional Use | Good | Better |

---

## Example Conversation

**User**: `Find FDEs for ticket 12345`

**Assistant**: `🔍 Searching for FDEs for ticket #12345...`

**Assistant**:
```
✅ Found FDEs for ticket #12345

👥 Recommended Field Development Engineers

1. John Doe - 95% Match
   - 📧 Email: john.doe@company.com
   - 🎯 Expertise: Kubernetes, AWS, Python
   - 💬 Slack: @johndoe

...

Need help with another ticket? Just let me know the ticket number!
```

**User**: `How about ticket 789?`

**Assistant**: `🔍 Searching for FDEs for ticket #789...`

---

## Error Handling

### No Ticket ID Found

**User**: `I need help`

**Assistant**:
```
I couldn't find a ticket ID in your message.

Please include a ticket number like:
- "Find FDEs for ticket 12345"
- "Who can help with #789?"
- "Get recommendations for 54321"

What ticket would you like help with?
```

### API Errors

**User**: `Find FDEs for ticket 12345`

**Assistant** (if API fails):
```
❌ API Error: Connection timeout

Please try again or contact support if the issue persists.
```

---

## Deployment Notes

### Docker Deployment

The Dockerfile remains unchanged - the chat interface uses only standard Streamlit features:

```dockerfile
CMD ["streamlit", "run", "app.py", ...]
```

### Environment Variables

Same as before:
- `API_ENDPOINT`: API Gateway URL
- `API_KEY`: Authentication key

### Resource Requirements

Chat interface has minimal overhead:
- **Memory**: Same as form interface (~100MB)
- **CPU**: Negligible increase
- **Storage**: Session state stored in memory

---

## Customization

### Changing Welcome Message

Edit the initial message in `app.py`:

```python
st.session_state.messages = [
    {
        "role": "assistant",
        "content": "Your custom welcome message here..."
    }
]
```

### Modifying Response Format

Update the `format_fde_response()` function:

```python
def format_fde_response(result: dict, ticket_id: str) -> str:
    # Customize formatting here
    message = f"Custom format for ticket {ticket_id}"
    return message
```

### Adding New Patterns

Add patterns to `extract_ticket_id()`:

```python
patterns = [
    r'ticket\s+(\d+)',
    r'custom\s+pattern\s+(\d+)',  # New pattern
]
```

---

## Troubleshooting

### Chat Not Responding

**Issue**: Input box doesn't work

**Solution**:
- Refresh the page
- Check browser console for errors
- Ensure Streamlit version >= 1.28.0

### Ticket ID Not Recognized

**Issue**: "I couldn't find a ticket ID"

**Solution**:
- Use one of the supported formats
- Include at least 4 digits
- Try: `ticket 12345` instead of custom phrasing

### Chat History Not Clearing

**Issue**: Clear button doesn't work

**Solution**:
- Click the button and wait for reload
- Manually refresh the page (F5)
- Check if session state is enabled

---

## Future Enhancements

Potential improvements for the chat interface:

1. **Multi-turn Conversations**
   - Follow-up questions about specific FDEs
   - Ask for more details on similar tickets

2. **Rich Media**
   - Embedded charts for confidence scores
   - Profile pictures for FDEs
   - Ticket timeline visualizations

3. **Voice Input**
   - Speech-to-text for mobile users
   - Hands-free operation

4. **Smart Suggestions**
   - Autocomplete for ticket IDs
   - Recently searched tickets
   - Trending issues

5. **Export Functionality**
   - Download conversation as PDF
   - Email recommendations
   - Copy to clipboard

---

## Migration from Form Interface

If you prefer the original form interface:

### Option 1: Keep Both Versions

Create two separate files:
- `app_chat.py` - Chat interface (current)
- `app_form.py` - Original form interface

Deploy both and use URL parameters to switch.

### Option 2: Revert to Form

The original form interface code is preserved in git history:

```bash
git checkout HEAD~1 -- frontend/app.py
```

---

## Support

For issues or questions:
- Check CloudWatch logs: `/ecs/zendesk-sme-finder-frontend`
- Review conversation history for debugging
- Test with known ticket IDs first

---

## Summary

The chat interface provides a modern, conversational way to interact with the FDE Finder while maintaining all the functionality of the original form-based interface. It's production-ready and requires no additional configuration beyond the standard deployment.
