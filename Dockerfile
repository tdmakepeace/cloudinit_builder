FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install only runtime dependencies needed for the Flask app.
RUN pip install --no-cache-dir flask passlib pyyaml

COPY . /app

# Keep generated files under /app/output so users can bind-mount it.
RUN mkdir -p /app/output

EXPOSE 10000

# Run Flask directly (skip app.py __main__ desktop/webview branch).
CMD ["python", "-c", "from app import app; app.run(host='0.0.0.0', port=10000, debug=False, use_reloader=False)"]
