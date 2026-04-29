"""Main FastAPI application for Fakelytics platform"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from src.core.config.settings import settings
from src.api.middleware.logging import TraceIDMiddleware, ErrorHandlerMiddleware, app_logger
from src.api.models.schemas import HealthResponse
from datetime import datetime


# Lifespan events for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app startup and shutdown"""
    # Startup
    app_logger.info("Fakelytics API starting", extra={"version": settings.APP_VERSION})
    yield
    # Shutdown
    app_logger.info("Fakelytics API shutting down")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="Unified multimodal content verification platform",
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


# Add middleware - order matters!
# 1. Trace ID middleware (outer - runs first on request)
app.add_middleware(TraceIDMiddleware)

# 2. Error handling middleware
app.add_middleware(ErrorHandlerMiddleware)

# 3. CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Trace-ID", "X-RateLimit-*"],
)


# Exception handlers

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle all unhandled exceptions"""
    trace_id = getattr(request.state, "trace_id", "unknown")
    
    # Log the exception
    app_logger.error(
        "Unhandled exception",
        extra={
            "trace_id": trace_id,
            "exception_type": type(exc).__name__,
            "exception": str(exc),
        },
        exc_info=True
    )
    
    # Return error response
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": "An internal server error occurred",
            "details": {"trace_id": trace_id}
        },
        headers={"X-Trace-ID": trace_id}
    )


# Routes

@app.get("/health", tags=["Health"], response_model=HealthResponse)
async def health_check(request: Request) -> HealthResponse:
    """
    Health check endpoint
    
    **Satisfies**: FR-010 (Audit logging)
    **Returns**: System status, version, and timestamp
    """
    trace_id = getattr(request.state, "trace_id", "unknown")
    
    app_logger.info(
        "Health check",
        extra={"trace_id": trace_id}
    )
    
    return HealthResponse(
        status="healthy",
        version=settings.APP_VERSION,
        timestamp=datetime.utcnow()
    )


@app.get("/", tags=["Root"])
async def root():
    """API root endpoint"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "api_prefix": settings.API_PREFIX
    }


# Import and include routers
from src.api.routes import verification

app.include_router(verification.router, prefix=settings.API_PREFIX, tags=["Verification"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.API_HOST,
        port=settings.API_PORT,
        log_level=settings.LOG_LEVEL.lower(),
    )
