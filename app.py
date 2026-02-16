"""
Flask application for Jira webhook orchestration.
"""
import os
import logging
from flask import Flask, request, jsonify
from dotenv import load_dotenv

from webhook_handler import WebhookHandler

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('webhook_orchestrator.log')
    ]
)

logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Initialize webhook handler
try:
    webhook_handler = WebhookHandler()
    logger.info("Webhook handler initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize webhook handler: {e}")
    raise


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({'status': 'healthy'}), 200


@app.route('/webhook', methods=['POST'])
def webhook():
    """
    Endpoint for receiving Jira webhooks.
    """
    # Log incoming request
    logger.info(f"Received webhook from {request.remote_addr}")

    # Get signature header
    signature = request.headers.get('X-Hub-Signature', '')

    # Get raw body for signature verification
    raw_body = request.get_data()

    # Parse JSON payload
    try:
        payload = request.get_json()
        if payload is None:
            logger.error("Request body is not valid JSON")
            return jsonify({'error': 'Invalid JSON'}), 400
    except Exception as e:
        logger.error(f"Error parsing JSON: {e}")
        return jsonify({'error': 'Malformed JSON'}), 400

    # Process the webhook
    try:
        status_code, response = webhook_handler.process_webhook(
            payload,
            signature,
            raw_body
        )
        return jsonify(response), status_code
    except Exception as e:
        logger.error(f"Unexpected error processing webhook: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    logger.error(f"Internal server error: {error}")
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('DEBUG', 'False').lower() == 'true'

    logger.info(f"Starting Flask server on port {port}")
    logger.info(f"Debug mode: {debug}")

    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )
