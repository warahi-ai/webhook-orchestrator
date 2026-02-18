# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Flask webhook orchestrator that listens for Jira status-change webhooks and automatically creates GitHub issues tagged for Claude Code to implement. When a Jira ticket moves to a configurable trigger status (default: "In Progress"), it creates a formatted GitHub issue with `@claude` mention, which triggers a GitHub Action for automated implementation. When Claude opens a PR, a separate workflow (`jira-pr-sync.yml` in the automated-workflows repo) transitions the Jira ticket to "Review" and adds a PR link comment, closing the loop.

## Commands

```bash
# Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.template .env  # then fill in actual values

# Run
python app.py  # starts Flask on PORT (default 5000)

# Local development tunnel
ngrok http 5000
```

There is no test suite or linter configured.

## Architecture

**Request flow:** Jira webhook → `app.py` (Flask) → `webhook_handler.py` (orchestrator) → GitHub issue → Claude Code Action → PR → `jira-pr-sync.yml` (in automated-workflows repo) → Jira ticket transitioned to Review with PR link comment

Four modules behind the Flask entry point:

- **`webhook_handler.py`** — `WebhookHandler` class orchestrates the full pipeline: signature verification → status change detection → ticket info extraction → duplicate check → GitHub issue creation. Returns HTTP status codes (200/400/403/500) with JSON responses.
- **`signature_verifier.py`** — HMAC SHA256 validation of `X-Hub-Signature` header using timing-safe comparison.
- **`jira_parser.py`** — Parses Jira webhook payloads. Handles Atlassian Document Format (ADF) to Markdown conversion. Extracts "Claude Effort" (low/medium/high) from a custom field, with auto-detection fallback if `JIRA_EFFORT_FIELD_ID` is not set.
- **`github_client.py`** — `GitHubClient` class wraps GitHub REST API. Creates issues with formatted body containing Jira link, description, acceptance criteria, and `@claude` instructions. Searches existing issues to prevent duplicates. Generates branch names as `feature/{JIRA-KEY}-{kebab-case-summary}`.

## Environment Variables

Configured via `.env` (see `.env.template`). Key variables: `GITHUB_TOKEN`, `GITHUB_REPO` (owner/repo format), `JIRA_WEBHOOK_SECRET`, `JIRA_TRIGGER_STATUS`, `JIRA_BASE_URL`, `JIRA_EFFORT_FIELD_ID` (optional).

## Git Workflow

Development happens on the `develop` branch. Feature branches use the naming convention `feature/{JIRA-KEY}-{kebab-case-summary}`. PRs target `develop`.
