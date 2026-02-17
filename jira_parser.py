"""
Jira webhook payload parsing utilities.
"""
import logging
from typing import Optional, Tuple, Dict, Any

logger = logging.getLogger(__name__)


def is_status_change_webhook(payload: Dict[str, Any]) -> bool:
    """
    Check if the webhook payload contains a status change.

    Args:
        payload: Jira webhook payload

    Returns:
        True if this is a status change webhook, False otherwise
    """
    changelog = payload.get('changelog', {})
    items = changelog.get('items', [])

    for item in items:
        if item.get('field') == 'status':
            return True

    return False


def parse_status_change(payload: Dict[str, Any]) -> Optional[Tuple[str, str]]:
    """
    Extract the old and new status from a Jira webhook payload.

    Args:
        payload: Jira webhook payload

    Returns:
        Tuple of (old_status, new_status) or None if no status change found
    """
    changelog = payload.get('changelog', {})
    items = changelog.get('items', [])

    for item in items:
        if item.get('field') == 'status':
            old_status = item.get('fromString', '')
            new_status = item.get('toString', '')
            logger.info(f"Status change detected: {old_status} → {new_status}")
            return (old_status, new_status)

    return None


def parse_description(description: Any) -> str:
    """
    Parse Jira description field, handling both plain text and ADF format.

    Args:
        description: Description field from Jira (can be string or ADF object)

    Returns:
        Plain text description
    """
    if description is None:
        return ""

    # If it's already a string, return it
    if isinstance(description, str):
        return description

    # If it's ADF (Atlassian Document Format), convert to plain text
    if isinstance(description, dict):
        try:
            return _adf_to_text(description)
        except Exception as e:
            logger.warning(f"Failed to parse ADF description: {e}")
            return str(description)

    return str(description)


def _adf_to_text(adf: Dict[str, Any]) -> str:
    """
    Convert Atlassian Document Format to plain text.

    Args:
        adf: ADF document structure

    Returns:
        Plain text representation
    """
    if not isinstance(adf, dict):
        return str(adf)

    # ADF structure: { "type": "doc", "content": [...] }
    content = adf.get('content', [])
    if not content:
        return ""

    text_parts = []
    for node in content:
        text_parts.append(_adf_node_to_text(node))

    return '\n\n'.join(filter(None, text_parts))


def _adf_node_to_text(node: Dict[str, Any]) -> str:
    """
    Convert a single ADF node to text.

    Args:
        node: ADF node

    Returns:
        Text representation of the node
    """
    if not isinstance(node, dict):
        return str(node)

    node_type = node.get('type', '')
    content = node.get('content', [])
    text = node.get('text', '')

    # Handle different node types
    if node_type == 'text':
        return text
    elif node_type == 'paragraph':
        parts = [_adf_node_to_text(child) for child in content]
        return ''.join(parts)
    elif node_type == 'heading':
        parts = [_adf_node_to_text(child) for child in content]
        level = node.get('attrs', {}).get('level', 1)
        heading_text = ''.join(parts)
        return f"{'#' * level} {heading_text}"
    elif node_type == 'bulletList' or node_type == 'orderedList':
        items = [_adf_node_to_text(child) for child in content]
        return '\n'.join(items)
    elif node_type == 'listItem':
        parts = [_adf_node_to_text(child) for child in content]
        return f"- {''.join(parts)}"
    elif node_type == 'codeBlock':
        parts = [_adf_node_to_text(child) for child in content]
        return f"```\n{''.join(parts)}\n```"
    elif content:
        # For other node types with content, recursively process children
        parts = [_adf_node_to_text(child) for child in content]
        return ''.join(parts)

    return text


def _extract_custom_select_value(field_value: Any) -> str:
    """
    Extract the value from a Jira custom select field.

    Select fields come as objects like: {"value": "high", "id": "10XXX"}
    """
    if isinstance(field_value, dict):
        return field_value.get('value', '')
    if isinstance(field_value, str):
        return field_value
    return ''


def extract_ticket_info(payload: Dict[str, Any]) -> Dict[str, str]:
    """
    Extract ticket information from Jira webhook payload.

    Args:
        payload: Jira webhook payload

    Returns:
        Dictionary with ticket key, summary, description, acceptance criteria,
        and claude_effort
    """
    issue = payload.get('issue', {})
    fields = issue.get('fields', {})

    ticket_info = {
        'key': issue.get('key', ''),
        'summary': fields.get('summary', ''),
        'description': parse_description(fields.get('description')),
    }

    # Try to extract acceptance criteria from custom field or description
    acceptance_criteria = ''
    for field_key, field_value in fields.items():
        if 'acceptance' in field_key.lower() or 'criteria' in field_key.lower():
            if field_value:
                acceptance_criteria = parse_description(field_value)
                break

    ticket_info['acceptance_criteria'] = acceptance_criteria

    # Extract Claude Effort from custom field
    # Supports: explicit field ID via env var, or auto-detect by scanning fields
    import os
    effort_field_id = os.getenv('JIRA_EFFORT_FIELD_ID', '')
    claude_effort = ''

    if effort_field_id and effort_field_id in fields:
        # Use explicit field ID from env var
        claude_effort = _extract_custom_select_value(fields[effort_field_id])
        logger.info(f"Claude effort from {effort_field_id}: {claude_effort}")
    else:
        # Auto-detect: scan custom fields for select values matching effort levels
        valid_efforts = {'low', 'medium', 'high'}
        for field_key, field_value in fields.items():
            if field_key.startswith('customfield_') and field_value:
                value = _extract_custom_select_value(field_value).lower()
                if value in valid_efforts:
                    claude_effort = value
                    logger.info(f"Claude effort auto-detected from {field_key}: {claude_effort}")
                    break

    ticket_info['claude_effort'] = claude_effort or 'medium'

    logger.info(f"Extracted ticket info for {ticket_info['key']} (effort: {ticket_info['claude_effort']})")
    return ticket_info
