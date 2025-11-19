FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY README.md ./

ENV PYTHONPATH=/app/src \
    BROWSER_BASE_URL=https://example.com \
    AI_MODEL_NAME=mock-gpt \
    ORCHESTRATOR_MAX_STEPS=5

CMD ["python", "-m", "gpt1.cli"]
