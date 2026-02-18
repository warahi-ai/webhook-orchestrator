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

- **Python 3.8 or higher**
- **GitHub Account** with:
  - Personal access token with `repo` scope
  - Claude Code GitHub Action installed on your target repository
- **Jira Account** with:
  - Admin access to configure webhooks
  - A Jira project (e.g., AWF)
- **ngrok Account** (free tier works):
  - Sign up at https://dashboard.ngrok.com/signup
  - Required for local development to expose your server to the internet

## Setup

### 1. Clone and Install Dependencies

```bash
cd webhook-orchestrator

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create your `.env` file from the template:

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

#### Getting a GitHub Token:

1. Go to https://github.com/settings/tokens
2. Click **"Generate new token (classic)"**
3. Give it a descriptive name (e.g., "Webhook Orchestrator")
4. Select scope: **`repo`** (Full control of private repositories)
5. Click **"Generate token"**
6. **Copy the token immediately** (you won't see it again!)
7. Paste it in your `.env` file as `GITHUB_TOKEN`

#### Jira Webhook Secret:

**Note:** You'll get this secret when creating the Jira webhook in Step 5. Jira can auto-generate it for you, or you can provide your own.

If you want to generate your own secret beforehand:
```bash
# macOS/Linux:
openssl rand -hex 32
```

Either way, you'll need to copy the secret from Jira and paste it into your `.env` file as `JIRA_WEBHOOK_SECRET`.

### 3. Run the Flask Server

```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Start the server
python app.py
```

You should see:
```
✓ Webhook handler initialized successfully
✓ Starting Flask server on port 5000
✓ Running on http://127.0.0.1:5000
```

Keep this terminal open and running.

### 4. Install and Configure ngrok

#### Install ngrok (macOS):

```bash
brew install ngrok
```

For other platforms, see: https://ngrok.com/download

#### Authenticate ngrok:

1. Sign up for a free ngrok account: https://dashboard.ngrok.com/signup
2. Get your authtoken: https://dashboard.ngrok.com/get-started/your-authtoken
3. Configure ngrok with your authtoken:
   ```bash
   ngrok config add-authtoken YOUR_AUTHTOKEN_HERE
   ```

This is a **one-time setup** - ngrok will remember your token.

#### Start ngrok tunnel:

In a **new terminal** (keep the Flask server running):

```bash
# If you have a static domain (free tier includes one):
ngrok http --url=your-static-domain.ngrok-free.dev 5000

# Or without a static domain (URL changes on every restart):
ngrok http 5000
```

**Tip:** ngrok's free tier includes one static domain. Find yours at https://dashboard.ngrok.com/domains. Using a static domain means you **don't need to update the Jira webhook URL** every time you restart ngrok.

Keep this terminal open and running.

## 5. Configure Jira Webhook

### Setting up the Webhook

1. **Go to Jira Webhook Settings:**
   - Direct URL: https://warahi.atlassian.net/plugins/servlet/webhooks
   - Or: Jira Settings (⚙️) → System → WebHooks

2. **Click "Create a WebHook"**

3. **Configure the webhook with these settings:**

   | Field | Value |
   |-------|-------|
   | **Name** | `Notify Claude` or `GitHub Issue Creator` |
   | **Status** | ✅ Enabled |
   | **URL** | Your ngrok URL + `/webhook`<br>Example: `https://abc123-xyz.ngrok-free.dev/webhook` |
   | **Description** | `Automatically creates GitHub issues when tickets move to In Progress` |
   | **Events** | ✅ Issue updated |
   | **JQL** | `project = "AWF"` (replace AWF with your project key) |
   | **Secret** | Click "Generate" to auto-generate, or paste your own |
   | **Exclude body** | No |

4. **Copy the secret** - After creating the webhook:
   - If you clicked "Generate", Jira will display the secret
   - Copy this secret and add it to your `.env` file as `JIRA_WEBHOOK_SECRET`
   - **Important:** Save it now - you may not be able to view it again!

5. **Click "Create"** to save the webhook

6. **Verify the webhook is enabled** (green toggle on the webhooks page)

### Testing the Integration

Now let's test the complete flow:

1. **Go to your Jira board:**
   - Example: https://warahi.atlassian.net/jira/software/c/projects/AWF/boards

2. **Create a test ticket** (or use an existing one)

3. **Drag the ticket to "In Progress" column**

4. **Check the Flask server terminal** - you should see:
   ```
   ✓ Received webhook from 127.0.0.1
   ✓ Webhook signature verified
   ✓ Status change detected: To Do → In Progress
   ✓ Trigger status 'In Progress' detected!
   ✓ Extracted ticket info for AWF-5
   ✓ Creating GitHub issue for AWF-5
   ✓ Successfully created GitHub issue: https://github.com/...
   ```

5. **Check your GitHub repository** - you should see a new issue with `[AWF-X]` in the title

6. **Check GitHub Actions** - Claude Code Action should automatically start working on the issue

7. **Wait for Claude to finish** - it will create a branch, implement the feature, and open a PR to `develop`

### Common Issues During Testing

**Webhook not received:**
- Verify ngrok is still running (URLs expire if you restart ngrok)
- Check the webhook URL in Jira matches your current ngrok URL exactly
- Look for delivery failures in Jira webhook history

**Signature verification fails:**
- Ensure `JIRA_WEBHOOK_SECRET` in `.env` matches exactly what's in Jira webhook
- No extra spaces or line breaks

**GitHub issue not created:**
- Verify `GITHUB_TOKEN` has `repo` scope
- Check GitHub token hasn't expired
- Review Flask logs for detailed error messages

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
- Create a branch named `feature/AWF-4-add-user-authentication` from `develop`
- Implement the requirements described above
- Write comprehensive tests
- **Create a Pull Request targeting the `develop` branch**

This issue was automatically created from Jira ticket AWF-4.
```

**Note:** The `@claude` tag triggers the Claude Code GitHub Action, which will automatically:
1. Create a feature branch from `develop`
2. Implement the requirements
3. Write tests
4. Open a Pull Request targeting `develop`

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

## Important Notes

### Quick Start (Returning Users)

If you've already completed the initial setup and just want to get the server running:

**Terminal 1 - Flask server:**
```bash
cd webhook-orchestrator
source venv/bin/activate
python app.py
```

**Terminal 2 - ngrok tunnel:**
```bash
# With static domain (recommended - no need to update Jira webhook):
ngrok http --url=your-static-domain.ngrok-free.dev 5000

# Without static domain:
ngrok http 5000
```

### Shutting Down

**Stop the Flask server:** Press `Ctrl+C` in Terminal 1

**Deactivate the virtual environment:**
```bash
deactivate
```

**Stop ngrok:** Press `Ctrl+C` in Terminal 2

### Virtual Environment

The project uses a Python virtual environment to isolate dependencies:

```bash
# Activate (required before running the server)
source venv/bin/activate    # macOS/Linux
venv\Scripts\activate       # Windows

# Deactivate (when you're done working)
deactivate

# Recreate if something breaks
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### ngrok URL Changes

If you're **not** using a static domain, the ngrok URL changes every time you restart. When this happens:

1. Get your new ngrok URL: Check the ngrok terminal or visit http://localhost:4040
2. Update Jira webhook: Edit your webhook in Jira with the new URL
3. Test again: Move a ticket to verify it works

**Tip:** Use a static domain to avoid this. ngrok's free tier includes one — find yours at https://dashboard.ngrok.com/domains.

### Keeping Everything Running

You need **2 terminals** running simultaneously:

1. **Terminal 1:** Flask server (`source venv/bin/activate && python app.py`)
2. **Terminal 2:** ngrok tunnel (`ngrok http --url=your-domain.ngrok-free.dev 5000`)

If either the Flask server or ngrok stops, the webhook won't work.

## Production Deployment

For production use, deploy to a cloud service instead of using ngrok:

### Recommended Platforms:
- **Railway**: Easy deployment, free tier available
- **Heroku**: Classic choice, free tier available
- **AWS EC2/ECS**: More control, requires setup
- **Google Cloud Run**: Serverless, pay-per-use
- **DigitalOcean**: Simple VPS option

### Deployment Checklist:
- [ ] Set environment variables in your hosting platform
- [ ] Use a production WSGI server (gunicorn, waitress)
- [ ] Enable HTTPS (required for webhooks)
- [ ] Update Jira webhook URL to your production URL
- [ ] Set up logging/monitoring
- [ ] Consider using a database for tracking issue mappings

## Troubleshooting

### Webhook not received
- **Check ngrok is running:** Visit http://localhost:4040 to see ngrok status
- **Verify URL matches:** The URL in Jira must exactly match your ngrok URL + `/webhook`
- **Check Jira webhook logs:** Go to webhook settings → Click your webhook → View "Recent Deliveries"
- **Firewall issues:** Ensure your firewall allows incoming connections on port 5000

### Signature verification fails (403 Forbidden)
- **Secret mismatch:** Ensure `JIRA_WEBHOOK_SECRET` in `.env` matches Jira webhook secret exactly
- **Check for spaces:** No extra spaces or newlines in the secret
- **Restart Flask:** After changing `.env`, restart the Flask server

### GitHub issue not created (500 Error)
- **Token expired:** GitHub tokens can expire - generate a new one
- **Wrong scope:** Token must have `repo` scope (not just `public_repo`)
- **Repository access:** Ensure the token has access to your repository
- **Check logs:** Review Flask terminal for detailed error messages

### Claude Code Action doesn't trigger
- **Missing @claude tag:** Issue body must contain `@claude`
- **Action not installed:** Verify Claude Code GitHub Action is installed on your repo
- **Check Actions tab:** Go to GitHub repo → Actions tab to see if workflow ran

### Duplicate issues created
- The duplicate check searches for the Jira key in existing issues
- If issues are created very quickly, duplicates might slip through
- Close the duplicate and Claude will work on the first one

### ngrok "authentication failed" error
- You need to sign up for ngrok: https://dashboard.ngrok.com/signup
- Run: `ngrok config add-authtoken YOUR_TOKEN`
- Get your token from: https://dashboard.ngrok.com/get-started/your-authtoken

## Future Enhancements

- Bidirectional sync: Update Jira when PR is merged
- Support for multiple Jira projects
- Database to track Jira-GitHub issue mappings
- Dashboard to monitor webhook activity
- Configurable GitHub issue templates
- Rate limiting and IP whitelisting

## License

MIT
