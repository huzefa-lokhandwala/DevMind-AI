# DevMind AI Deployment Guide

Comprehensive instructions for deploying DevMind AI in local development, containerized Docker Compose, and production environments.

---

## 1. Deployment Overview

DevMind AI consists of three interconnected services:

1. **FastAPI Backend Service** (`app`): Port `8000`. Runs Python 3.12, Uvicorn, FAISS vector search, and Gemini provider.
2. **Next.js Frontend Workspace** (`frontend`): Port `3000`. Runs Next.js 14 standalone Node.js server.
3. **PostgreSQL Database** (`db`): Port `5432`. Runs PostgreSQL 16 with the `pgvector` extension.

```
Browser (localhost:3000) ---> Next.js Frontend App
   │
   +---> API Fetch (http://localhost:8000) ---> FastAPI Backend App
                                                    │
                                                    +---> PostgreSQL + pgvector (port 5432)
```

---

## 2. Environment Configuration

### Development Profile (`.env`)
Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

```env
# Gemini API Key (Required for AI response generation)
GEMINI_API_KEY=your_gemini_api_key_here

# Environment Mode ('development', 'testing', or 'production')
DEVMIND_ENV=development

# Security API Key Header (Optional in local development)
DEVMIND_API_KEY=

# CORS Allowed Origins
CORS_ORIGINS=http://localhost:3000

# Database Connection (Local Docker Container)
DATABASE_URL=postgresql+psycopg://devmind:devmind_local@localhost:5432/devmind
POSTGRES_DB=devmind
POSTGRES_USER=devmind
POSTGRES_PASSWORD=devmind_local
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Frontend API URL
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

---

### Production Profile (`.env.production`)
Copy `.env.production.example` to `.env` in production environments:

```bash
cp .env.production.example .env
```

> [!IMPORTANT]
> In production (`DEVMIND_ENV=production`), `DEVMIND_API_KEY` is **mandatory**. If unconfigured, the backend will fail closed with `500 Server Security Misconfiguration` to prevent open API access.

---

## 3. Deployment Modes

### Mode A: Docker Compose (Recommended)

Run the full unified application with a single command:

```bash
docker compose up --build -d
```

- **Frontend**: [http://localhost:3000](http://localhost:3000)
- **Backend API**: [http://localhost:8000](http://localhost:8000)
- **Health Verification**:
  ```bash
  curl -i http://localhost:8000/health
  curl -i http://localhost:8000/health/ready
  ```

---

### Mode B: Production Profile Override

For production servers requiring log rotation, resource limits, and strict restart policies:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d
```

#### Production Optimizations in `docker-compose.prod.yml`:
- Sets `DEVMIND_ENV=production`.
- Configures `json-file` log rotation with `20m` max file size and max 5 files.
- Sets container restart policy to `always`.

---

### Mode C: Manual Local Development

If running backend and frontend directly on the host machine:

1. **Start Database Container**:
   ```bash
   docker compose up -d db
   ```

2. **Run Backend Database Migrations & Start Server**:
   ```bash
   source .venv/bin/activate
   alembic upgrade head
   uvicorn app.api.main:app --reload --port 8000
   ```

3. **Start Frontend Dev Server**:
   ```bash
   cd frontend
   npm run dev
   ```

---

## 4. Monitoring & Operations

### Container Status
```bash
docker compose ps
```

### Viewing Logs
```bash
# View backend app logs
docker compose logs -f app

# View frontend logs
docker compose logs -f frontend

# View database logs
docker compose logs -f db
```

### Database Migrations (Alembic)
To apply new migrations inside Docker:
```bash
docker compose exec app alembic upgrade head
```

---

## 5. Security & Maintenance

### CORS Configuration
Ensure `CORS_ORIGINS` strictly specifies production domain URLs (e.g. `https://devmind.example.com`). Never use `allow_origins=["*"]` in production.

### Backup Database Data
PostgreSQL data is stored in the Docker named volume `postgres_data`. To backup:
```bash
docker compose exec db pg_dump -U devmind devmind > devmind_backup.sql
```

### Rollback Procedure
To stop containers, clear volumes, and restore to previous release tag:
```bash
docker compose down
git checkout <previous_stable_tag>
docker compose up --build -d
```
