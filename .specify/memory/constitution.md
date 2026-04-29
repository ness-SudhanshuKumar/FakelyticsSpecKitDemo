# Fakelytics Constitution

## Core Principles

### I. Modular Pipeline Architecture
Every verification modality (text, image, audio, video, spam) MUST be an isolated, independently testable module. Each module MUST have a clear, single purpose and MUST NOT depend on other modules for its core verification logic. Modules MUST be self-contained with their own dependencies, configuration, and test suites.

### II. Concurrent Processing
All verification pipelines MUST run concurrently. The system MUST NOT allow one pipeline's failure or slowness to block others. If a pipeline finds nothing or fails, the report MUST still complete with partial results. The overall system MUST remain functional even when individual pipelines are unavailable.

### III. Evidence-Based Verdict (NON-NEGOTIABLE)
Every finding MUST include: confidence score (0-100), verdict (Supported / Disputed / Unverifiable), and cited evidence. The system MUST NEVER return a verdict without evidence. Findings without verifiable evidence MUST be marked as Unverifiable. All evidence sources MUST be traceable and auditable.

### IV. Dual Output Format
Every report MUST provide both human-readable summary AND machine-readable JSON output. The JSON output MUST follow a consistent schema for API consumers. The human summary MUST be understandable by non-technical users while the JSON provides full detail for programmatic access.

### V. API-First Design
The platform MUST be designed primarily for API consumption. All features MUST have corresponding API endpoints. Response schemas MUST be versioned and backward-compatible. The API MUST support both synchronous requests and webhook-based async callbacks for long-running verifications.

## Technology Standards

**AI/ML Pipeline Requirements**:
- Each modality pipeline MUST use industry-standard AI/ML models for detection
- Models MUST be versioned and replaceable without breaking the API contract
- All AI predictions MUST include confidence scores and explanation traces

**Performance Standards**:
- Individual pipeline response time target: <30 seconds
- Overall report generation target: <60 seconds for complete analysis
- System MUST handle concurrent requests with proper queue management

**Data Handling**:
- All extracted content MUST be processed in memory where possible
- Persistent storage only for audit logs and user data (with consent)
- Evidence URLs MUST be validated for accessibility before citation

## Development Workflow

**Testing Requirements**:
- Unit tests REQUIRED for every pipeline module
- Integration tests REQUIRED for inter-pipeline communication
- Contract tests REQUIRED for API response schemas
- Each user story MUST be independently testable

**Code Review**:
- All PRs MUST verify compliance with modular architecture
- Changes to pipeline modules MUST include corresponding test updates
- API schema changes MUST be documented with migration notes

**Versioning**:
- Use MAJOR.MINOR.PATCH format
- MAJOR: Breaking API changes or pipeline replacement
- MINOR: New pipeline or significant feature addition
- PATCH: Bug fixes and performance improvements

## Governance

This constitution supersedes all other development practices. All PRs and reviews MUST verify compliance with these principles. Complexity additions MUST be justified with clear rationale.

Amendments to this constitution require:
1. Written proposal documenting the change
2. Review and approval from at least one maintainer
3. Migration plan if changes affect existing implementations
4. Update to version following semantic versioning rules

**Version**: 1.0.0 | **Ratified**: 2026-04-27 | **Last Amended**: 2026-04-27
