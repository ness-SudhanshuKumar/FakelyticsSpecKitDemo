"""
Text extraction and preprocessing pipeline module

Satisfies T-301: Extract and preprocess text from ContentExtract for text analysis.

This module handles:
- Text extraction from ContentExtract models
- HTML tag and formatting cleaning
- Multiple language detection (NLP)
- Text tokenization and normalization
- Return of preprocessed text for downstream analysis
"""

import logging
import re
import string
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

try:
    import langdetect
    from langdetect import detect, detect_langs
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False
    
try:
    import nltk
    from nltk.tokenize import sent_tokenize, word_tokenize
    from nltk.corpus import stopwords
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False

logger = logging.getLogger(__name__)


class Language(str, Enum):
    """Supported languages for text analysis"""
    ENGLISH = "en"
    SPANISH = "es"
    FRENCH = "fr"
    GERMAN = "de"
    PORTUGUESE = "pt"
    ITALIAN = "it"
    DUTCH = "nl"
    RUSSIAN = "ru"
    CHINESE = "zh"
    JAPANESE = "ja"
    ARABIC = "ar"
    HINDI = "hi"
    KOREAN = "ko"
    UNKNOWN = "unknown"


@dataclass
class TextMetadata:
    """Metadata about preprocessed text"""
    original_length: int
    cleaned_length: int
    languages: List[str]
    detected_language: str
    num_sentences: int
    num_tokens: int
    has_urls: bool
    has_emails: bool
    avg_word_length: float


@dataclass
class PreprocessedText:
    """Result of text preprocessing"""
    original_text: str
    cleaned_text: str
    sentences: List[str]
    tokens: List[str]
    metadata: TextMetadata
    
    def __repr__(self) -> str:
        return (
            f"PreprocessedText(cleaned_length={self.metadata.cleaned_length}, "
            f"language={self.metadata.detected_language}, "
            f"sentences={self.metadata.num_sentences})"
        )


class TextPreprocessor:
    """
    Preprocesses text for verification pipelines.
    
    Satisfies T-301 acceptance criteria:
    - Extracts text content from ContentExtract ✓
    - Cleans HTML tags and formatting ✓
    - Handles multiple languages (NLP detection) ✓
    - Tokenizes and normalizes text ✓
    - Returns preprocessed text for analysis ✓
    """
    
    # URL and email patterns
    URL_PATTERN = re.compile(
        r'https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&/=]*)'
    )
    EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    
    # HTML tag pattern
    HTML_TAG_PATTERN = re.compile(r'<[^>]+>')
    
    # Whitespace normalization pattern
    WHITESPACE_PATTERN = re.compile(r'\s+')
    
    def __init__(self):
        """Initialize text preprocessor"""
        self.logger = logger
        self._ensure_nltk_data()
    
    @staticmethod
    def _ensure_nltk_data():
        """Ensure NLTK data is downloaded (punkt tokenizer)"""
        if NLTK_AVAILABLE:
            try:
                nltk.data.find('tokenizers/punkt')
            except LookupError:
                try:
                    nltk.download('punkt', quiet=True)
                except Exception as e:
                    logger.warning(f"Could not download NLTK punkt data: {e}")
    
    def preprocess(self, text: str, language: Optional[str] = None) -> PreprocessedText:
        """
        Preprocess text for analysis.
        
        Args:
            text: Raw text content to preprocess
            language: Optional language code (if known)
            
        Returns:
            PreprocessedText with cleaned and tokenized content
            
        Raises:
            ValueError: If text is empty or invalid
        """
        if not text or not isinstance(text, str):
            raise ValueError(f"Invalid text input: {type(text)}")
        
        if len(text.strip()) == 0:
            raise ValueError("Text content is empty")
        
        original_length = len(text)
        
        # Step 1: Remove HTML tags
        text_no_html = self._remove_html_tags(text)
        
        # Step 2: Normalize whitespace
        text_normalized = self._normalize_whitespace(text_no_html)
        
        # Step 3: Detect language(s)
        detected_language, all_languages = self._detect_language(text_normalized, language)
        
        # Step 4: Clean text (remove special chars, normalize)
        cleaned_text = self._clean_text(text_normalized)
        
        # Step 5: Extract features before tokenization
        has_urls = bool(self.URL_PATTERN.search(text))
        has_emails = bool(self.EMAIL_PATTERN.search(text))
        
        # Step 6: Tokenize into sentences
        sentences = self._tokenize_sentences(cleaned_text)
        
        # Step 7: Tokenize into words
        tokens = self._tokenize_words(cleaned_text)
        
        # Step 8: Create metadata
        avg_word_length = (
            sum(len(token) for token in tokens) / len(tokens)
            if tokens else 0
        )
        
        metadata = TextMetadata(
            original_length=original_length,
            cleaned_length=len(cleaned_text),
            languages=all_languages,
            detected_language=detected_language,
            num_sentences=len(sentences),
            num_tokens=len(tokens),
            has_urls=has_urls,
            has_emails=has_emails,
            avg_word_length=avg_word_length,
        )
        
        result = PreprocessedText(
            original_text=text,
            cleaned_text=cleaned_text,
            sentences=sentences,
            tokens=tokens,
            metadata=metadata,
        )
        
        self.logger.info(
            f"Text preprocessed: {original_length} → {len(cleaned_text)} chars, "
            f"language={detected_language}, sentences={len(sentences)}, tokens={len(tokens)}"
        )
        
        return result
    
    def _remove_html_tags(self, text: str) -> str:
        """Remove HTML tags and entities from text"""
        # Remove script and style elements
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove HTML tags
        text = self.HTML_TAG_PATTERN.sub(' ', text)
        
        # Decode common HTML entities
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&amp;', '&')
        text = text.replace('&quot;', '"')
        text = text.replace('&#39;', "'")
        
        return text
    
    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace by replacing multiple spaces with single space"""
        text = self.WHITESPACE_PATTERN.sub(' ', text)
        return text.strip()
    
    def _detect_language(self, text: str, hint_language: Optional[str] = None) -> tuple[str, List[str]]:
        """
        Detect the language(s) of the text.
        
        Args:
            text: Text to analyze
            hint_language: Optional language hint
            
        Returns:
            Tuple of (primary_language_code, all_detected_languages)
        """
        if hint_language:
            # If hint provided, use it
            return hint_language, [hint_language]
        
        if not LANGDETECT_AVAILABLE:
            self.logger.warning("langdetect not available, defaulting to English")
            return Language.ENGLISH.value, [Language.ENGLISH.value]
        
        try:
            # Use a sample if text is very long (langdetect works better on shorter text)
            sample = text[:1000] if len(text) > 1000 else text
            
            # Get primary language
            primary = detect(sample)
            
            # Get all probabilities
            all_langs = detect_langs(sample)
            all_detected = [str(lang).split('_')[0] for lang in all_langs]
            
            self.logger.debug(f"Detected languages: {all_detected}")
            return primary, all_detected
            
        except Exception as e:
            self.logger.warning(f"Language detection failed: {e}, defaulting to unknown")
            return Language.UNKNOWN.value, [Language.UNKNOWN.value]
    
    def _clean_text(self, text: str) -> str:
        """
        Clean and normalize text content.
        
        This includes:
        - Removing/normalizing special characters
        - Normalizing quotes
        - Removing control characters
        - Preserving sentence structure
        """
        # Normalize quotes
        text = re.sub(r'["""]', '"', text)
        text = re.sub(r"['']", "'", text)
        
        # Remove control characters but preserve newlines
        text = ''.join(ch for ch in text if ch.isprintable() or ch in '\n\t')
        
        # Preserve sentence breaks by normalizing ellipsis
        text = re.sub(r'\.{2,}', '.', text)
        text = re.sub(r'([!?]){2,}', r'\1', text)
        
        # Add space after punctuation if missing (but not in numbers/decimals)
        text = re.sub(r'([.!?])([A-Z])', r'\1 \2', text)
        
        # Normalize multiple punctuation
        text = re.sub(r'([,;:])\s*\1+', r'\1', text)
        
        return text.strip()
    
    def _tokenize_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences.
        
        Args:
            text: Cleaned text
            
        Returns:
            List of sentences
        """
        if NLTK_AVAILABLE:
            try:
                sentences = sent_tokenize(text)
                return [s.strip() for s in sentences if s.strip()]
            except Exception as e:
                self.logger.warning(f"NLTK sentence tokenization failed: {e}, using simple split")
        
        # Fallback: simple sentence split on punctuation
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _tokenize_words(self, text: str) -> List[str]:
        """
        Split text into word tokens.
        
        Args:
            text: Cleaned text
            
        Returns:
            List of word tokens
        """
        if NLTK_AVAILABLE:
            try:
                # Use NLTK word tokenizer for better handling
                tokens = word_tokenize(text.lower())
                # Filter out pure punctuation tokens
                tokens = [t for t in tokens if any(c.isalnum() for c in t)]
                return tokens
            except Exception as e:
                self.logger.warning(f"NLTK word tokenization failed: {e}, using simple split")
        
        # Fallback: simple word tokenization
        # Split on whitespace and punctuation
        text = re.sub(r'[' + re.escape(string.punctuation) + r']', ' ', text)
        tokens = text.lower().split()
        return [t for t in tokens if t]
    
    def extract_and_preprocess(self, content_extract) -> PreprocessedText:
        """
        Extract text from ContentExtract and preprocess it.
        
        This is a convenience method that works directly with ContentExtract objects
        from the extraction service.
        
        Args:
            content_extract: ContentExtract object from extraction service
            
        Returns:
            PreprocessedText with cleaned and tokenized content
            
        Raises:
            ValueError: If ContentExtract has no text content
        """
        if not hasattr(content_extract, 'text_content'):
            raise ValueError(
                f"Invalid ContentExtract object: missing text_content attribute"
            )
        
        if not content_extract.text_content:
            raise ValueError("ContentExtract contains no text content")
        
        self.logger.info(
            f"Extracting text from URL: {getattr(content_extract, 'url', 'unknown')}"
        )
        
        return self.preprocess(content_extract.text_content)
    
    def get_summary_stats(self, preprocessed: PreprocessedText) -> Dict[str, Any]:
        """
        Get summary statistics about preprocessed text.
        
        Args:
            preprocessed: PreprocessedText object
            
        Returns:
            Dictionary of statistics
        """
        metadata = preprocessed.metadata
        
        # Calculate reading time (avg 200 words per minute)
        reading_time_minutes = len(preprocessed.tokens) / 200
        
        # Calculate compression ratio
        compression_ratio = (
            metadata.cleaned_length / metadata.original_length
            if metadata.original_length > 0 else 0
        )
        
        return {
            "original_length": metadata.original_length,
            "cleaned_length": metadata.cleaned_length,
            "compression_ratio": compression_ratio,
            "language": metadata.detected_language,
            "all_detected_languages": metadata.languages,
            "num_sentences": metadata.num_sentences,
            "num_tokens": metadata.num_tokens,
            "avg_sentence_length": (
                len(preprocessed.tokens) / len(preprocessed.sentences)
                if preprocessed.sentences else 0
            ),
            "avg_word_length": metadata.avg_word_length,
            "reading_time_minutes": reading_time_minutes,
            "has_urls": metadata.has_urls,
            "has_emails": metadata.has_emails,
        }


# Global instance
_preprocessor: Optional[TextPreprocessor] = None


def get_preprocessor() -> TextPreprocessor:
    """Get or create global TextPreprocessor instance"""
    global _preprocessor
    if _preprocessor is None:
        _preprocessor = TextPreprocessor()
    return _preprocessor


# Celery task for asynchronous text preprocessing
def preprocess_text_task(text: str, language: Optional[str] = None) -> Dict[str, Any]:
    """
    Celery task wrapper for text preprocessing.
    
    This can be called asynchronously via Celery for large text processing.
    
    Args:
        text: Raw text to preprocess
        language: Optional language hint
        
    Returns:
        Dictionary representation of PreprocessedText for JSON serialization
    """
    try:
        preprocessor = get_preprocessor()
        preprocessed = preprocessor.preprocess(text, language)
        
        # Return dict-serializable result
        return {
            "success": True,
            "original_text": preprocessed.original_text,
            "cleaned_text": preprocessed.cleaned_text,
            "sentences": preprocessed.sentences,
            "tokens": preprocessed.tokens,
            "metadata": {
                "original_length": preprocessed.metadata.original_length,
                "cleaned_length": preprocessed.metadata.cleaned_length,
                "languages": preprocessed.metadata.languages,
                "detected_language": preprocessed.metadata.detected_language,
                "num_sentences": preprocessed.metadata.num_sentences,
                "num_tokens": preprocessed.metadata.num_tokens,
                "has_urls": preprocessed.metadata.has_urls,
                "has_emails": preprocessed.metadata.has_emails,
                "avg_word_length": preprocessed.metadata.avg_word_length,
            }
        }
    except Exception as e:
        logger.error(f"Text preprocessing task failed: {e}")
        return {
            "success": False,
            "error": str(e),
        }
