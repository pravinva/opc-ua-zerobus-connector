"""Minimal Flask app for testing Databricks Apps deployment."""

from flask import Flask
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)


@app.route('/')
def home():
    """Simple HTML response."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>OT Simulator - Test</title>
    </head>
    <body>
        <h1>OT Simulator Test App (Flask)</h1>
        <p>If you can see this, the app is working!</p>
        <p>Port 8080 is responding correctly.</p>
    </body>
    </html>
    """
    return html


@app.route('/health')
def health():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == '__main__':
    logger.info("Starting minimal Flask test app on port 8000...")
    app.run(host='0.0.0.0', port=8000, debug=False)
