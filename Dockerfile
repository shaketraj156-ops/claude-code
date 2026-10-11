FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 HOST=0.0.0.0
WORKDIR /app
COPY Track2-ClaudeImpactLabs/ ./Track2-ClaudeImpactLabs/
COPY server.py ./server.py
CMD ["python", "server.py"]
