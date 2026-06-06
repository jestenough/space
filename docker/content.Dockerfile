FROM python:3.14.5-slim-trixie

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    make \
    pandoc \
  && rm -rf /var/lib/apt/lists/*

COPY . .
