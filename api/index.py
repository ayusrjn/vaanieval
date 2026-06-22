"""ASGI handler for Vercel serverless functions."""

import sys
import os

# Add both paths to support different import styles
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
backend_dir = os.path.join(project_root, 'backend')

# Add paths in order: backend first (for app.* imports), then project root (for backend.* imports)
sys.path.insert(0, backend_dir)
sys.path.insert(0, project_root)

from app.main import app

__all__ = ["app"]
