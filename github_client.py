"""
GitHub API client for creating issues.
"""
import os
import logging
import requests
from typing import Dict, Optional
import re

logger = logging.getLogger(__name__)


class GitHubClient:
    """Client for interacting with GitHub API."""

    def __init__(self):
        self.token = os.getenv('GITHUB_TOKEN')
        self.repo = os.getenv('GITHUB_REPO')
        self.jira_base_url = os.getenv('JIRA_BASE_URL', 'https://warahi.atlassian.net')

        if not self.token:
            raise ValueError("GITHUB_TOKEN environment variable not set")
        if not self.repo:
            raise ValueError("GITHUB_REPO environment variable not set")

        self.api_base = "https://api.github.com"
        self.headers = {
            'Authorization': f'token {self.token}',
            'Accept': 'application/vnd.github.v3+json',
        }

    def issue_exists_for_ticket(self, jira_key: str) -> bool:
        """
        Check if a GitHub issue already exists for the given Jira ticket.

        Args:
            jira_key: Jira ticket key (e.g., "AWF-4")

        Returns:
            True if an issue exists, False otherwise
        """
        # Search for issues with the Jira key in title or body
        search_query = f'repo:{self.repo} {jira_key} in:title,body is:issue'
        search_url = f'{self.api_base}/search/issues'

        try:
            response = requests.get(
                search_url,
                headers=self.headers,
                params={'q': search_query}
            )
            response.raise_for_status()

            data = response.json()
            total_count = data.get('total_count', 0)

            if total_count > 0:
                logger.info(f"Found {total_count} existing issue(s) for {jira_key}")
                return True

            return False

        except requests.exceptions.RequestException as e:
            logger.error(f"Error checking for existing issue: {e}")
            # In case of error, assume it doesn't exist to avoid blocking
            return False

    def create_issue(self, ticket_info: Dict[str, str]) -> Optional[str]:
        """
        Create a GitHub issue from Jira ticket information.

        Args:
            ticket_info: Dictionary with keys: key, summary, description, acceptance_criteria

        Returns:
            GitHub issue URL if successful, None otherwise
        """
        jira_key = ticket_info.get('key', '')
        summary = ticket_info.get('summary', '')
        description = ticket_info.get('description', '')
        acceptance_criteria = ticket_info.get('acceptance_criteria', '')
        claude_effort = ticket_info.get('claude_effort', 'medium')

        # Map effort levels to Claude instructions
        effort_instructions = {
            'low': (
                "This is a **low effort** task. "
                "Keep the implementation simple and focused. "
                "Minimal exploration needed."
            ),
            'medium': (
                "This is a **medium effort** task. "
                "Implement thoroughly with proper error handling and tests."
            ),
            'high': (
                "This is a **high effort** task. "
                "Take a thorough approach: explore the codebase carefully, "
                "consider edge cases, write comprehensive tests, and ensure "
                "high-quality architecture."
            ),
        }

        effort_text = effort_instructions.get(claude_effort, effort_instructions['medium'])

        # Create kebab-case version of summary for branch naming
        kebab_summary = self._to_kebab_case(summary)

        # Format the issue title
        title = f"[{jira_key}] {summary}"

        # Format the issue body
        body_parts = [
            "## Jira Ticket",
            f"**Key:** {jira_key}",
            f"**Link:** {self.jira_base_url}/browse/{jira_key}",
            f"**Effort:** {claude_effort.capitalize()}",
            "",
            "## Summary",
            summary,
        ]

        if description:
            body_parts.extend([
                "",
                "## Description",
                description,
            ])

        if acceptance_criteria:
            body_parts.extend([
                "",
                "## Acceptance Criteria",
                acceptance_criteria,
            ])

        body_parts.extend([
            "",
            "---",
            "",
            f"@claude {effort_text}",
            "",
            "Please implement this feature following these guidelines:",
            f"- Create a branch named `feature/{jira_key}-{kebab_summary}` from `develop`",
            "- Implement the requirements described above",
            "- Write comprehensive tests",
            "- **Create a Pull Request targeting the `develop` branch**",
            "",
            f"This issue was automatically created from Jira ticket {jira_key}.",
        ])

        body = '\n'.join(body_parts)

        # Create the issue via GitHub API
        issues_url = f'{self.api_base}/repos/{self.repo}/issues'
        payload = {
            'title': title,
            'body': body,
        }

        try:
            logger.info(f"Creating GitHub issue for {jira_key}")
            response = requests.post(
                issues_url,
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()

            issue_data = response.json()
            issue_url = issue_data.get('html_url', '')

            logger.info(f"Successfully created GitHub issue: {issue_url}")
            return issue_url

        except requests.exceptions.RequestException as e:
            logger.error(f"Error creating GitHub issue: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            return None

    @staticmethod
    def _to_kebab_case(text: str) -> str:
        """
        Convert text to kebab-case for branch naming.

        Args:
            text: Input text

        Returns:
            Kebab-case version of the text
        """
        # Remove special characters and replace spaces with hyphens
        text = re.sub(r'[^\w\s-]', '', text)
        text = re.sub(r'[\s_]+', '-', text)
        text = text.strip('-').lower()
        # Limit length to keep branch names reasonable
        return text[:50]
