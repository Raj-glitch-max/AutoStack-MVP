# Autostack Backend (FastAPI)

Backend for the Autostack MVP, implemented with FastAPI, PostgreSQL (async), SQLAlchemy, and Alembic.

## Quickstart

1. **Create virtualenv & install deps**

```bash
cd autostack-backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
```

2. **Configure environment**

Copy `.env.example` to `.env` and fill in real values:

```bash
cp .env.example .env
```

Set at minimum:

- `DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/autostack`
- `SECRET_KEY=...`
- GitHub & Google OAuth credentials
- `AUTOSTACK_DEPLOY_DIR=./deployments`

3. **Run database migrations**

```bash
alembic upgrade head
```

4. **Run the API server**

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open Swagger UI at: http://localhost:8000/docs

## Environment

Set the following variables (use your own values in production). The OAuth credentials below were provided for this MVP:

| Variable | Example / Default |
| --- | --- |
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/autostack` |
| `SECRET_KEY` | `dev-secret-key` |
| `FRONTEND_URL` | `http://localhost:3000` |
| `FRONTEND_ADDITIONAL_ORIGINS` | `http://localhost:5173` |
| `GITHUB_CLIENT_ID` | `<your-github-client-id>` |
| `GITHUB_CLIENT_SECRET` | `<your-github-client-secret>` |
| `GITHUB_CALLBACK_URL` | `http://localhost:8000/auth/github/callback` |
| `GITHUB_WEBHOOK_SECRET` | `<your-github-webhook-secret>` |
| `GOOGLE_CLIENT_ID` | `<your-google-client-id>` |
| `GOOGLE_CLIENT_SECRET` | `<your-google-client-secret>` |
| `GOOGLE_CALLBACK_URL` | `http://localhost:8000/auth/google/callback` |
| `AUTOSTACK_DEPLOY_DIR` | `./deployments` |
| `SMTP_*`, `EMAIL_FROM` | Configure for forgot-password emails. Leave blank to log to console. |

## Docker / Compose

```bash
docker compose up --build
```

This runs Postgres + the FastAPI app with volumes for database state and deployment artifacts. Override any environment variable by exporting it before running compose.

## Database Migrations

- Create a new migration: `alembic revision --autogenerate -m "description"`
- Run migrations: `alembic upgrade head`

## Smoke Tests

The backend ships with lightweight async smoke tests covering auth, deployments, webhooks, and WebSockets.

```bash
scripts/smoke_test.sh        # macOS/Linux
scripts/smoke_test.ps1       # Windows
```

Both scripts default to sqlite in the repo folder and do not require Postgres.
