
import math
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

SUPPORTED_OPERATIONS = {
    "add",
    "subtract",
    "multiply",
    "divide",
}


class CalculatorError(ValueError):
    """An expected calculator input or calculation error."""


def parse_number(value, field_name):
    """Convert an input string to a finite floating-point number."""
    if value is None or not value.strip():
        raise CalculatorError(f"Please enter the {field_name}.")

    try:
        number = float(value)
    except (ValueError, OverflowError):
        raise CalculatorError(
            f"The {field_name} must be a valid number."
        ) from None

    if not math.isfinite(number):
        raise CalculatorError(
            f"The {field_name} must be a finite number."
        )

    return number


def calculate(a, b, operation):
    """Perform one supported calculation."""
    if operation not in SUPPORTED_OPERATIONS:
        raise CalculatorError("Unsupported operation.")

    if operation == "add":
        result = a + b
    elif operation == "subtract":
        result = a - b
    elif operation == "multiply":
        result = a * b
    else:
        if b == 0:
            raise CalculatorError("Cannot divide by zero.")
        result = a / b

    if not math.isfinite(result):
        raise CalculatorError(
            "The result is too large to represent."
        )

    return result


@app.route("/", methods=["GET", "POST"])
def calculator():
    result = None
    error = None
    operation = "unknown"
    request_start = time.perf_counter()

    if request.method == "POST":
        operation = request.form.get("operation", "unknown")

        # Use only fixed metric labels to avoid unbounded label values.
        metric_operation = (
            operation
            if operation in SUPPORTED_OPERATIONS
            else "unknown"
        )

        operation_start = time.perf_counter()

        try:
            a = parse_number(request.form.get("a"), "first number")
            b = parse_number(request.form.get("b"), "second number")

            result = calculate(a, b, operation)

        except CalculatorError as exc:
            error = str(exc)

        except (OverflowError, ZeroDivisionError):
            error = "The calculation could not be completed."

        finally:
            calculator_operation_duration_seconds.labels(
                operation=metric_operation
            ).observe(time.perf_counter() - operation_start)

        status = "error" if error else "success"

        calculator_operation_total.labels(
            operation=metric_operation,
            status=status,
        ).inc()

    status = "error" if error else "success"

    calculator_requests_total.labels(
        method=request.method,
        status=status,
    ).inc()

    # Keep the route timing available for future diagnostics.
    _request_duration = time.perf_counter() - request_start

    return render_template(
        "index.html",
        result=result,
        error=error,
    )


@app.route("/healthz", methods=["GET"])
def health_check():
    return {"status": "healthy"}, 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

print("hello world")