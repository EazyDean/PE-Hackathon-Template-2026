FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml README.md ./
COPY app ./app
COPY run.py ./
COPY .python-version ./

RUN uv sync

EXPOSE 5000

CMD ["uv", "run", "python", "run.py"]
