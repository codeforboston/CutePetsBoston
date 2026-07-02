FROM python:3.14-slim-bookworm AS base

ENV VENV=/opt/venv
RUN python -m venv $VENV
ENV PATH="$VENV/bin:$PATH"

WORKDIR /app

COPY requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock

COPY main.py ./


FROM base AS app

RUN useradd app
RUN mkdir -p /home/app && \
    chown -R app:app /home/app && \
    chown -R app:app /app
USER app

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--reload"]


FROM base AS devbox
COPY requirements.txt ./
COPY requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt
