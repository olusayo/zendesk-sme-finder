"""
Orchestration Lambda

This Lambda function supports hybrid workflow:
1. Receives ticket_id and/or ticket_description from API Gateway
2. If ticket_id provided: Try full workflow (fetch from Zendesk, create Slack)
3. If ticket_id fails (missing API keys): Fallback to description-based workflow
4. If only description provided: Use description-based workflow directly
5. Invokes Bedrock Agent to find FDEs using Knowledge Bases
6. Returns formatted JSON to API Gateway
"""

import json
import os
import boto3
from typing import Dict, Any
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize Bedrock Agent client
bedrock_agent_runtime = boto3.client('bedrock-agent-runtime')

# Configuration from environment variables
AGENT_ID = os.environ['BEDROCK_AGENT_ID']
AGENT_ALIAS_ID = os.environ['BEDROCK_AGENT_ALIAS_ID']


def parse_agent_response(response_stream) -> Dict[str, Any]:
    """
    Parse the streaming response from Bedrock Agent.

    The agent returns streaming chunks that need to be assembled.
    We extract the final result from the completion event.
    """
    import re

    result = {
        'recommended_fdes': [],
        'similar_tickets': [],
        'slack_conversation_url': '',
        'zendesk_url': ''
    }

    completion_text = ""

    try:
        # Process streaming events
        for event in response_stream:
            if 'chunk' in event:
                chunk = event['chunk']
                if 'bytes' in chunk:
                    completion_text += chunk['bytes'].decode('utf-8')

        logger.info(f"Agent completion text: {completion_text}")

        # Try to extract JSON first (preferred format)
        if completion_text:
            json_match = re.search(r'\{.*\}', completion_text, re.DOTALL)
            if json_match:
                try:
                    parsed_result = json.loads(json_match.group())
                    result.update(parsed_result)
                    return result
                except json.JSONDecodeError:
                    pass  # Fall through to markdown parsing

        # If no JSON found, parse markdown format
        # Extract FDEs from markdown format like:
        # **1. Joseph (joseph@doit.com) - Confidence: 0.95**
        # - **Expertise:** PostgreSQL, SQL Tuning, ...
        # - **Reasoning:** Joseph holds multiple...
        fde_pattern = r'\*\*(\d+)\.\s+([^(]+)\s*\(([^)]+)\)\s*-\s*Confidence:\s*([\d.]+)\*\*\s*\n\s*-\s*\*\*Expertise:\*\*([^\n]+)\n\s*-\s*\*\*Reasoning:\*\*([^\n]+(?:\n(?!\*\*\d+\.|\n\n)[^\n]+)*)'

        fde_matches = re.finditer(fde_pattern, completion_text, re.MULTILINE | re.DOTALL)

        for match in fde_matches:
            name = match.group(2).strip()
            email = match.group(3).strip()
            confidence = float(match.group(4).strip())
            expertise_str = match.group(5).strip()
            reasoning = match.group(6).strip()

            # Parse expertise list
            expertise = [e.strip() for e in expertise_str.split(',')]

            result['recommended_fdes'].append({
                'name': name,
                'email': email,
                'slack_id': '',  # Not included in this format
                'expertise': expertise,
                'confidence': confidence,
                'reasoning': reasoning
            })

        # Extract similar tickets section
        # Look for numbered items in "Similar Resolved Tickets" section
        similar_tickets_section = re.search(r'\*\*Similar Resolved Tickets:\*\*(.+?)(?=\n\n\n\n\n|\*\*Workflow Mode|\Z)', completion_text, re.DOTALL)
        if similar_tickets_section:
            similar_text = similar_tickets_section.group(1)
            # Pattern: 1. **Title** - Resolution details...
            ticket_pattern = r'(\d+)\.\s+\*\*([^\*]+)\*\*\s+-\s+([^\n]+(?:\n(?!\d+\.).[^\n]+)*)'
            ticket_matches = re.finditer(ticket_pattern, similar_text)

            for tmatch in ticket_matches:
                ticket_subject = tmatch.group(2).strip()
                ticket_resolution = tmatch.group(3).strip()

                result['similar_tickets'].append({
                    'ticket_id': 'N/A',
                    'subject': ticket_subject,
                    'resolution': ticket_resolution,
                    'similarity_score': 0.85  # Default score
                })

        # Extract workflow mode
        workflow_match = re.search(r'\*\*Workflow Mode\*\*:\s*([^\n]+)', completion_text)
        if workflow_match:
            result['workflow_mode'] = workflow_match.group(1).strip()

    except Exception as e:
        logger.error(f"Error parsing agent response: {str(e)}")
        logger.error(f"Completion text was: {completion_text}")

    return result


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for orchestration.

    Event structure from API Gateway:
    {
        "body": "{\"ticket_id\": \"12345\", \"ticket_description\": \"Customer experiencing PostgreSQL issues\"}",
        "headers": {...},
        "requestContext": {...}
    }

    Event structure from Lambda Function URL:
    {
        "ticket_id": "12345",
        "ticket_description": "Customer experiencing PostgreSQL issues"
    }

    Supports three modes:
    1. ticket_id only: Try full Zendesk/Slack workflow, fallback to description if fails
    2. ticket_id + ticket_description: Try full workflow, fallback to description
    3. ticket_description only: Use description-based workflow directly
    """
    logger.info(f"Received event: {json.dumps(event)}")

    try:
        # Parse request body - handle both API Gateway and Lambda Function URL formats
        if 'body' in event:
            # API Gateway format (body is JSON string)
            body = json.loads(event.get('body', '{}'))
        else:
            # Lambda Function URL format (direct JSON)
            body = event

        ticket_id = body.get('ticket_id')
        ticket_description = body.get('ticket_description')

        # Validate at least one is provided
        if not ticket_id and not ticket_description:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Missing ticket_id or ticket_description in request body'
                })
            }

        logger.info(f"Processing - ticket_id: {ticket_id}, has_description: {bool(ticket_description)}")

        # Generate unique session ID
        session_id = f"session-{ticket_id or 'desc'}-{context.aws_request_id}"

        # Build agent input text based on what's provided
        if ticket_id and not ticket_description:
            # Mode 1: Ticket ID only - try full workflow
            agent_input = f"Find FDEs for Zendesk ticket {ticket_id}. Fetch the ticket details, analyze requirements, search for similar resolved tickets, recommend 3 FDEs with expertise reasoning, create a Slack conversation, and update the Zendesk ticket."
        elif ticket_id and ticket_description:
            # Mode 2: Both provided - try full workflow with fallback context
            agent_input = f"Find FDEs for Zendesk ticket {ticket_id}. Description: {ticket_description}. Try to fetch ticket details from Zendesk. If that fails, use the provided description to search for similar tickets and recommend 3 FDEs with expertise reasoning based on the description."
        else:
            # Mode 3: Description only - skip Zendesk/Slack operations
            agent_input = f"Find FDEs based on this ticket description: {ticket_description}. Search for similar resolved tickets in the knowledge base and recommend 3 FDEs whose expertise best matches this issue. Provide reasoning for each recommendation. Do NOT attempt to fetch from Zendesk or create Slack conversations."

        # Invoke Bedrock Agent
        logger.info(f"Invoking Bedrock Agent (ID: {AGENT_ID}, Alias: {AGENT_ALIAS_ID})")
        logger.info(f"Agent input: {agent_input}")

        response = bedrock_agent_runtime.invoke_agent(
            agentId=AGENT_ID,
            agentAliasId=AGENT_ALIAS_ID,
            sessionId=session_id,
            inputText=agent_input
        )

        # Parse streaming response
        event_stream = response.get('completion', [])
        result = parse_agent_response(event_stream)

        # Add ticket_id to result if provided
        if ticket_id:
            result['ticket_id'] = ticket_id

        logger.info(f"Successfully processed request")
        logger.info(f"Result: {json.dumps(result)}")

        # Return success response
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(result)
        }

    except bedrock_agent_runtime.exceptions.ThrottlingException:
        logger.error("Bedrock Agent throttling exception")
        return {
            'statusCode': 429,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Service is busy. Please try again in a moment.'
            })
        }

    except bedrock_agent_runtime.exceptions.ValidationException as e:
        logger.error(f"Bedrock Agent validation error: {str(e)}")
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': f'Invalid request: {str(e)}'
            })
        }

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Internal server error. Please try again later.'
            })
        }
