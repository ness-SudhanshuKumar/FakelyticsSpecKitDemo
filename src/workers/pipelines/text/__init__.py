"""Text verification pipeline module

This module handles text-based fact-checking and credibility verification.
It includes text extraction, preprocessing, fact-checking, and NLP analysis.
"""

from src.workers.pipelines.text.preprocessor import (
    TextPreprocessor,
    PreprocessedText,
    TextMetadata,
    Language,
    get_preprocessor,
    preprocess_text_task,
)

from src.workers.pipelines.text.factchecker import (
    Verdict,
    Evidence,
    ClaimFinding,
    ClaimExtractor,
    FactChecker,
    MockFactCheckProvider,
    FactCheckSearchProvider,
    get_claim_extractor,
    get_fact_checker,
    fact_check_task,
)

__all__ = [
    "TextPreprocessor",
    "PreprocessedText",
    "TextMetadata",
    "Language",
    "get_preprocessor",
    "preprocess_text_task",
    "Verdict",
    "Evidence",
    "ClaimFinding",
    "ClaimExtractor",
    "FactChecker",
    "MockFactCheckProvider",
    "FactCheckSearchProvider",
    "get_claim_extractor",
    "get_fact_checker",
    "fact_check_task",
]

