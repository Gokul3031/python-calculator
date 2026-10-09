from flask import Flask, render_template, request

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def calculator():
    result = None
    error = None

    if request.method == "POST":
        try:
            a = float(request.form["a"])
            b = float(request.form["b"])
            operation = request.form["operation"]

            if operation == "add":
                result = a + b
            elif operation == "subtract":
                result = a - b
            elif operation == "multiply":
                result = a * b
            elif operation == "divide":
                if b == 0:
                    error = "Cannot divide by zero"
                else:
                    result = a / b
        except (ValueError, KeyError):
            error = "Please enter valid numbers"

    return render_template("index.html", result=result, error=error)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
