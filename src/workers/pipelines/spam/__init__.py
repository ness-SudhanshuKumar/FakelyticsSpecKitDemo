"""Spam pipeline exports."""

from src.workers.pipelines.spam.detector import analyze_spam_and_source

__all__ = ["analyze_spam_and_source"]
