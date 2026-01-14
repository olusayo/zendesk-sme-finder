"""
Zendesk Action Group Lambda

This Lambda function serves as an Action Group for Bedrock Agent.
It handles two API paths:
1. /fetch-ticket - Fetch ticket details from Zendesk
2. /update-ticket - Update Zendesk ticket with FDE recommendations
"""

import json
import os
import boto3
from typing import Dict, Any
import logging
import requests
from requests.auth import HTTPBasicAuth

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Zendesk configuration
secrets_client = boto3.client('secretsmanager')


def get_zendesk_credentials() -> Dict[str, str]:
    """Fetch Zendesk credentials from Secrets Manager"""
    secret_name = os.environ.get('ZENDESK_SECRET_NAME', 'zendesk/api-credentials')

    try:
        response = secrets_client.get_secret_value(SecretId=secret_name)
        secret = json.loads(response['SecretString'])
        return secret
    except Exception as e:
        logger.error(f"Error fetching Zendesk credentials: {str(e)}")
        raise


def fetch_ticket(ticket_id: str) -> Dict[str, Any]:
    """
    Fetch ticket details from Zendesk API.

    Returns ticket information including:
    - Ticket ID, subject, description
    - Priority, status, tags
    - Assigned engineer (requester and assignee details)
    - Created/updated timestamps
    """
    logger.info(f"Fetching ticket {ticket_id} from Zendesk")

    try:
        # Get Zendesk credentials
        creds = get_zendesk_credentials()
        domain = creds['domain']
        email = creds['email']
        api_token = creds['api_token']

        # Fetch ticket
        url = f"https://{domain}/api/v2/tickets/{ticket_id}.json"
        response = requests.get(
            url,
            auth=HTTPBasicAuth(f"{email}/token", api_token),
            headers={'Content-Type': 'application/json'}
        )
        response.raise_for_status()

        ticket_data = response.json()['ticket']

        # Fetch assignee details if assigned
        assigned_engineer = None
        if ticket_data.get('assignee_id'):
            user_url = f"https://{domain}/api/v2/users/{ticket_data['assignee_id']}.json"
            user_response = requests.get(
                user_url,
                auth=HTTPBasicAuth(f"{email}/token", api_token)
            )
            if user_response.status_code == 200:
                user_data = user_response.json()['user']
                assigned_engineer = {
                    'id': user_data['id'],
                    'name': user_data['name'],
                    'email': user_data['email'],
                    'slack_id': user_data.get('user_fields', {}).get('slack_id', '')
                }

        # Format response
        result = {
            'ticket_id': str(ticket_data['id']),
            'subject': ticket_data.get('subject', ''),
            'description': ticket_data.get('description', ''),
            'priority': ticket_data.get('priority', 'normal'),
            'status': ticket_data.get('status', ''),
            'tags': ticket_data.get('tags', []),
            'created_at': ticket_data.get('created_at', ''),
            'updated_at': ticket_data.get('updated_at', ''),
            'assigned_engineer': assigned_engineer
        }

        logger.info(f"Successfully fetched ticket {ticket_id}")
        return result

    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error fetching ticket: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error fetching ticket: {str(e)}")
        raise


def update_ticket(ticket_id: str, slack_url: str, recommended_fdes: list) -> Dict[str, Any]:
    """
    Update Zendesk ticket with FDE recommendations and Slack link.

    Adds an internal comment with:
    - Recommended FDEs
    - Slack conversation link
    - Timestamp
    """
    logger.info(f"Updating ticket {ticket_id} in Zendesk")

    try:
        # Get Zendesk credentials
        creds = get_zendesk_credentials()
        domain = creds['domain']
        email = creds['email']
        api_token = creds['api_token']

        # Format FDE list
        fde_list = "\n".join([
            f"- {fde['name']} ({fde['email']}) - {int(fde.get('confidence', 0) * 100)}% match"
            for fde in recommended_fdes
        ])

        # Create comment
        comment_body = f"""
FDE Recommendations (AI-Generated):

{fde_list}

Slack Conversation: {slack_url}

The assigned engineer and recommended FDEs have been added to a Slack conversation for collaboration.
"""

        # Update ticket
        url = f"https://{domain}/api/v2/tickets/{ticket_id}.json"
        payload = {
            'ticket': {
                'comment': {
                    'body': comment_body,
                    'public': False  # Internal comment
                }
            }
        }

        response = requests.put(
            url,
            auth=HTTPBasicAuth(f"{email}/token", api_token),
            headers={'Content-Type': 'application/json'},
            json=payload
        )
        response.raise_for_status()

        logger.info(f"Successfully updated ticket {ticket_id}")

        return {
            'ticket_id': ticket_id,
            'updated': True,
            'zendesk_url': f"https://{domain}/agent/tickets/{ticket_id}"
        }

    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error updating ticket: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error updating ticket: {str(e)}")
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
        "actionGroup": "zendesk-operations",
        "apiPath": "/fetch-ticket" or "/update-ticket",
        "httpMethod": "POST",
        "parameters": [
            {"name": "ticket_id", "type": "string", "value": "12345"},
            ...
        ]
    }
    """
    logger.info(f"Received event: {json.dumps(event)}")

    try:
        # Extract action details
        api_path = event['apiPath']
        parameters = {p['name']: p['value'] for p in event.get('parameters', [])}

        logger.info(f"API Path: {api_path}, Parameters: {parameters}")

        # Route to appropriate function
        if api_path == '/fetch-ticket':
            ticket_id = parameters.get('ticket_id')
            if not ticket_id:
                raise ValueError("Missing ticket_id parameter")

            result = fetch_ticket(ticket_id)

        elif api_path == '/update-ticket':
            ticket_id = parameters.get('ticket_id')
            slack_url = parameters.get('slack_url')
            recommended_fdes_json = parameters.get('recommended_fdes')

            if not all([ticket_id, slack_url, recommended_fdes_json]):
                raise ValueError("Missing required parameters")

            recommended_fdes = json.loads(recommended_fdes_json)
            result = update_ticket(ticket_id, slack_url, recommended_fdes)

        else:
            raise ValueError(f"Unknown API path: {api_path}")

        # Return response in Bedrock Agent format
        return {
            'messageVersion': '1.0',
            'response': {
                'actionGroup': event['actionGroup'],
                'apiPath': api_path,
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
                'actionGroup': event.get('actionGroup', 'zendesk-operations'),
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
