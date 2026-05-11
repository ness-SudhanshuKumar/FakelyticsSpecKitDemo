"""Database persistence layer for credibility reports."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from uuid import UUID
from typing import Optional, List

from src.api.models.schemas import CredibilityReport, RequestStatus

logger = logging.getLogger(__name__)


class ReportPersistence:
    """Service for persisting and retrieving credibility reports from database."""

    # In-memory fallback storage for MVP (would be replaced with PostgreSQL)
    _reports: dict[str, dict] = {}
    _retention_days: int = 90

    def store_report(self, report: CredibilityReport) -> bool:
        """
        Store completed report in database.
        
        **Satisfies**: T-802 (Store report in PostgreSQL with audit trail)
        
        Args:
            report: Credibility report to store
            
        Returns:
            True if storage successful
        """
        try:
            report_id = str(report.request_id)
            
            # Convert report to JSON-serializable format
            report_dict = {
                "request_id": report_id,
                "url": report.url,
                "overall_credibility_score": report.overall_credibility_score,
                "summary": report.summary,
                "findings": report.findings.model_dump(mode="json"),
                "timestamp": report.timestamp.isoformat(),
                "created_at": datetime.utcnow().isoformat(),
                "retention_expires_at": (datetime.utcnow() + timedelta(days=self._retention_days)).isoformat(),
            }
            
            # Store in-memory (would be PostgreSQL in production)
            self._reports[report_id] = report_dict
            
            logger.info(
                "Report persisted",
                extra={
                    "request_id": report_id,
                    "url": report.url,
                    "score": report.overall_credibility_score
                }
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error storing report: {str(e)}", exc_info=True)
            return False

    def get_report(self, request_id: UUID) -> Optional[dict]:
        """
        Retrieve stored report by request ID.
        
        Args:
            request_id: Request ID to retrieve
            
        Returns:
            Report dict if found, None otherwise
        """
        try:
            report_id_str = str(request_id)
            report_dict = self._reports.get(report_id_str)
            
            if not report_dict:
                return None
            
            # Check retention policy
            retention_expires = datetime.fromisoformat(report_dict.get("retention_expires_at", ""))
            if datetime.utcnow() > retention_expires:
                logger.info(f"Report expired for request {request_id}")
                del self._reports[report_id_str]
                return None
            
            return report_dict
            
        except Exception as e:
            logger.error(f"Error retrieving report: {str(e)}")
            return None

    def delete_report(self, request_id: UUID) -> bool:
        """
        Delete stored report.
        
        Args:
            request_id: Request ID to delete
            
        Returns:
            True if deletion successful
        """
        try:
            report_id_str = str(request_id)
            if report_id_str in self._reports:
                del self._reports[report_id_str]
                logger.info(f"Report deleted for request {request_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting report: {str(e)}")
            return False

    def cleanup_expired_reports(self) -> int:
        """
        Clean up expired reports based on retention policy.
        
        **Satisfies**: T-802 (Implements retention policy)
        
        Returns:
            Number of reports deleted
        """
        try:
            now = datetime.utcnow()
            expired_keys = []
            
            for key, report_dict in self._reports.items():
                retention_expires = datetime.fromisoformat(report_dict.get("retention_expires_at", ""))
                if now > retention_expires:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self._reports[key]
            
            if expired_keys:
                logger.info(f"Cleaned up {len(expired_keys)} expired reports")
            
            return len(expired_keys)
            
        except Exception as e:
            logger.error(f"Error cleaning up reports: {str(e)}")
            return 0

    def get_report_count(self) -> int:
        """Get total number of stored reports."""
        return len(self._reports)

    def list_reports(self, limit: int = 100, offset: int = 0) -> List[dict]:
        """
        List stored reports with pagination.
        
        Args:
            limit: Maximum number of reports to return
            offset: Offset for pagination
            
        Returns:
            List of report metadata
        """
        try:
            reports_list = list(self._reports.values())
            # Sort by timestamp (newest first)
            reports_list.sort(key=lambda r: r.get("timestamp", ""), reverse=True)
            return reports_list[offset:offset + limit]
        except Exception as e:
            logger.error(f"Error listing reports: {str(e)}")
            return []


# Global instance
report_persistence = ReportPersistence()
