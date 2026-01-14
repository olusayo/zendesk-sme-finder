# Hybrid Workflow Guide - Zendesk SME Finder

## Overview

The Zendesk SME Finder now supports a **hybrid workflow** that gracefully handles scenarios where Zendesk and Slack API credentials are not available. This allows you to:

1. ✅ **Test the system** without API credentials using ticket descriptions
2. ✅ **Get FDE recommendations** based on historical data and expertise matching
3. ✅ **Use full integration** when API credentials become available (future)
4. ✅ **Automatic fallback** if Zendesk API calls fail

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit Frontend                        │
│   User Input: Ticket ID and/or Ticket Description           │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   API Gateway + Orchestrator Lambda          │
│                                                              │
│  ┌──────────────────────────────────────────────────┐      │
│  │  Decision Logic:                                  │      │
│  │                                                    │      │
│  │  Has Ticket ID?                                   │      │
│  │    YES → Try Full Workflow                        │      │
│  │           ├─ Success: Use Zendesk data            │      │
│  │           └─ Fail: Fallback to description        │      │
│  │                                                    │      │
│  │    NO → Description-Only Workflow                 │      │
│  └──────────────────────────────────────────────────┘      │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    Bedrock Agent                             │
│                                                              │
│  Mode 1: Full Workflow (with API keys)                      │
│    1. fetchTicket (Zendesk Lambda)                          │
│    2. Search Knowledge Bases                                 │
│    3. Recommend Top 3 FDEs                                   │
│    4. createConversation (Slack Lambda)                      │
│    5. updateTicket (Zendesk Lambda)                          │
│                                                              │
│  Mode 2: Fallback (API call fails)                          │
│    1. Skip fetchTicket                                       │
│    2. Use provided description                               │
│    3. Search Knowledge Bases                                 │
│    4. Recommend Top 3 FDEs                                   │
│    5. Skip Slack/Zendesk updates                            │
│                                                              │
│  Mode 3: Description-Only (no ticket ID)                     │
│    1. Skip all Zendesk/Slack operations                     │
│    2. Search Knowledge Bases                                 │
│    3. Recommend Top 3 FDEs                                   │
└───────────────────────────┬─────────────────────────────────┘
                            │
        ┌───────────────────┴──────────────────┐
        │                                      │
        ↓                                      ↓
┌──────────────────────┐          ┌───────────────────────┐
│  Similar Tickets KB  │          │   FDE Profiles KB    │
│  (Historical Data)   │          │  (Expertise Data)    │
└──────────────────────┘          └───────────────────────┘
```

---

## Three Workflow Modes

### Mode 1: Full Workflow (With API Keys)

**When:** User provides ticket ID AND Zendesk/Slack API keys are configured

**User Input:**
```
Find FDEs for ticket 12345
```

**Flow:**
1. Orchestrator receives `ticket_id: "12345"`
2. Agent calls `fetchTicket` Lambda → Gets full ticket details from Zendesk
3. Agent searches `similar-tickets-kb` for historical matches
4. Agent searches `fde-profiles-kb` for expertise matches
5. Agent recommends Top 3 FDEs with reasoning
6. Agent calls `createConversation` Lambda → Creates Slack channel
7. Agent calls `updateTicket` Lambda → Updates Zendesk with Slack link
8. Returns FDE recommendations + Slack URL + Zendesk URL

**Output:**
```json
{
  "recommended_fdes": [...],
  "similar_tickets": [...],
  "slack_conversation_url": "https://workspace.slack.com/archives/C12345",
  "zendesk_url": "https://company.zendesk.com/agent/tickets/12345",
  "workflow_mode": "full"
}
```

---

### Mode 2: Fallback Workflow (Ticket ID but API Fails)

**When:** User provides ticket ID BUT Zendesk API keys are missing or invalid

**User Input:**
```
Find FDEs for ticket 12345
```

**Flow:**
1. Orchestrator receives `ticket_id: "12345"` and `ticket_description: "Find FDEs for ticket 12345"`
2. Agent tries `fetchTicket` Lambda → **Fails** (401 Unauthorized or connection error)
3. Agent gracefully handles failure, extracts description from user input
4. Agent searches `similar-tickets-kb` using description
5. Agent searches `fde-profiles-kb` for expertise matches
6. Agent recommends Top 3 FDEs with reasoning
7. Agent skips `createConversation` and `updateTicket` (no API access)
8. Returns FDE recommendations only

**Output:**
```json
{
  "recommended_fdes": [...],
  "similar_tickets": [...],
  "slack_conversation_url": "",
  "zendesk_url": "",
  "workflow_mode": "fallback"
}
```

---

### Mode 3: Description-Only Workflow (No Ticket ID)

**When:** User provides only a description, no ticket ID

**User Input:**
```
Customer experiencing PostgreSQL performance issues with slow queries and timeouts on production database
```

**Flow:**
1. Orchestrator receives `ticket_description: "Customer experiencing..."`
2. Agent receives explicit instruction: "Do NOT attempt Zendesk/Slack operations"
3. Agent searches `similar-tickets-kb` using description
4. Agent searches `fde-profiles-kb` for expertise matches
5. Agent recommends Top 3 FDEs with reasoning
6. Returns FDE recommendations only

**Output:**
```json
{
  "recommended_fdes": [...],
  "similar_tickets": [...],
  "slack_conversation_url": "",
  "zendesk_url": "",
  "workflow_mode": "description-only"
}
```

---

## Frontend User Experience

### With Ticket ID
```
User: "Find FDEs for ticket 12345"
System: "🔍 Searching for FDEs for ticket #12345..."
System: (Tries Zendesk API, gracefully falls back if needed)
System: "✅ Found FDEs for ticket #12345

### 👥 Recommended Field Development Engineers

**1. John Doe** - 95% Match
- 📧 Email: john.doe@company.com
- 🎯 Expertise: PostgreSQL, Performance Tuning, Cloud Infrastructure
- 💬 Slack: @U12345678
- 📝 Reasoning: Strong PostgreSQL expertise with 8+ years experience. Successfully resolved 15 similar performance issues.

**2. Jane Smith** - 88% Match
- 📧 Email: jane.smith@company.com
- 🎯 Expertise: Database Architecture, PostgreSQL, Query Optimization
- 💬 Slack: @U87654321
- 📝 Reasoning: Database architecture specialist with deep PostgreSQL knowledge.

**3. Mike Johnson** - 82% Match
- 📧 Email: mike.johnson@company.com
- 🎯 Expertise: DevOps, PostgreSQL, Performance Monitoring
- 💬 Slack: @U11223344
- 📝 Reasoning: DevOps background with PostgreSQL performance expertise."
```

### With Description Only
```
User: "Customer experiencing PostgreSQL performance issues with slow queries and timeouts"
System: "🔍 Analyzing your description and searching for matching FDEs..."
System: (Searches Knowledge Bases directly, skips Zendesk/Slack)
System: (Returns same FDE recommendations as above)
```

---

## Benefits of Hybrid Approach

### 1. **Testable Without API Keys** ✅
- Deploy the system immediately
- Test AI recommendations
- Validate Knowledge Base search quality
- Demo the system to stakeholders

### 2. **Graceful Degradation** ✅
- System never fails completely
- Always provides FDE recommendations
- Users get value even without full integration

### 3. **Future-Ready** ✅
- Add API keys later without code changes
- Automatic upgrade to full functionality
- No redeployment needed

### 4. **Flexible Input** ✅
- Users can provide ticket IDs when available
- Users can describe issues in natural language
- System adapts to what's provided

---

## Knowledge Bases - Core of the System

Both workflows rely on two Knowledge Bases that contain real historical data:

### 1. Similar Tickets Knowledge Base
**S3 Location:** `s3://genai-enablement-team3/tickets/`
**Purpose:** Historical Zendesk tickets with resolutions
**Contents:**
- Ticket descriptions
- Technical requirements
- Resolution summaries
- Tags and categories
- Success metrics

**Search Query Example:**
```
"PostgreSQL performance issues with timeouts"
```

**Returns:**
- Tickets with similar PostgreSQL problems
- Successful resolution patterns
- Relevant tags and expertise required

### 2. FDE Profiles Knowledge Base
**S3 Location:** `s3://genai-enablement-team3/certificates/`
**Purpose:** Field Development Engineer expertise profiles
**Contents:**
- FDE names and contact info
- Slack IDs
- Technical expertise areas
- Certifications
- Past ticket history
- Success rates

**Search Query Example:**
```
"PostgreSQL, performance tuning, database optimization"
```

**Returns:**
- FDEs with matching expertise
- Confidence scores based on experience
- Relevant certifications

---

## Testing the Hybrid Workflow

### Step 1: Deploy Without API Keys

Follow the deployment guide but use placeholder values in `terraform.tfvars`:

```hcl
zendesk_domain    = "yourcompany.zendesk.com"
zendesk_email     = "your-email@example.com"
zendesk_api_token = "placeholder-token"

slack_bot_token = "xoxb-placeholder-token"
slack_team_url  = "https://yourteam.slack.com"
```

### Step 2: Test Description-Only Mode

Open the Streamlit app and enter:
```
Customer experiencing PostgreSQL performance issues with slow queries
```

**Expected Result:**
- Agent searches Knowledge Bases
- Returns Top 3 FDEs with expertise reasoning
- No Slack/Zendesk links (expected)

### Step 3: Test Ticket ID with Fallback

Enter:
```
Find FDEs for ticket 12345
```

**Expected Result:**
- Agent tries to fetch ticket (will fail with placeholder credentials)
- Agent gracefully falls back to using the description "Find FDEs for ticket 12345"
- Searches Knowledge Bases
- Returns Top 3 FDEs with expertise reasoning

### Step 4: Add Real API Keys (Future)

When you get real API keys:
1. Update `terraform.tfvars` with real values
2. Run `terraform apply`
3. No code changes needed
4. System automatically uses full workflow

---

## Implementation Details

### Updated Files

1. **frontend/app.py** (Streamlit UI)
   - Added support for ticket_description parameter
   - Sends both ticket_id and description to API
   - Updated UI messaging to explain hybrid mode

2. **lambdas/orchestration/handler.py** (Orchestrator Lambda)
   - Accepts both `ticket_id` and `ticket_description`
   - Builds different agent prompts based on input
   - Handles three workflow modes

3. **Bedrock Agent Instructions**
   - Updated to support hybrid workflow
   - Graceful error handling for failed API calls
   - Mode-aware processing

### No Changes Needed For

- ✅ Lambda action groups (zendesk/slack) - keep as-is
- ✅ Knowledge Bases - already functional
- ✅ Terraform infrastructure - no changes
- ✅ API Gateway - accepts new parameters

---

## Example API Requests

### Mode 1: Ticket ID Only
```json
POST /find-fde
{
  "ticket_id": "12345"
}
```

### Mode 2: Ticket ID + Description (Fallback Support)
```json
POST /find-fde
{
  "ticket_id": "12345",
  "ticket_description": "Customer experiencing PostgreSQL performance issues"
}
```

### Mode 3: Description Only
```json
POST /find-fde
{
  "ticket_description": "Customer experiencing PostgreSQL performance issues with slow queries and timeouts on production database"
}
```

---

## Monitoring and Debugging

### CloudWatch Logs

**Orchestrator Lambda:**
```
Processing - ticket_id: 12345, has_description: True
Agent input: Find FDEs for Zendesk ticket 12345...
```

**Bedrock Agent:**
- Check agent invocation logs
- Look for fetchTicket failures (expected without API keys)
- Verify Knowledge Base searches succeed
- Confirm FDE recommendations returned

### Expected Errors (Normal Behavior)

When running without API keys, you'll see these errors in logs (this is expected):
```
ERROR: fetchTicket Lambda failed: 401 Unauthorized
INFO: Falling back to description-based workflow
INFO: Searching Knowledge Bases...
INFO: Returning 3 FDE recommendations
```

---

## Migration Path

### Phase 1: Current (No API Keys)
- Deploy with placeholder credentials
- Test description-only workflow
- Validate Knowledge Base quality
- Demo to stakeholders

### Phase 2: Add Zendesk API (Future)
- Obtain Zendesk API token
- Update terraform.tfvars
- Run terraform apply
- Test ticket ID → fetchTicket → recommendations

### Phase 3: Add Slack Integration (Future)
- Configure Slack bot
- Update terraform.tfvars
- Run terraform apply
- Test full workflow with Slack channel creation

---

## FAQ

**Q: Do I need Zendesk/Slack API keys to test?**
A: No! The system works with descriptions only.

**Q: What happens if I provide a ticket ID without API keys?**
A: The system tries to fetch, fails gracefully, then uses the description you provided.

**Q: Are the Knowledge Bases required?**
A: Yes! They contain the historical data needed for FDE recommendations.

**Q: Can I use this in production without API keys?**
A: Yes, if users are willing to provide descriptions instead of ticket IDs.

**Q: How do I add API keys later?**
A: Just update `terraform.tfvars` and run `terraform apply`. No code changes needed.

**Q: Does the fallback logic work automatically?**
A: Yes! The Bedrock Agent detects failures and switches modes automatically.

---

## Next Steps

1. ✅ Deploy the system with placeholder credentials
2. ✅ Test with ticket descriptions
3. ✅ Validate FDE recommendations quality
4. ✅ Review Knowledge Base search results
5. ⏳ Obtain real API credentials (when ready)
6. ⏳ Update terraform.tfvars and redeploy
7. ⏳ Test full workflow with Zendesk/Slack integration

---

## Support

For issues:
- Check CloudWatch logs for errors
- Verify Knowledge Bases show "Available" status
- Ensure Bedrock Agent is "Prepared"
- Test agent in Bedrock console test panel
- Review [BEDROCK_AGENT_INSTRUCTIONS.md](./BEDROCK_AGENT_INSTRUCTIONS.md) for agent configuration