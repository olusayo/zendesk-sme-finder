"""
Zendesk API client for fetching ticket data.

This module provides a clean interface to the Zendesk API with
proper error handling, retries, and rate limiting.
"""

import requests
from typing import Dict, Any, Optional, List
from time import sleep

import sys
sys.path.insert(0, '/opt/python')

from logging_config import StructuredLogger
from constants import ZENDESK_DOMAIN, ZENDESK_EMAIL, ZENDESK_API_TOKEN

logger = StructuredLogger(__name__)


class ZendeskClient:
    """
    Zendesk API client with retry logic and rate limiting.

    Usage:
        client = ZendeskClient()
        ticket = client.get_ticket_with_context(ticket_id=12345)
    """

    def __init__(self):
        """Initialize Zendesk client with credentials."""
        self.domain = ZENDESK_DOMAIN
        self.email = ZENDESK_EMAIL
        self.api_token = ZENDESK_API_TOKEN
        self.base_url = f"https://{self.domain}/api/v2"
        self.session = requests.Session()
        self.session.auth = (f"{self.email}/token", self.api_token)
        self.session.headers.update({"Content-Type": "application/json"})

    def get_ticket_with_context(self, ticket_id: str) -> Dict[str, Any]:
        """
        Fetch full ticket context including comments and metadata.

        Args:
            ticket_id: Zendesk ticket ID

        Returns:
            Dict containing ticket data, comments, requester info, tags, etc.

        Raises:
            requests.exceptions.RequestException: If API call fails
        """
        logger.info(f"Fetching ticket {ticket_id} from Zendesk")

        # Fetch main ticket data
        ticket = self._get_ticket(ticket_id)

        # Fetch ticket comments
        comments = self._get_ticket_comments(ticket_id)

        # Fetch requester details
        requester_id = ticket.get("requester_id")
        requester = self._get_user(requester_id) if requester_id else {}

        # Fetch assignee details (current CRE)
        assignee_id = ticket.get("assignee_id")
        assignee = self._get_user(assignee_id) if assignee_id else {}

        # Construct full context
        ticket_context = {
            "id": ticket.get("id"),
            "subject": ticket.get("subject"),
            "description": ticket.get("description"),
            "status": ticket.get("status"),
            "priority": ticket.get("priority"),
            "tags": ticket.get("tags", []),
            "created_at": ticket.get("created_at"),
            "updated_at": ticket.get("updated_at"),
            "requester": {
                "id": requester.get("id"),
                "name": requester.get("name"),
                "email": requester.get("email"),
                "organization_id": requester.get("organization_id")
            },
            "assignee": {
                "id": assignee.get("id"),
                "name": assignee.get("name"),
                "email": assignee.get("email")
            },
            "comments": [
                {
                    "id": comment.get("id"),
                    "author_id": comment.get("author_id"),
                    "body": comment.get("body"),
                    "created_at": comment.get("created_at"),
                    "public": comment.get("public")
                }
                for comment in comments
            ],
            "custom_fields": ticket.get("custom_fields", []),
            "raw_ticket": ticket  # Keep full ticket for reference
        }

        logger.info(
            f"Successfully fetched ticket {ticket_id}",
            extra={
                "ticket_id": ticket_id,
                "num_comments": len(comments),
                "priority": ticket.get("priority")
            }
        )

        return ticket_context

    def _get_ticket(self, ticket_id: str) -> Dict[str, Any]:
        """
        Fetch ticket data from Zendesk API.

        Args:
            ticket_id: Zendesk ticket ID

        Returns:
            Ticket data dict
        """
        url = f"{self.base_url}/tickets/{ticket_id}.json"
        response = self._make_request("GET", url)
        return response.get("ticket", {})

    def _get_ticket_comments(self, ticket_id: str) -> List[Dict[str, Any]]:
        """
        Fetch all comments for a ticket.

        Args:
            ticket_id: Zendesk ticket ID

        Returns:
            List of comment dicts
        """
        url = f"{self.base_url}/tickets/{ticket_id}/comments.json"
        response = self._make_request("GET", url)
        return response.get("comments", [])

    def _get_user(self, user_id: str) -> Dict[str, Any]:
        """
        Fetch user details from Zendesk.

        Args:
            user_id: Zendesk user ID

        Returns:
            User data dict
        """
        url = f"{self.base_url}/users/{user_id}.json"
        response = self._make_request("GET", url)
        return response.get("user", {})

    def _make_request(
        self,
        method: str,
        url: str,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Make HTTP request to Zendesk API with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Full URL to request
            max_retries: Maximum number of retry attempts

        Returns:
            Response JSON data

        Raises:
            requests.exceptions.RequestException: If all retries fail
        """
        for attempt in range(max_retries):
            try:
                response = self.session.request(method, url)

                # Handle rate limiting
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    logger.warning(
                        f"Zendesk rate limit hit, retrying after {retry_after}s",
                        extra={"retry_after": retry_after, "attempt": attempt + 1}
                    )
                    sleep(retry_after)
                    continue

                # Raise for other errors
                response.raise_for_status()

                return response.json()

            except requests.exceptions.RequestException as e:
                logger.warning(
                    f"Zendesk API request failed (attempt {attempt + 1}/{max_retries})",
                    extra={
                        "url": url,
                        "error": str(e),
                        "attempt": attempt + 1
                    }
                )

                if attempt == max_retries - 1:
                    logger.error(f"All Zendesk API retries exhausted for {url}")
                    raise

                # Exponential backoff
                sleep(2 ** attempt)

        raise requests.exceptions.RequestException("Max retries exceeded")
