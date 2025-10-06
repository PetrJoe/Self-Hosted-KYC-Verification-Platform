"""
KYC Verification Platform - Main Entry Point
A self-hosted, modular KYC verification system with end-to-end verification capabilities.
"""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.api import api_router
from app.database.session import create_tables
from app.core.config import settings

app = FastAPI(
    title="KYC Verification Platform",
    description="End-to-end KYC verification platform for businesses and developers",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set up CORS
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    await create_tables()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

# Include API routes
app.include_router(api_router, prefix=settings.API_V1_STR)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )