"""Main FastAPI application for Fakelytics platform"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, Response
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
    Health check endpoint with comprehensive system status.
    
    **Satisfies**: FR-010 (Audit logging), T-903 (Health Checks)
    **Returns**: System status, version, and timestamp
    """
    trace_id = getattr(request.state, "trace_id", "unknown")
    
    # Check basic health
    health_status = "healthy"
    checks = {
        "api": "ok",
        "extraction_service": "ok",
        "report_persistence": "ok",
        "report_formatter": "ok",
    }
    
    # Verify critical services are available
    try:
        from src.core.extraction.service import extraction_service
        if extraction_service is None:
            health_status = "degraded"
            checks["extraction_service"] = "unavailable"
    except Exception as e:
        health_status = "degraded"
        checks["extraction_service"] = f"error: {str(e)}"
    
    try:
        from src.services.persistence.reports import report_persistence
        if report_persistence.get_report_count() >= 0:  # Test method
            checks["report_persistence"] = "ok"
    except Exception as e:
        health_status = "degraded"
        checks["report_persistence"] = f"error: {str(e)}"
    
    app_logger.info(
        "Health check performed",
        extra={
            "trace_id": trace_id,
            "status": health_status,
            "checks": checks
        }
    )
    
    return HealthResponse(
        status=health_status,
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


@app.get("/metrics", tags=["Monitoring"])
async def get_metrics(request: Request):
    """
    Prometheus-compatible metrics endpoint.
    
    **Satisfies**: T-902 (Metrics & Monitoring - Prometheus endpoint)
    **Returns**: System metrics in Prometheus format
    """
    trace_id = getattr(request.state, "trace_id", "unknown")
    
    try:
        from src.services.monitoring.metrics import metrics_collector
        metrics_text = metrics_collector.to_prometheus_format()
        
        app_logger.info(
            "Metrics endpoint accessed",
            extra={"trace_id": trace_id}
        )
        
        return Response(
            content=metrics_text,
            media_type="text/plain; version=0.0.4"
        )
    except Exception as e:
        app_logger.error(
            "Error generating metrics",
            extra={"trace_id": trace_id, "error": str(e)},
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Error generating metrics"
        )


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
