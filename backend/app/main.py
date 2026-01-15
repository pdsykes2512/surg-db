"""
FastAPI Main Application
IMPACT API - Integrated Monitoring Platform for Audit Care & Treatment
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from slowapi.errors import RateLimitExceeded

from .config import settings
from .database import Database
from .routes import patients, episodes, reports, auth, admin, clinicians, exports, codes, nhs_providers, audit, investigations, backups, treatments_surgery, rstudio
from .middleware import limiter, rate_limit_exceeded_handler, RequestLoggingMiddleware, register_error_handlers


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    await Database.connect_db()
    await Database.initialize_indexes()
    yield
    # Shutdown
    await Database.close_db()


app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    lifespan=lifespan
)

# Register global error handlers for consistent error responses
register_error_handlers(app)

# Add rate limiter state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# Request logging middleware (add first to log all requests)
app.add_middleware(RequestLoggingMiddleware)

# CORS middleware - restricted to specific methods and headers for security
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

# Include routers
app.include_router(auth.router)
app.include_router(patients.router)
app.include_router(episodes.router)  # Episode-based care (cancer, IBD, benign)
app.include_router(treatments_surgery.router)  # Surgery treatments with RTT and reversal relationships
app.include_router(reports.router)
app.include_router(admin.router)
app.include_router(clinicians.router)
app.include_router(exports.router)
app.include_router(codes.router)  # ICD-10 and OPCS-4 validation/lookup
app.include_router(nhs_providers.router)  # NHS provider lookup via ODS API
app.include_router(audit.router)  # Audit logging and activity tracking
app.include_router(investigations.router)  # Clinical investigations and imaging
app.include_router(backups.router)  # Database backup management
app.include_router(rstudio.router)  # RStudio Server integration for advanced analytics


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "IMPACT API - Integrated Monitoring Platform for Audit Care & Treatment",
        "version": settings.api_version,
        "docs": "/docs"
    }


@app.get("/debug/config")
async def debug_config():
    """Debug endpoint to check configuration"""
    return {
        "mongodb_db_name": settings.mongodb_db_name,
        "mongodb_system_db_name": settings.mongodb_system_db_name,
        "api_version": settings.api_version
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )
