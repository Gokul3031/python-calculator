from app import app, metrics

# Export Flask application metrics at /metrics via the app module.
# This keeps compatibility with any deployment that imports monitor.py.
