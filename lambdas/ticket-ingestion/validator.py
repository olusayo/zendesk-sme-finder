"""
Ticket data validation module.

Validates ticket data structure and content before processing.
"""

from typing import Dict, Any, List

import sys
sys.path.insert(0, '/opt/python')

from constants import (
    MAX_TICKET_DESCRIPTION_LENGTH,
    MIN_TICKET_DESCRIPTION_LENGTH
)


def validate_ticket_data(ticket_data: Dict[str, Any]) -> List[str]:
    """
    Validate ticket data structure and content.

    Args:
        ticket_data: Ticket context dict from Zendesk

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    # Required fields
    required_fields = ["id", "subject", "description", "requester", "tags"]
    for field in required_fields:
        if field not in ticket_data or not ticket_data[field]:
            errors.append(f"Missing required field: {field}")

    # Validate ticket ID
    if "id" in ticket_data:
        ticket_id = ticket_data["id"]
        if not isinstance(ticket_id, (int, str)) or str(ticket_id).strip() == "":
            errors.append("Invalid ticket ID")

    # Validate description length
    if "description" in ticket_data:
        description = ticket_data["description"]
        if description:
            desc_length = len(description)
            if desc_length < MIN_TICKET_DESCRIPTION_LENGTH:
                errors.append(f"Description too short (min: {MIN_TICKET_DESCRIPTION_LENGTH} chars)")
            elif desc_length > MAX_TICKET_DESCRIPTION_LENGTH:
                errors.append(f"Description too long (max: {MAX_TICKET_DESCRIPTION_LENGTH} chars)")

    # Validate requester
    if "requester" in ticket_data:
        requester = ticket_data["requester"]
        if not isinstance(requester, dict):
            errors.append("Invalid requester format")
        elif "id" not in requester or not requester["id"]:
            errors.append("Missing requester ID")

    # Validate tags (must contain "need_sme" tag)
    if "tags" in ticket_data:
        tags = ticket_data["tags"]
        if not isinstance(tags, list):
            errors.append("Tags must be a list")
        elif "need_sme" not in tags:
            errors.append("Ticket does not have 'need_sme' tag")

    # Validate comments
    if "comments" in ticket_data:
        comments = ticket_data["comments"]
        if not isinstance(comments, list):
            errors.append("Comments must be a list")

    return errors
