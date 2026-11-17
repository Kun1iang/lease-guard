FROM node:24-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim
WORKDIR /app/backend
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --extra ocr
COPY backend/app ./app
COPY --from=frontend-build /app/frontend/dist /app/frontend/dist
ENV PATH="/app/backend/.venv/bin:$PATH"
ENV DATABASE_URL="sqlite:////app/backend/data/lease_guard.db"
ENV STORAGE_DIR="/app/backend/storage"
RUN mkdir -p /app/backend/data /app/backend/storage
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
