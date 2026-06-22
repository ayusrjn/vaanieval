"""Vercel Python function entrypoint."""

from backend.api.index import app

application = app
handler = app
