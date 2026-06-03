FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml ./
RUN uv pip compile pyproject.toml --output-file requirements.txt && \
    uv pip install --system --no-cache -r requirements.txt

COPY app ./app

# Команда переопределяется в docker-compose (bot / worker / api)
CMD ["python", "-m", "app.bot.runner"]
