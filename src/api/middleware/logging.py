"""Middleware for request/response logging and tracing"""

import logging
import time
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from pythonjsonlogger import jsonlogger


# Configure JSON logging
def setup_json_logger(logger_name: str) -> logging.Logger:
    """Set up JSON logger for structured logging"""
    logger = logging.getLogger(logger_name)
    logHandler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter()
    logHandler.setFormatter(formatter)
    logger.addHandler(logHandler)
    logger.setLevel(logging.INFO)
    return logger


# Global logger instances
app_logger = setup_json_logger("fakelytics")
access_logger = setup_json_logger("fakelytics.access")


class TraceIDMiddleware(BaseHTTPMiddleware):
    """Middleware to add trace IDs to all requests"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add trace ID to request and response"""
        # Generate or get trace ID
        trace_id = request.headers.get("X-Trace-ID", str(uuid.uuid4()))
        
        # Store in request state
        request.state.trace_id = trace_id
        request.state.start_time = time.time()

        # Call next middleware/route
        response = await call_next(request)

        # Add trace ID to response headers
        response.headers["X-Trace-ID"] = trace_id
        
        # Log request completion
        process_time = time.time() - request.state.start_time
        access_logger.info(
            "HTTP Request",
            extra={
                "trace_id": trace_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "process_time": process_time,
                "client_host": request.client.host if request.client else None,
            }
        )

        return response


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Middleware for global error handling"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Wrap request in error handling"""
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            trace_id = getattr(request.state, "trace_id", "unknown")
            app_logger.error(
                "Unhandled exception",
                extra={
                    "trace_id": trace_id,
                    "exception": str(exc),
                    "path": request.url.path,
                    "method": request.method,
                },
                exc_info=True
            )
            # Let FastAPI exception handlers deal with it
            raise
