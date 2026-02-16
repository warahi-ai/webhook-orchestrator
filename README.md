# Jira to GitHub Webhook Orchestrator

A Python Flask application that automatically creates GitHub issues from Jira tickets when they're moved to "In Progress" status. The GitHub issues are tagged with `@claude` to trigger the Claude Code GitHub Action for automated implementation.

## Overview

**The Flow:**
1. Developer drags a Jira ticket to "In Progress" column on the board
2. Jira fires a webhook to this Flask server
3. Server verifies the webhook signature
4. Server checks if the status changed to the trigger status (default: "In Progress")
5. Server creates a GitHub issue with the ticket details and `@claude` tag
6. Claude Code GitHub Action automatically picks up the issue and implements the feature

## Prerequisites

- Python 3.8 or higher
- GitHub personal access token with `repo` scope
- Jira webhook configured with a secret
- ngrok (for local development) or a deployed server

## Setup

### 1. Clone and Install Dependencies

```bash
cd webhook-orchestrator
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy the template and fill in your values:

```bash
cp .env.template .env
```

Edit `.env` with your actual values:

```env
# GitHub Configuration
GITHUB_TOKEN=ghp_your_github_personal_access_token
GITHUB_REPO=warahi-ai/automated-workflows

# Jira Configuration
JIRA_WEBHOOK_SECRET=your_jira_webhook_secret
JIRA_TRIGGER_STATUS=In Progress
JIRA_BASE_URL=https://warahi.atlassian.net

# Server Configuration
PORT=5000
```

**Getting a GitHub Token:**
1. Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Generate new token with `repo` scope
3. Copy the token to your `.env` file

**Jira Webhook Secret:**
- This is set when you configure the Jira webhook (see Jira Configuration section)

### 3. Run the Server

```bash
python app.py
```

The server will start on `http://0.0.0.0:5000` (or the port specified in `.env`).

### 4. Expose with ngrok (for local development)

In a separate terminal:

```bash
ngrok http 5000
```

Copy the HTTPS URL (e.g., `https://abc123.ngrok.io`) for the next step.

## Jira Configuration

### Setting up the Webhook

1. Go to your Jira project settings
2. Navigate to System → WebHooks → Create a WebHook
3. Configure the webhook:
   - **Name:** GitHub Issue Creator
   - **Status:** Enabled
   - **URL:** Your ngrok URL + `/webhook` (e.g., `https://abc123.ngrok.io/webhook`)
   - **Description:** Creates GitHub issues when tickets move to In Progress
   - **Issue related events:** Select "Issue updated"
   - **JQL:** `project = "AWF"` (or your project key)
   - **Secret:** Generate a random secret and save it to your `.env` as `JIRA_WEBHOOK_SECRET`

4. Save the webhook

### Testing the Webhook

1. In Jira, create a test ticket
2. Drag it to the "In Progress" column
3. Check the Flask server logs - you should see:
   ```
   Received webhook from <IP>
   Webhook signature verified
   Trigger status 'In Progress' detected!
   Successfully created GitHub issue: https://github.com/...
   ```
4. Check your GitHub repository for the new issue

## Architecture

### File Structure

```
webhook-orchestrator/
├── app.py                    # Flask application entry point
├── webhook_handler.py        # Main orchestration logic
├── jira_parser.py           # Jira payload parsing utilities
├── github_client.py         # GitHub API integration
├── signature_verifier.py    # HMAC signature verification
├── requirements.txt         # Python dependencies
├── .env.template           # Environment variable template
├── .gitignore              # Git ignore file
└── README.md               # This file
```

### Components

**signature_verifier.py**
- Verifies HMAC SHA256 signatures from Jira webhooks
- Uses timing-safe comparison to prevent timing attacks

**jira_parser.py**
- Parses Jira webhook payloads
- Handles Atlassian Document Format (ADF) conversion to plain text
- Extracts ticket key, summary, description, and acceptance criteria

**github_client.py**
- Interacts with GitHub REST API
- Creates formatted issues with `@claude` tag
- Checks for duplicate issues to prevent re-creation

**webhook_handler.py**
- Orchestrates the entire flow
- Verifies signatures, parses payloads, creates issues
- Handles all edge cases and error scenarios

**app.py**
- Flask web server
- Routes webhook requests to the handler
- Provides health check endpoint

## GitHub Issue Format

Issues created by this orchestrator follow this format:

**Title:** `[AWF-4] Add user authentication`

**Body:**
```markdown
## Jira Ticket
**Key:** AWF-4
**Link:** https://warahi.atlassian.net/browse/AWF-4

## Summary
Add user authentication

## Description
Implement OAuth 2.0 authentication for users...

## Acceptance Criteria
- Users can log in with Google
- Sessions persist for 30 days
- Logout functionality works correctly

---

@claude Please implement this feature following these guidelines:
- Create a branch named `feature/AWF-4-add-user-authentication`
- Implement the requirements described above
- Write comprehensive tests
- Open a PR when ready

This issue was automatically created from Jira ticket AWF-4.
```

## Edge Cases & Error Handling

The application handles these scenarios:

1. **Invalid Signature** - Returns 403 Forbidden
2. **Non-Status Change Webhooks** - Returns 200 OK, ignores the webhook
3. **Status Change to Wrong Column** - Returns 200 OK, ignores the webhook
4. **Duplicate GitHub Issue** - Returns 200 OK, doesn't create a duplicate
5. **GitHub API Failure** - Returns 500, logs detailed error
6. **Missing Required Fields** - Returns 400 Bad Request
7. **Malformed JSON** - Returns 400 Bad Request

## Logging

Logs are written to both:
- Console (stdout)
- `webhook_orchestrator.log` file

Log entries include:
- Incoming webhook requests
- Signature verification results
- Status changes detected
- GitHub issue creation attempts
- All errors with stack traces

## Security

- All webhook requests are verified using HMAC SHA256 signatures
- Credentials are stored in environment variables, never in code
- Timing-safe comparison prevents timing attacks
- HTTPS required for production (use ngrok HTTPS for local dev)

## Troubleshooting

### Webhook not received
- Check that ngrok is running and the URL matches the Jira webhook configuration
- Verify the webhook is enabled in Jira
- Check Jira webhook logs for delivery failures

### Signature verification fails
- Ensure `JIRA_WEBHOOK_SECRET` in `.env` matches the secret in Jira webhook configuration
- Check that Jira is sending the `X-Hub-Signature` header

### GitHub issue not created
- Verify `GITHUB_TOKEN` has `repo` scope
- Check that `GITHUB_REPO` is correct (format: `owner/repo`)
- Review logs for GitHub API errors

### Duplicate issues created
- The duplicate check searches for the Jira key in existing issues
- If issues are created very quickly, duplicates might slip through

## Future Enhancements

- Bidirectional sync: Update Jira when PR is merged
- Support for multiple Jira projects
- Database to track Jira-GitHub issue mappings
- Dashboard to monitor webhook activity
- Configurable GitHub issue templates
- Rate limiting and IP whitelisting

## License

MIT
