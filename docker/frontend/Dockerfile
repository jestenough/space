FROM node:24.16.0-trixie-slim

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
