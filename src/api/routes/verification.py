"""Verification API routes for URL submission and report retrieval"""

import logging
from uuid import uuid4
from fastapi import APIRouter, HTTPException, Request, status
from typing import Optional

from src.api.models.schemas import (
    VerifyRequest,
    VerifyResponse,
    ReportResponse,
    RequestStatus,
    ErrorResponse,
    CredibilityReport,
    Findings,
    PipelineResult,
    Verdict,
)
from src.core.extraction.service import extraction_service, ContentExtractionError
from src.core.storage.inmemory import request_store
from src.core.config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/verify", tags=["Verification"])


@router.post("", response_model=VerifyResponse, status_code=status.HTTP_200_OK)
async def submit_verification(
    request: Request,
    verify_request: VerifyRequest,
) -> VerifyResponse:
    """
    Submit a URL for verification
    
    **Satisfies**: 
    - FR-001 (Accept URL and extract content)
    - FR-007 (Synchronous API with timeout)
    - FR-008 (Asynchronous callbacks via webhooks)
    - US-1 (URL-Based Verification)
    - US-2 (API Integration)
    
    **Spec Section**: API Contract POST /verify
    
    **Assumptions**:
    - URL is already validated by Pydantic
    - Content extraction completes within timeout
    - Report generation is synchronous for MVP
    
    **Returns**:
    - 200: Report completed immediately (sync mode)
    - 202: Verification queued (async mode)
    """
    trace_id = getattr(request.state, "trace_id", "unknown")
    request_id = uuid4()

    try:
        logger.info(
            "Verification request received",
            extra={
                "trace_id": trace_id,
                "request_id": str(request_id),
                "url": verify_request.url,
                "async_mode": verify_request.options.async_mode if verify_request.options else False,
            }
        )

        # Create request record
        options = verify_request.options or {}
        webhook_url = options.webhook_url if hasattr(options, 'webhook_url') else None
        async_mode = options.async_mode if hasattr(options, 'async_mode') else False

        request_store.create_request(
            request_id=request_id,
            url=verify_request.url,
            async_mode=async_mode,
            webhook_url=str(webhook_url) if webhook_url else None,
        )

        # For MVP: Process synchronously
        # Extract content from URL
        try:
            logger.info(f"Extracting content from {verify_request.url}")
            content = await extraction_service.extract(verify_request.url)
        except ContentExtractionError as e:
            logger.error(f"Content extraction failed: {str(e)}")
            request_store.set_error(request_id, str(e))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "extraction_failed",
                    "message": f"Failed to extract content: {str(e)}",
                }
            )

        # Generate report (MVP: simple mock report)
        # In production, this would invoke pipelines in parallel
        report = _generate_mock_report(request_id, verify_request.url, content)

        # Store report
        request_store.set_report(request_id, report)

        logger.info(
            "Verification completed",
            extra={
                "trace_id": trace_id,
                "request_id": str(request_id),
                "credibility_score": report.overall_credibility_score,
            }
        )

        return VerifyResponse(
            request_id=request_id,
            status=RequestStatus.COMPLETED,
            report=report,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Verification failed with exception",
            extra={
                "trace_id": trace_id,
                "request_id": str(request_id),
                "exception": str(e),
            },
            exc_info=True
        )
        request_store.set_error(request_id, str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "verification_failed",
                "message": "An error occurred during verification",
            }
        )


def _generate_mock_report(request_id, url: str, content) -> CredibilityReport:
    """
    Generate a mock report for MVP
    
    **TODO**: Replace with actual pipeline execution
    """
    from datetime import datetime

    # Mock findings for MVP
    findings = Findings(
        text=PipelineResult(
            verdict=Verdict.SUPPORTED if len(content.text_content) > 100 else Verdict.UNVERIFIABLE,
            confidence=75,
            findings=[]
        ),
        image=PipelineResult(
            verdict=Verdict.UNVERIFIABLE if len(content.images) == 0 else Verdict.DISPUTED,
            confidence=50 if content.images else 0,
            findings=[]
        ) if content.images else None,
        audio_video=None,
        spam=PipelineResult(
            verdict=Verdict.SUPPORTED,
            confidence=85,
            findings=[]
        ),
    )

    # Calculate overall score (mock)
    scores = [
        findings.text.confidence,
        findings.spam.confidence,
    ]
    if findings.image:
        scores.append(findings.image.confidence)

    overall_score = int(sum(scores) / len(scores)) if scores else 50

    return CredibilityReport(
        request_id=request_id,
        url=url,
        overall_credibility_score=overall_score,
        summary=f"Mock report: Content extracted with {len(content.text_content)} chars, "
                f"{len(content.images)} images, {len(content.audio)} audio, {len(content.video)} video",
        findings=findings,
        timestamp=datetime.utcnow(),
    )


@router.get("/{request_id}", response_model=ReportResponse, status_code=status.HTTP_200_OK)
async def get_report(
    request: Request,
    request_id: str,
) -> ReportResponse:
    """
    Retrieve verification report by request ID
    
    **Satisfies**:
    - FR-007 (Report retrieval endpoint)
    - US-2 (API Integration)
    
    **Spec Section**: API Contract GET /report/{request_id}
    
    **Returns**:
    - 200: Report retrieved successfully
    - 202: Still processing
    - 404: Report not found
    """
    trace_id = getattr(request.state, "trace_id", "unknown")

    logger.info(
        "Report retrieval requested",
        extra={
            "trace_id": trace_id,
            "request_id": request_id,
        }
    )

    try:
        from uuid import UUID
        request_uuid = UUID(request_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_request_id",
                "message": "Invalid request ID format",
            }
        )

    request_data = request_store.get_request(request_uuid)

    if not request_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "not_found",
                "message": "Request not found",
            }
        )

    status_code = status.HTTP_200_OK
    if request_data["status"] == RequestStatus.PROCESSING:
        status_code = status.HTTP_202_ACCEPTED

    return ReportResponse(
        request_id=request_uuid,
        status=request_data["status"],
        report=request_data["report"],
    )
