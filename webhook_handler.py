"""
Main webhook handling logic for Jira to GitHub orchestration.
"""
import os
import logging
from typing import Dict, Tuple

from signature_verifier import verify_signature
from jira_parser import (
    is_status_change_webhook,
    parse_status_change,
    extract_ticket_info
)
from github_client import GitHubClient

logger = logging.getLogger(__name__)


class WebhookHandler:
    """Handles incoming Jira webhooks and orchestrates GitHub issue creation."""

    def __init__(self):
        self.jira_secret = os.getenv('JIRA_WEBHOOK_SECRET')
        self.trigger_status = os.getenv('JIRA_TRIGGER_STATUS', 'In Progress')
        self.github_client = GitHubClient()

        if not self.jira_secret:
            raise ValueError("JIRA_WEBHOOK_SECRET environment variable not set")

    def process_webhook(
        self,
        payload: Dict,
        signature: str,
        raw_body: bytes
    ) -> Tuple[int, Dict[str, str]]:
        """
        Process an incoming Jira webhook.

        Args:
            payload: Parsed JSON payload
            signature: X-Hub-Signature header value
            raw_body: Raw request body as bytes

        Returns:
            Tuple of (status_code, response_dict)
        """
        # Step 1: Verify signature
        if not verify_signature(raw_body, signature, self.jira_secret):
            logger.warning("Webhook signature verification failed")
            return (403, {'error': 'Invalid signature'})

        logger.info("Webhook signature verified")

        # Step 2: Check if this is a status change webhook
        if not is_status_change_webhook(payload):
            logger.info("Webhook is not a status change, ignoring")
            return (200, {'message': 'Not a status change webhook'})

        # Step 3: Parse the status change
        status_change = parse_status_change(payload)
        if not status_change:
            logger.warning("Could not parse status change from webhook")
            return (200, {'message': 'No status change found'})

        old_status, new_status = status_change

        # Step 4: Check if the new status matches our trigger status
        if new_status != self.trigger_status:
            logger.info(
                f"Status changed to '{new_status}', but trigger status is "
                f"'{self.trigger_status}'. Ignoring."
            )
            return (200, {
                'message': f'Status change to {new_status} does not match trigger'
            })

        logger.info(f"Trigger status '{self.trigger_status}' detected!")

        # Step 5: Extract ticket information
        try:
            ticket_info = extract_ticket_info(payload)
        except Exception as e:
            logger.error(f"Error extracting ticket info: {e}")
            return (400, {'error': 'Failed to extract ticket information'})

        jira_key = ticket_info.get('key', '')
        if not jira_key:
            logger.error("No Jira key found in payload")
            return (400, {'error': 'No Jira key found'})

        # Step 6: Check for duplicate GitHub issue
        try:
            if self.github_client.issue_exists_for_ticket(jira_key):
                logger.info(f"GitHub issue already exists for {jira_key}, skipping")
                return (200, {
                    'message': f'GitHub issue already exists for {jira_key}'
                })
        except Exception as e:
            logger.error(f"Error checking for duplicate issue: {e}")
            # Continue anyway to avoid blocking on search errors

        # Step 7: Create GitHub issue
        try:
            issue_url = self.github_client.create_issue(ticket_info)
        except Exception as e:
            logger.error(f"Error creating GitHub issue: {e}", exc_info=True)
            return (500, {'error': 'Failed to create GitHub issue'})

        if not issue_url:
            return (500, {'error': 'Failed to create GitHub issue'})

        logger.info(f"Successfully created GitHub issue: {issue_url}")
        return (200, {
            'message': 'GitHub issue created successfully',
            'issue_url': issue_url,
            'jira_key': jira_key
        })
