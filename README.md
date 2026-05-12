# Chloe Bookkeeping — Client Portal

Custom bookkeeping portal for **Channeled by Chloe LLC**.
Replaces the third-party NewWay Accounting portal with a self-hosted solution.

---

## Tech Stack

| Layer    | Technology                              |
| -------- | --------------------------------------- |
| Backend  | Python 3.12, FastAPI, SQLAlchemy, Alembic |
| Database | PostgreSQL 16                           |
| Frontend | Next.js 14, Tailwind CSS, TypeScript    |
| AI       | Anthropic Claude (claude-sonnet-4-20250514)       |
| PDF      | ReportLab                               |
| Auth     | JWT (access + refresh tokens)           |

---

## Quick Start

### 1. Clone and configure environment

```bash
cp .env.example .env
# Edit .env with your real credentials
```

### 2. Start PostgreSQL (Docker)

```bash
docker compose up db -d
```

### 3. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Health check: [http://localhost:8000/health](http://localhost:8000/health)

### 4. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open: [http://localhost:3000](http://localhost:3000)

---

## Project Structure

```
Chloe Bookkeeping/
├── backend/
│   ├── agents/          # AI agents (categorizer, insights, report gen)
│   ├── connectors/      # QuickBooks & Shopify API connectors
│   ├── db/              # SQLAlchemy models + Alembic migrations
│   ├── api/             # FastAPI route handlers
│   ├── storage/         # File storage abstraction (local → S3/R2)
│   └── main.py          # FastAPI app entry point
├── frontend/
│   ├── app/             # Next.js app router pages
│   ├── components/      # Shared React components
│   └── lib/             # API client utilities
├── .env.example         # Template for environment variables
├── docker-compose.yml   # Local development services
└── README.md
```

---

## Environment Variables

See [`.env.example`](.env.example) for the full list.
**Never commit `.env` to version control.**

---

## License

Private — Channeled by Chloe LLC. All rights reserved.
