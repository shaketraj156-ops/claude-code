FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY Track2-ClaudeImpactLabs/ ./Track2-ClaudeImpactLabs/
WORKDIR /app/Track2-ClaudeImpactLabs/visarjan-demo
CMD ["python", "server.py"]
