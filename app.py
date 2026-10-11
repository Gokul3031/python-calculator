import time

from flask import Flask, render_template, request
from prometheus_flask_exporter import PrometheusMetrics
from prometheus_client import Counter, Histogram

app = Flask(__name__)
metrics = PrometheusMetrics(app)

calculator_operation_total = Counter(
    "calculator_operation_total",
    "Total number of calculator operations by type and result",
    ["operation", "status"],
)

calculator_operation_duration_seconds = Histogram(
    "calculator_operation_duration_seconds",
    "Time spent processing calculator operations in seconds",
    ["operation"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

calculator_requests_total = Counter(
    "calculator_requests_total",
    "Total HTTP requests received by the calculator application",
    ["method", "status"],
)

@app.route("/", methods=["GET", "POST"])
def calculator():
    result = None
    error = None
    request_start = time.perf_counter()
    operation = "unknown"

    if request.method == "POST":
        try:
            a = float(request.form["a"])
            b = float(request.form["b"])
            operation = request.form["operation"]

            if operation == "add":
                result = a + b
                calculator_operation_total.labels(operation=operation, status="success").inc()
            elif operation == "subtract":
                result = a - b
                calculator_operation_total.labels(operation=operation, status="success").inc()
            elif operation == "multiply":
                result = a * b
                calculator_operation_total.labels(operation=operation, status="success").inc()
            elif operation == "divide":
                if b == 0:
                    error = "Cannot divide by zero"
                    calculator_operation_total.labels(operation=operation, status="error").inc()
                else:
                    result = a / b
                    calculator_operation_total.labels(operation=operation, status="success").inc()
            else:
                error = "Unsupported operation"
                calculator_operation_total.labels(operation=operation, status="error").inc()
        except (ValueError, KeyError):
            error = "Please enter valid numbers"
            calculator_operation_total.labels(operation="invalid_input", status="error").inc()

    status = "success" if error is None else "error"
    processing_time = time.perf_counter() - request_start
    calculator_operation_duration_seconds.labels(operation=operation).observe(processing_time)
    calculator_requests_total.labels(method=request.method, status=status).inc()

    return render_template("index.html", result=result, error=error)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
