"""ASGI handler for Vercel serverless functions."""

from app.main import app

# Vercel expects an async handler function
async def handler(request):
    """Handle incoming HTTP requests for Vercel."""
    return app
