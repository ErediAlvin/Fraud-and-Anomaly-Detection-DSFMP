"""
DSFMP Fraud Detection — FastAPI Application Entry Point

This is the main application factory. It:
1. Configures CORS for the React frontend
2. Manages startup/shutdown lifecycle (DB, Redis, ML models)
3. Registers all API routers
4. Provides a health check endpoint
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import settings
from database.connection import engine
from database.redis import get_redis, close_redis


# ── Lifespan: Startup & Shutdown ──────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs once on startup and once on shutdown.

    Startup:
    - Verify MySQL connection
    - Verify Redis connection
    - (Phase 2) Load ML models into memory

    Shutdown:
    - Close Redis pool
    - Dispose SQLAlchemy engine
    """
    # ── Startup ──
    print(f"[START] Starting {settings.app_name} v{settings.app_version}")

    # Verify MySQL is reachable
    try:
        async with engine.connect() as conn:
            await conn.execute(
                __import__("sqlalchemy").text("SELECT 1")
            )
        print("[OK] MySQL connection verified")
    except Exception as e:
        print(f"[ERROR] MySQL connection failed: {e}")
        # Don't crash — let the app start so health checks can report status

    # Verify Redis is reachable
    try:
        redis = await get_redis()
        await redis.ping()
        print("[OK] Redis connection verified")
    except Exception as e:
        print(f"[WARN] Redis connection failed (non-critical): {e}")

    # Load ML models into application state
    try:
        from ml.models.scoring_engine import get_isolation_forest_model
        app.state.isolation_forest = get_isolation_forest_model()
        print("[OK] Isolation Forest ML model loaded successfully into memory")
    except Exception as e:
        print(f"[WARN] Isolation Forest model load skipped or failed: {e}")

    print(f"[OK] {settings.app_name} ready -- accepting requests")

    yield  # <- App runs here

    # ── Shutdown ──
    print("[STOP] Shutting down...")
    await close_redis()
    await engine.dispose()
    print("[OK] Shutdown complete")


# ── App Factory ───────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Backend API for the DSFMP Fraud Detection Module. "
        "Provides ML-powered fraud scoring, case management, "
        "blockchain ledger integration, and real-time alerting "
        "for Kenya's Digital School Feeding Management Platform."
    ),
    docs_url="/docs" if settings.debug else None,      # Swagger UI
    redoc_url="/redoc" if settings.debug else None,     # ReDoc
    lifespan=lifespan,
)


# ── CORS Middleware ───────────────────────────────
# Allow the React frontend to make cross-origin requests.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health Check ──────────────────────────────────
@app.get(
    "/health",
    tags=["System"],
    summary="Health check",
    response_description="Returns API health status and uptime info",
)
async def health_check():
    """
    Lightweight health check endpoint.
    Returns 200 with basic status info. Used by Docker, load balancers,
    and the frontend to verify the API is running.
    """
    # Check DB connectivity
    db_status = "healthy"
    try:
        async with engine.connect() as conn:
            await conn.execute(
                __import__("sqlalchemy").text("SELECT 1")
            )
    except Exception:
        db_status = "unhealthy"

    # Check Redis connectivity
    redis_status = "healthy"
    try:
        redis = await get_redis()
        await redis.ping()
    except Exception:
        redis_status = "unhealthy"

    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": {
            "mysql": db_status,
            "redis": redis_status,
        },
    }


# ── Register Routers ─────────────────────────────
# Uncomment these as you build each module:

from routes.auth import router as auth_router
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])

from routes.dashboard import router as dashboard_router
app.include_router(dashboard_router, prefix="/api/dashboard", tags=["Dashboard"])

from routes.alerts import router as alerts_router
app.include_router(alerts_router, prefix="/api/alerts", tags=["Fraud Alerts"])

from routes.cases import router as cases_router
app.include_router(cases_router, prefix="/api/cases", tags=["Case Management"])

from routes.beneficiaries import router as beneficiaries_router
app.include_router(beneficiaries_router, prefix="/api/beneficiaries", tags=["Beneficiaries"])

from routes.transactions import router as transactions_router
app.include_router(transactions_router, prefix="/api/transactions", tags=["Transactions"])

from routes.supply_chain import router as supply_chain_router
app.include_router(supply_chain_router, prefix="/api/supply-chain", tags=["Supply Chain"])

# from routes.blockchain import router as blockchain_router
# app.include_router(blockchain_router, prefix="/api/blockchain", tags=["Blockchain"])

from routes.risk_profiles import router as risk_profiles_router
app.include_router(risk_profiles_router, prefix="/api/risk-profiles", tags=["Risk Profiles"])

from routes.reports import router as reports_router
app.include_router(reports_router, prefix="/api/reports", tags=["Reports"])

from routes.model_performance import router as model_perf_router
app.include_router(model_perf_router, prefix="/api/models", tags=["Model Performance"])

# from routes.procedures import router as procedures_router
# app.include_router(procedures_router, prefix="/api/procedures", tags=["SOB/COB Procedures"])

from routes.settings import router as settings_router
app.include_router(settings_router, prefix="/api/settings", tags=["System Settings"])
