FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY migrations ./migrations
COPY scripts ./scripts
# Keep legacy script path compatibility (e.g., python backend/scripts/...) inside the container
RUN mkdir -p /app/backend && ln -s /app/scripts /app/backend/scripts
RUN chmod +x scripts/start_worker.sh
ENV PYTHONPATH=/app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
