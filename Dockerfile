FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY iot_connector/ /app/
COPY README.md /app/README.md

# Non-root user
RUN useradd -m iotuser && chown -R iotuser:iotuser /app
USER iotuser

EXPOSE 8080
EXPOSE 9090

CMD ["python", "-m", "connector"]
