"""
FastAPI Main Application
Surgical Outcomes Database API
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .config import settings
from .database import Database
from .routes import patients, episodes_v2, reports, auth, admin, clinicians, exports, codes


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    await Database.connect_db()
    yield
    # Shutdown
    await Database.close_db()


app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(patients.router)
app.include_router(episodes_v2.router)  # Episode-based care (cancer, IBD, benign)
app.include_router(reports.router)
app.include_router(admin.router)
app.include_router(clinicians.router)
app.include_router(exports.router)
app.include_router(codes.router)  # ICD-10 and OPCS-4 validation/lookup


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Surgical Outcomes Database API",
        "version": settings.api_version,
        "docs": "/docs"
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
