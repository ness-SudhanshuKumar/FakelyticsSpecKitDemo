"""Verification API routes for URL submission and report retrieval."""

from __future__ import annotations

import logging
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status

from src.api.dependencies.security import AuthContext, enforce_rate_limit, require_api_key
from src.api.models.schemas import ReportResponse, RequestStatus, VerifyRequest, VerifyResponse
from src.core.config.settings import settings
from src.core.extraction.service import ContentExtractionError, extraction_service
from src.core.storage.inmemory import request_store
from src.services.orchestration import build_credibility_report, post_webhook_result

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Verification"])


async def _run_verification(request_id: UUID, url: str):
    """Run extraction + orchestration and persist report status."""
    request_store.update_status(request_id, RequestStatus.PROCESSING)
    content = await extraction_service.extract(url)
    report = await build_credibility_report(request_id=request_id, url=url, content=content)
    request_store.set_report(request_id, report)
    return report


async def _process_async_request(request_id: UUID, url: str, webhook_url: str | None) -> None:
    """Background async flow for verification + optional webhook callback."""
    try:
        report = await _run_verification(request_id=request_id, url=url)
        if webhook_url:
            await post_webhook_result(
                webhook_url=webhook_url,
                request_id=request_id,
                status=RequestStatus.COMPLETED.value,
                report=report,
            )
    except Exception as exc:
        logger.error("Async verification failed", extra={"request_id": str(request_id), "error": str(exc)})
        request_store.set_error(request_id, str(exc))
        if webhook_url:
            await post_webhook_result(
                webhook_url=webhook_url,
                request_id=request_id,
                status=RequestStatus.FAILED.value,
                error_message=str(exc),
            )


@router.post("/verify", response_model=VerifyResponse, status_code=status.HTTP_200_OK)
async def submit_verification(
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    verify_request: VerifyRequest,
    auth: AuthContext = Depends(require_api_key),
) -> VerifyResponse:
    """
    Submit a URL for verification.

    - Sync mode (default): returns 200 + completed report.
    - Async mode: returns 202 + request_id and optional webhook callback on completion.
    """
    enforce_rate_limit(response=response, auth=auth, endpoint="/verify")

    trace_id = getattr(request.state, "trace_id", "unknown")
    request_id = uuid4()
    options = verify_request.options
    async_mode = bool(options.async_mode if options else False)
    webhook_url = str(options.webhook_url) if options and options.webhook_url else None

    request_data = request_store.create_request(
        request_id=request_id,
        url=verify_request.url,
        async_mode=async_mode,
        webhook_url=webhook_url,
    )

    logger.info(
        "Verification request received",
        extra={
            "trace_id": trace_id,
            "request_id": str(request_id),
            "url": verify_request.url,
            "async_mode": async_mode,
        },
    )

    if async_mode and settings.ENABLE_ASYNC_MODE:
        request_store.update_status(request_id, RequestStatus.PROCESSING)
        background_tasks.add_task(
            _process_async_request,
            request_id=request_id,
            url=verify_request.url,
            webhook_url=webhook_url if settings.ENABLE_WEBHOOKS else None,
        )
        response.status_code = status.HTTP_202_ACCEPTED
        return VerifyResponse(
            request_id=request_id,
            status=RequestStatus.PROCESSING,
            report=None,
            created_at=request_data["created_at"],
            completed_at=None,
        )

    try:
        report = await _run_verification(request_id=request_id, url=verify_request.url)
        latest = request_store.get_request(request_id)
        return VerifyResponse(
            request_id=request_id,
            status=RequestStatus.COMPLETED,
            report=report,
            created_at=latest["created_at"] if latest else request_data["created_at"],
            completed_at=latest["completed_at"] if latest else None,
        )
    except ContentExtractionError as exc:
        request_store.set_error(request_id, str(exc))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "extraction_failed", "message": f"Failed to extract content: {str(exc)}"},
        )
    except Exception as exc:
        request_store.set_error(request_id, str(exc))
        logger.error(
            "Verification failed with exception",
            extra={"trace_id": trace_id, "request_id": str(request_id), "exception": str(exc)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "verification_failed", "message": "An error occurred during verification"},
        )


@router.get("/report/{request_id}", response_model=ReportResponse, status_code=status.HTTP_200_OK)
@router.get("/verify/{request_id}", response_model=ReportResponse, include_in_schema=False)
async def get_report(
    request: Request,
    response: Response,
    request_id: str,
    auth: AuthContext = Depends(require_api_key),
) -> ReportResponse:
    """Retrieve verification report by request ID."""
    enforce_rate_limit(response=response, auth=auth, endpoint="/report")

    trace_id = getattr(request.state, "trace_id", "unknown")
    logger.info("Report retrieval requested", extra={"trace_id": trace_id, "request_id": request_id})

    try:
        request_uuid = UUID(request_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_request_id", "message": "Invalid request ID format"},
        )

    request_data = request_store.get_request(request_uuid)
    if not request_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": "Request not found"},
        )

    if request_data["status"] in {RequestStatus.PENDING, RequestStatus.PROCESSING}:
        response.status_code = status.HTTP_202_ACCEPTED

    return ReportResponse(
        request_id=request_uuid,
        status=request_data["status"],
        report=request_data["report"],
    )

