import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.llm_monitor import reset_gemini_rate_limit, has_gemini_rate_limit_occurred
from app.db.session import connect_to_mongo, close_mongo_connection, db_manager, get_database
from app.seed import seed_database
from app.api.routes import (
    auth, dashboard, products, demand, collaborations, campaigns, copilot, neighborhood
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Connect to DB and seed synthetic demo data if empty
    logger.info("Initializing LocalPulse AI backend services...")
    await connect_to_mongo()
    if db_manager.db is not None:
        seed_result = await seed_database(db_manager.db, force=False)
        logger.info(f"Database seed check: {seed_result}")
    yield
    # Shutdown: Close DB
    await close_mongo_connection()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="LocalPulse AI — Merchant Growth AI Engine for Local Indian MSMEs",
    lifespan=lifespan,
)

# Configure CORS
origins = settings.cors_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$|^https://.*\.vercel\.app$|^https://.*\.netlify\.app$|^https://.*\.onrender\.com$|^https://.*\.railway\.app$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Gemini-Rate-Limited", "X-Gemini-Quota-Exceeded"],
)

@app.middleware("http")
async def gemini_rate_limit_monitor_middleware(request: Request, call_next):
    reset_gemini_rate_limit()
    response = await call_next(request)
    if has_gemini_rate_limit_occurred():
        response.headers["X-Gemini-Rate-Limited"] = "true"
        response.headers["X-Gemini-Quota-Exceeded"] = "true"
    return response

# Root endpoint for platform health checks and discovery
@app.get("/", tags=["Health"])
async def root():
    """Root endpoint for cloud platform health checks and service info."""
    return {
        "status": "online",
        "app": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": "/docs",
        "health": "/health",
        "api": settings.API_V1_STR,
    }

# Global health endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint indicating database connectivity and demo mode."""
    db_status = "connected" if db_manager.db is not None else "disconnected"
    return {
        "status": "healthy",
        "app": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "database": db_status,
        "database_backend": "In-Memory MongoMock" if db_manager.is_mock else "MongoDB Cluster",
        "llm_provider": settings.LLM_PROVIDER,
        "llm_configured": bool(settings.LLM_API_KEY and settings.LLM_API_KEY.strip()),
    }

# Manual seed re-trigger endpoint for hackathon demo resets
@app.post("/api/seed/reset", tags=["Admin & Demo"])
async def reset_seed_data():
    """Reset and re-seed all fictional demo merchants, products, and sales records."""
    if db_manager.db is None:
        await connect_to_mongo()
    result = await seed_database(db_manager.db, force=True)
    return {"status": "success", "seed_summary": result}

# Include all API routes
api_prefix = settings.API_V1_STR
app.include_router(auth.router, prefix=api_prefix)
app.include_router(dashboard.router, prefix=api_prefix)
app.include_router(products.router, prefix=api_prefix)
app.include_router(demand.router, prefix=api_prefix)
app.include_router(collaborations.router, prefix=api_prefix)
app.include_router(campaigns.router, prefix=api_prefix)
app.include_router(copilot.router, prefix=api_prefix)
app.include_router(neighborhood.router, prefix=api_prefix)

# Consistent JSON error handler
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error processing {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred. Please verify input parameters."},
    )
