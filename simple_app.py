"""Minimal aiohttp app for testing Databricks Apps deployment."""

from aiohttp import web
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def handle_root(request):
    """Simple HTML response."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>OT Simulator - Test</title>
    </head>
    <body>
        <h1>OT Simulator Test App</h1>
        <p>If you can see this, the app is working!</p>
        <p>Port 8080 is responding correctly.</p>
    </body>
    </html>
    """
    return web.Response(text=html, content_type='text/html')


async def handle_health(request):
    """Health check endpoint."""
    return web.json_response({"status": "healthy"})


def create_app():
    """Create the aiohttp application."""
    app = web.Application()
    app.router.add_get('/', handle_root)
    app.router.add_get('/health', handle_health)
    return app


if __name__ == '__main__':
    logger.info("Starting minimal test app on port 8080...")
    app = create_app()
    web.run_app(app, host='0.0.0.0', port=8080)
