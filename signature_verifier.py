"""
Jira webhook signature verification using HMAC SHA256.
"""
import hmac
import hashlib
import logging

logger = logging.getLogger(__name__)


def verify_signature(payload_body: bytes, signature_header: str, secret: str) -> bool:
    """
    Verify the HMAC SHA256 signature from Jira webhook.

    Args:
        payload_body: Raw request body as bytes
        signature_header: Value from X-Hub-Signature header
        secret: Jira webhook secret

    Returns:
        True if signature is valid, False otherwise
    """
    if not signature_header:
        logger.warning("Missing X-Hub-Signature header")
        return False

    if not secret:
        logger.error("JIRA_WEBHOOK_SECRET not configured")
        return False

    # Jira uses format: sha256=<hash>
    if not signature_header.startswith('sha256='):
        logger.warning(f"Invalid signature format: {signature_header[:20]}...")
        return False

    # Extract the hash part
    provided_signature = signature_header[7:]  # Remove 'sha256=' prefix

    # Compute expected signature
    expected_signature = hmac.new(
        secret.encode('utf-8'),
        payload_body,
        hashlib.sha256
    ).hexdigest()

    # Timing-safe comparison to prevent timing attacks
    is_valid = hmac.compare_digest(expected_signature, provided_signature)

    if not is_valid:
        logger.warning("Signature verification failed")

    return is_valid
