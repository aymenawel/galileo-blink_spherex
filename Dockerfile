# Galileo Blink: one container serving the API and the built interface.
# Stage 1 builds the interface; stage 2 is the Python server.
FROM node:22-slim AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 \
    GALILEO_BLINK_CACHE=/tmp/galileo-blink-cache
WORKDIR /app
COPY pyproject.toml README.md ./
COPY galileo_blink/ galileo_blink/
# Installed in place: the code finds data/, prebuilt/ and web/dist beside itself.
RUN pip install --no-cache-dir -e .
COPY data/ data/
COPY prebuilt/ prebuilt/
COPY --from=web /web/dist web/dist
EXPOSE 8080
CMD ["sh", "-c", "uvicorn galileo_blink.server.app:app --host 0.0.0.0 --port ${PORT:-8080}"]
