"""
Slack Action Group Lambda

This Lambda function serves as an Action Group for Bedrock Agent.
It handles the API path:
/create-conversation - Create Slack conversation with engineer and FDEs
"""

import json
import os
import boto3
from typing import Dict, Any, List
import logging
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Slack configuration
secrets_client = boto3.client('secretsmanager')


def get_slack_credentials() -> Dict[str, str]:
    """Fetch Slack credentials from Secrets Manager"""
    secret_name = os.environ.get('SLACK_SECRET_NAME', 'slack/bot-credentials')

    try:
        response = secrets_client.get_secret_value(SecretId=secret_name)
        secret = json.loads(response['SecretString'])
        return secret
    except Exception as e:
        logger.error(f"Error fetching Slack credentials: {str(e)}")
        raise


def create_conversation(
    ticket_id: str,
    engineer_slack_id: str,
    fde_slack_ids: List[str],
    ticket_subject: str,
    zendesk_url: str
) -> Dict[str, Any]:
    """
    Create a Slack conversation with the engineer and recommended FDEs.

    Steps:
    1. Create a new Slack channel
    2. Invite engineer and FDEs to the channel
    3. Post initial message with ticket details
    4. Return channel URL
    """
    logger.info(f"Creating Slack conversation for ticket {ticket_id}")

    try:
        # Get Slack credentials
        creds = get_slack_credentials()
        bot_token = creds['bot_token']

        # Initialize Slack client
        client = WebClient(token=bot_token)

        # Create channel name (Slack channel names must be lowercase, no spaces)
        channel_name = f"ticket-{ticket_id}".lower().replace(' ', '-')[:80]

        # Create private channel
        logger.info(f"Creating channel: {channel_name}")
        create_response = client.conversations_create(
            name=channel_name,
            is_private=False  # Set to True for private channels
        )

        channel_id = create_response['channel']['id']
        logger.info(f"Channel created: {channel_id}")

        # Invite engineer
        if engineer_slack_id:
            try:
                client.conversations_invite(
                    channel=channel_id,
                    users=engineer_slack_id
                )
                logger.info(f"Invited engineer: {engineer_slack_id}")
            except SlackApiError as e:
                logger.warning(f"Could not invite engineer {engineer_slack_id}: {e.response['error']}")

        # Invite FDEs
        for fde_id in fde_slack_ids:
            try:
                client.conversations_invite(
                    channel=channel_id,
                    users=fde_id
                )
                logger.info(f"Invited FDE: {fde_id}")
            except SlackApiError as e:
                logger.warning(f"Could not invite FDE {fde_id}: {e.response['error']}")

        # Post initial message
        fde_mentions = ' '.join([f"<@{fde_id}>" for fde_id in fde_slack_ids])

        message = f"""
:ticket: *New Support Ticket Needs FDE Assistance*

*Ticket:* <{zendesk_url}|#{ticket_id}>
*Subject:* {ticket_subject}

Hello <@{engineer_slack_id}>! The AI system has identified the following FDEs as best matches for this ticket:

{fde_mentions}

*Next Steps:*
1. Review the ticket details in Zendesk
2. FDEs: Please review and indicate if you can assist
3. Collaborate here to resolve the issue

The ticket has been updated with this Slack conversation link.
"""

        client.chat_postMessage(
            channel=channel_id,
            text=message,
            mrkdwn=True
        )

        logger.info(f"Posted initial message to channel {channel_id}")

        # Get channel permalink
        # Slack workspace URL format: https://{workspace}.slack.com/archives/{channel_id}
        workspace_info = client.auth_test()
        team_url = workspace_info['url']
        conversation_url = f"{team_url}archives/{channel_id}"

        result = {
            'conversation_url': conversation_url,
            'channel_id': channel_id,
            'channel_name': channel_name,
            'members_invited': [engineer_slack_id] + fde_slack_ids
        }

        logger.info(f"Successfully created conversation: {conversation_url}")
        return result

    except SlackApiError as e:
        logger.error(f"Slack API error: {e.response['error']}")
        raise
    except Exception as e:
        logger.error(f"Error creating conversation: {str(e)}")
        raise


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for Bedrock Agent Action Group.

    Event structure from Bedrock Agent:
    {
        "messageVersion": "1.0",
        "agent": {...},
        "sessionId": "...",
        "sessionAttributes": {...},
        "actionGroup": "slack-operations",
        "apiPath": "/create-conversation",
        "httpMethod": "POST",
        "parameters": [
            {"name": "ticket_id", "type": "string", "value": "12345"},
            {"name": "engineer_slack_id", "type": "string", "value": "U12345"},
            {"name": "fde_slack_ids", "type": "string", "value": "[\"U11111\", \"U22222\", \"U33333\"]"},
            {"name": "ticket_subject", "type": "string", "value": "PostgreSQL performance issue"},
            {"name": "zendesk_url", "type": "string", "value": "https://..."}
        ]
    }
    """
    logger.info(f"Received event: {json.dumps(event)}")

    try:
        # Extract parameters
        parameters = {p['name']: p['value'] for p in event.get('parameters', [])}

        logger.info(f"Parameters: {parameters}")

        # Parse required parameters
        ticket_id = parameters.get('ticket_id')
        engineer_slack_id = parameters.get('engineer_slack_id')
        fde_slack_ids_json = parameters.get('fde_slack_ids')
        ticket_subject = parameters.get('ticket_subject', 'Support Ticket')
        zendesk_url = parameters.get('zendesk_url', '')

        if not all([ticket_id, fde_slack_ids_json]):
            raise ValueError("Missing required parameters")

        # Parse FDE Slack IDs
        fde_slack_ids = json.loads(fde_slack_ids_json) if isinstance(fde_slack_ids_json, str) else fde_slack_ids_json

        # Create conversation
        result = create_conversation(
            ticket_id=ticket_id,
            engineer_slack_id=engineer_slack_id or '',
            fde_slack_ids=fde_slack_ids,
            ticket_subject=ticket_subject,
            zendesk_url=zendesk_url
        )

        # Return response in Bedrock Agent format
        return {
            'messageVersion': '1.0',
            'response': {
                'actionGroup': event['actionGroup'],
                'apiPath': event['apiPath'],
                'httpMethod': 'POST',
                'httpStatusCode': 200,
                'responseBody': {
                    'application/json': {
                        'body': json.dumps(result)
                    }
                }
            }
        }

    except Exception as e:
        logger.error(f"Error in action group: {str(e)}", exc_info=True)

        # Return error in Bedrock Agent format
        return {
            'messageVersion': '1.0',
            'response': {
                'actionGroup': event.get('actionGroup', 'slack-operations'),
                'apiPath': event.get('apiPath', ''),
                'httpMethod': 'POST',
                'httpStatusCode': 500,
                'responseBody': {
                    'application/json': {
                        'body': json.dumps({'error': str(e)})
                    }
                }
            }
        }
