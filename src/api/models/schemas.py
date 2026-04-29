"""Pydantic models for API requests and responses"""

from pydantic import BaseModel, Field, HttpUrl, field_validator
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime
from uuid import UUID, uuid4


class RequestStatus(str, Enum):
    """Status of a verification request"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Verdict(str, Enum):
    """Verdict on content credibility"""
    SUPPORTED = "Supported"
    DISPUTED = "Disputed"
    UNVERIFIABLE = "Unverifiable"


class PipelineType(str, Enum):
    """Types of verification pipelines"""
    TEXT = "text"
    IMAGE = "image"
    AUDIO_VIDEO = "audio_video"
    SPAM = "spam"


# Request Models

class RequestOptions(BaseModel):
    """Options for verification request"""
    async_mode: bool = Field(default=False, description="Run verification asynchronously")
    webhook_url: Optional[HttpUrl] = Field(default=None, description="Callback URL for async results")
    timeout_seconds: int = Field(default=60, ge=10, le=300, description="Maximum processing time")
    pipelines: Optional[List[PipelineType]] = Field(default=None, description="Which pipelines to run")

    class Config:
        use_enum_values = True


class VerifyRequest(BaseModel):
    """Request to verify a URL"""
    url: str = Field(..., max_length=2048, description="URL to verify")
    options: Optional[RequestOptions] = Field(default_factory=RequestOptions, description="Verification options")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v):
        """Validate URL format"""
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        if len(v) > 2048:
            raise ValueError("URL too long (max 2048 characters)")
        return v

    class Config:
        use_enum_values = True


# Response Models

class Evidence(BaseModel):
    """Evidence source for a finding"""
    url: str = Field(..., description="URL of evidence source")
    snippet: str = Field(..., description="Relevant snippet from source")
    title: Optional[str] = Field(None, description="Title of source")
    validated: bool = Field(default=False, description="Whether evidence URL is accessible")
    validated_at: Optional[datetime] = None

    class Config:
        use_enum_values = True


class Finding(BaseModel):
    """A single finding from a pipeline"""
    id: UUID = Field(default_factory=uuid4, description="Unique finding ID")
    summary: str = Field(..., description="Brief description of finding")
    verdict: Verdict = Field(..., description="Verdict on this finding")
    confidence: int = Field(..., ge=0, le=100, description="Confidence score 0-100")
    evidence: List[Evidence] = Field(default_factory=list, description="Evidence supporting finding")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Pipeline-specific data")

    class Config:
        use_enum_values = True


class PipelineResult(BaseModel):
    """Result from a single verification pipeline"""
    verdict: Verdict = Field(..., description="Overall verdict for this pipeline")
    confidence: int = Field(..., ge=0, le=100, description="Overall confidence for this pipeline")
    findings: List[Finding] = Field(default_factory=list, description="Individual findings")

    class Config:
        use_enum_values = True


class Findings(BaseModel):
    """Results from all verification pipelines"""
    text: Optional[PipelineResult] = Field(None, description="Text verification results")
    image: Optional[PipelineResult] = Field(None, description="Image verification results")
    audio_video: Optional[PipelineResult] = Field(None, description="Audio/video verification results")
    spam: Optional[PipelineResult] = Field(None, description="Spam detection results")

    class Config:
        use_enum_values = True


class CredibilityReport(BaseModel):
    """Complete credibility report for verified content"""
    request_id: UUID = Field(..., description="Unique request identifier")
    url: str = Field(..., description="URL that was verified")
    overall_credibility_score: int = Field(..., ge=0, le=100, description="Overall credibility score")
    summary: str = Field(..., description="Human-readable summary")
    findings: Findings = Field(..., description="Findings from all pipelines")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Report generation time")

    class Config:
        use_enum_values = True


class VerifyResponse(BaseModel):
    """Response to verification request"""
    request_id: UUID = Field(..., description="Unique request identifier")
    status: RequestStatus = Field(..., description="Current status")
    report: Optional[CredibilityReport] = Field(None, description="Report if completed")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Request creation time")
    completed_at: Optional[datetime] = Field(None, description="Request completion time")

    class Config:
        use_enum_values = True


class ReportResponse(BaseModel):
    """Response with report retrieval"""
    request_id: UUID = Field(..., description="Unique request identifier")
    status: RequestStatus = Field(..., description="Current status")
    report: Optional[CredibilityReport] = Field(None, description="Report if ready")

    class Config:
        use_enum_values = True


class WebhookPayload(BaseModel):
    """Payload sent to webhook URL"""
    request_id: UUID = Field(..., description="Request ID")
    status: str = Field(..., description="Final status")
    report: Optional[CredibilityReport] = Field(None, description="Completed report")
    error_message: Optional[str] = Field(None, description="Error if failed")

    class Config:
        use_enum_values = True


# Error Models

class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")

    class Config:
        use_enum_values = True


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="System status")
    version: str = Field(..., description="API version")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Check time")
