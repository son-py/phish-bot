# Single image for both web and bot; override CMD in docker-compose or host
FROM python:3.11-slim

WORKDIR /app
COPY . /app

RUN pip install --upgrade pip
RUN pip install -r bot/requirements.txt
RUN pip install -r web/requirements.txt

ENV PYTHONUNBUFFERED=1

# Default to web app; for bot use a different command
CMD ["gunicorn", "web.app:app", "--bind", "0.0.0.0:8000", "--workers", "2"]
