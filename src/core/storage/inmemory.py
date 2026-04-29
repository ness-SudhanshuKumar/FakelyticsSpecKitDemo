"""In-memory storage for verification requests and reports (for MVP)"""

import logging
from typing import Dict, Optional
from uuid import UUID
from datetime import datetime
from threading import Lock

from src.api.models.schemas import (
    VerifyRequest,
    CredibilityReport,
    RequestStatus,
    Findings,
    PipelineResult,
)

logger = logging.getLogger(__name__)


class InMemoryRequestStore:
    """In-memory storage for verification requests and reports"""

    def __init__(self):
        """Initialize storage"""
        self._requests: Dict[str, dict] = {}
        self._lock = Lock()

    def create_request(
        self,
        request_id: UUID,
        url: str,
        async_mode: bool = False,
        webhook_url: Optional[str] = None,
    ) -> dict:
        """Create a new verification request"""
        with self._lock:
            request_data = {
                "request_id": str(request_id),
                "url": url,
                "status": RequestStatus.PENDING,
                "created_at": datetime.utcnow(),
                "completed_at": None,
                "async_mode": async_mode,
                "webhook_url": webhook_url,
                "report": None,
                "error_message": None,
            }
            self._requests[str(request_id)] = request_data
            logger.info(f"Created request {request_id} for URL: {url}")
            return request_data

    def get_request(self, request_id: UUID) -> Optional[dict]:
        """Get a request by ID"""
        with self._lock:
            return self._requests.get(str(request_id))

    def update_status(
        self,
        request_id: UUID,
        status: RequestStatus,
    ) -> bool:
        """Update request status"""
        with self._lock:
            request_id_str = str(request_id)
            if request_id_str not in self._requests:
                return False
            self._requests[request_id_str]["status"] = status
            logger.info(f"Updated request {request_id} status to {status}")
            return True

    def set_report(
        self,
        request_id: UUID,
        report: CredibilityReport,
    ) -> bool:
        """Set completed report"""
        with self._lock:
            request_id_str = str(request_id)
            if request_id_str not in self._requests:
                return False
            self._requests[request_id_str]["report"] = report
            self._requests[request_id_str]["status"] = RequestStatus.COMPLETED
            self._requests[request_id_str]["completed_at"] = datetime.utcnow()
            logger.info(f"Set report for request {request_id}")
            return True

    def set_error(
        self,
        request_id: UUID,
        error_message: str,
    ) -> bool:
        """Mark request as failed with error"""
        with self._lock:
            request_id_str = str(request_id)
            if request_id_str not in self._requests:
                return False
            self._requests[request_id_str]["status"] = RequestStatus.FAILED
            self._requests[request_id_str]["error_message"] = error_message
            self._requests[request_id_str]["completed_at"] = datetime.utcnow()
            logger.error(f"Set error for request {request_id}: {error_message}")
            return True


# Global instance
request_store = InMemoryRequestStore()

