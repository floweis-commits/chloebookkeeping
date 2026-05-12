"""
Chloe Bookkeeping — FastAPI Application
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api import auth, files, flagged, permissions, reports, users, integrations
from backend.db.database import engine, Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables (dev only — use Alembic in production)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown: dispose of connection pool
    await engine.dispose()


app = FastAPI(
    title="Chloe Bookkeeping API",
    version="0.1.0",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(files.router, prefix="/api/files", tags=["files"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
app.include_router(permissions.router, prefix="/api/permissions", tags=["permissions"])
app.include_router(integrations.router, tags=["integrations"])
app.include_router(flagged.router, tags=["flagged"])


# ── Health check ──────────────────────────────────────────
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "chloe-bookkeeping"}
