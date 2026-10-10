from prometheus_flask_exporter import PrometheusMetrics
from app import app

# Export Flask application metrics at /metrics
metrics = PrometheusMetrics(app)
