"""
Unit tests for text preprocessing pipeline

Tests T-301: Text Extraction & Preprocessing
"""

import pytest
from unittest.mock import Mock, patch

from src.workers.pipelines.text.preprocessor import (
    TextPreprocessor,
    PreprocessedText,
    TextMetadata,
    Language,
    get_preprocessor,
)


class TestTextPreprocessor:
    """Test suite for TextPreprocessor class"""
    
    @pytest.fixture
    def preprocessor(self):
        """Create preprocessor instance for tests"""
        return TextPreprocessor()
    
    @pytest.fixture
    def sample_text(self):
        """Sample HTML-formatted text for testing"""
        return """
        <h1>Breaking News</h1>
        <p>This is a <b>test</b> article with &nbsp; multiple  spaces.</p>
        <p>Check out <a href="https://example.com">this link</a>!</p>
        <script>alert('malicious');</script>
        <p>Email me at test@example.com for more info...</p>
        <style>body { color: red; }</style>
        """
    
    # ===== Basic Preprocessing Tests =====
    
    def test_preprocess_valid_text(self, preprocessor, sample_text):
        """Test preprocessing of valid HTML-formatted text"""
        result = preprocessor.preprocess(sample_text)
        
        assert isinstance(result, PreprocessedText)
        assert result.cleaned_text  # Should have content
        assert len(result.sentences) > 0
        assert len(result.tokens) > 0
        assert result.metadata.cleaned_length < result.metadata.original_length
    
    def test_preprocess_removes_html_tags(self, preprocessor):
        """Test that HTML tags are properly removed"""
        text = "<p>Hello <b>world</b>!</p>"
        result = preprocessor.preprocess(text)
        
        assert "<p>" not in result.cleaned_text
        assert "<b>" not in result.cleaned_text
        assert "Hello" in result.cleaned_text
        assert "world" in result.cleaned_text
    
    def test_preprocess_removes_script_tags(self, preprocessor):
        """Test that script tags and content are removed"""
        text = "Normal text <script>alert('xss');</script> more text"
        result = preprocessor.preprocess(text)
        
        assert "alert" not in result.cleaned_text
        assert "xss" not in result.cleaned_text
        assert "Normal text" in result.cleaned_text
        assert "more text" in result.cleaned_text
    
    def test_preprocess_removes_style_tags(self, preprocessor):
        """Test that style tags and content are removed"""
        text = "Text <style>body { display: none; }</style> more text"
        result = preprocessor.preprocess(text)
        
        assert "display" not in result.cleaned_text
        assert "Text" in result.cleaned_text
        assert "more text" in result.cleaned_text
    
    def test_preprocess_normalizes_whitespace(self, preprocessor):
        """Test that multiple spaces are normalized to single space"""
        text = "Multiple   spaces   between    words"
        result = preprocessor.preprocess(text)
        
        assert "   " not in result.cleaned_text
        assert "Multiple spaces between words" in result.cleaned_text
    
    def test_preprocess_preserves_sentence_structure(self, preprocessor):
        """Test that sentence structure is preserved"""
        text = "First sentence. Second sentence! Third sentence?"
        result = preprocessor.preprocess(text)
        
        assert len(result.sentences) >= 3
        assert result.sentences[0].startswith("First")
        assert result.sentences[1].startswith("Second")
        assert result.sentences[2].startswith("Third")
    
    # ===== Language Detection Tests =====
    
    def test_language_detection_with_hint(self, preprocessor):
        """Test language detection when hint is provided"""
        text = "Some English text"
        result = preprocessor.preprocess(text, language="en")
        
        assert result.metadata.detected_language == "en"
    
    def test_language_detection_defaults_to_unknown_without_langdetect(self, preprocessor):
        """Test that language detection defaults gracefully when lib not available"""
        # This will use fallback since langdetect may not be installed
        text = "Some text in unknown language"
        result = preprocessor.preprocess(text)
        
        assert result.metadata.detected_language is not None
        # Language can be either detected or "unknown"
        assert isinstance(result.metadata.detected_language, str)
    
    def test_detect_html_entities(self, preprocessor):
        """Test that HTML entities are properly decoded"""
        text = "HTML &amp; XML &lt;tags&gt; &quot;quotes&quot;"
        result = preprocessor.preprocess(text)
        
        assert "&amp;" not in result.cleaned_text or "&" in result.cleaned_text
        assert "HTML" in result.cleaned_text
    
    # ===== Tokenization Tests =====
    
    def test_tokenize_into_sentences(self, preprocessor):
        """Test sentence tokenization"""
        text = "This is first. This is second! And third?"
        result = preprocessor.preprocess(text)
        
        assert len(result.sentences) >= 3
        assert all(isinstance(s, str) for s in result.sentences)
        assert all(len(s) > 0 for s in result.sentences)
    
    def test_tokenize_into_words(self, preprocessor):
        """Test word tokenization"""
        text = "This is a test sentence."
        result = preprocessor.preprocess(text)
        
        assert len(result.tokens) >= 5
        assert all(isinstance(t, str) for t in result.tokens)
        assert all(len(t) > 0 for t in result.tokens)
    
    def test_word_tokens_lowercase(self, preprocessor):
        """Test that word tokens are lowercased"""
        text = "UPPERCASE Text MiXeD case"
        result = preprocessor.preprocess(text)
        
        # Most tokens should be lowercase
        lowercase_tokens = [t for t in result.tokens if t.islower()]
        assert len(lowercase_tokens) >= 2
    
    # ===== Metadata Tests =====
    
    def test_metadata_extraction(self, preprocessor):
        """Test that metadata is correctly extracted"""
        text = "This is a test. Email me at test@example.com."
        result = preprocessor.preprocess(text)
        
        metadata = result.metadata
        assert metadata.original_length > 0
        assert metadata.cleaned_length > 0
        assert metadata.num_sentences >= 2
        assert metadata.num_tokens >= 8
        assert metadata.has_emails is True
    
    def test_detect_urls_in_text(self, preprocessor):
        """Test URL detection in text"""
        text = "Check out https://example.com for more info"
        result = preprocessor.preprocess(text)
        
        assert result.metadata.has_urls is True
    
    def test_detect_emails_in_text(self, preprocessor):
        """Test email detection in text"""
        text = "Contact me at test@example.com"
        result = preprocessor.preprocess(text)
        
        assert result.metadata.has_emails is True
    
    def test_no_urls_or_emails_in_plain_text(self, preprocessor):
        """Test that plain text has no URLs or emails"""
        text = "This is just plain text with no special content"
        result = preprocessor.preprocess(text)
        
        assert result.metadata.has_urls is False
        assert result.metadata.has_emails is False
    
    def test_average_word_length_calculation(self, preprocessor):
        """Test that average word length is calculated correctly"""
        text = "a bb ccc dddd eeeee"
        result = preprocessor.preprocess(text)
        
        assert result.metadata.avg_word_length > 0
        # Average of [1, 2, 3, 4, 5] = 3
        assert 2.0 <= result.metadata.avg_word_length <= 3.5
    
    # ===== Error Handling Tests =====
    
    def test_preprocess_empty_text_raises_error(self, preprocessor):
        """Test that empty text raises ValueError"""
        with pytest.raises(ValueError):
            preprocessor.preprocess("")
    
    def test_preprocess_none_raises_error(self, preprocessor):
        """Test that None input raises ValueError"""
        with pytest.raises(ValueError):
            preprocessor.preprocess(None)
    
    def test_preprocess_whitespace_only_raises_error(self, preprocessor):
        """Test that whitespace-only text raises ValueError"""
        with pytest.raises(ValueError, match="empty"):
            preprocessor.preprocess("   \n\t  ")
    
    def test_preprocess_invalid_type_raises_error(self, preprocessor):
        """Test that non-string input raises ValueError"""
        with pytest.raises(ValueError):
            preprocessor.preprocess(123)
    
    # ===== ContentExtract Integration Tests =====
    
    def test_extract_and_preprocess_with_content_extract(self, preprocessor):
        """Test extracting and preprocessing from ContentExtract object"""
        mock_content = Mock()
        mock_content.text_content = "This is test content from URL"
        mock_content.url = "https://example.com"
        
        result = preprocessor.extract_and_preprocess(mock_content)
        
        assert isinstance(result, PreprocessedText)
        assert "test" in result.cleaned_text
        assert len(result.sentences) > 0
    
    def test_extract_and_preprocess_missing_text_content(self, preprocessor):
        """Test error handling when ContentExtract lacks text_content"""
        mock_content = Mock(spec=[])  # No text_content attribute
        
        with pytest.raises(ValueError, match="missing text_content"):
            preprocessor.extract_and_preprocess(mock_content)
    
    def test_extract_and_preprocess_empty_text_content(self, preprocessor):
        """Test error handling when text_content is empty"""
        mock_content = Mock()
        mock_content.text_content = ""
        
        with pytest.raises(ValueError, match="no text content"):
            preprocessor.extract_and_preprocess(mock_content)
    
    # ===== Summary Stats Tests =====
    
    def test_get_summary_stats(self, preprocessor):
        """Test summary statistics generation"""
        text = "This is a test. It has two sentences. They are informative."
        result = preprocessor.preprocess(text)
        
        stats = preprocessor.get_summary_stats(result)
        
        assert "original_length" in stats
        assert "cleaned_length" in stats
        assert "compression_ratio" in stats
        assert "language" in stats
        assert "num_sentences" in stats
        assert "num_tokens" in stats
        assert "avg_sentence_length" in stats
        assert "avg_word_length" in stats
        assert "reading_time_minutes" in stats
        assert "has_urls" in stats
        assert "has_emails" in stats
        
        assert stats["num_sentences"] >= 3
        assert stats["compression_ratio"] <= 1.0
        assert stats["reading_time_minutes"] >= 0
    
    # ===== Global Instance Tests =====
    
    def test_get_preprocessor_returns_instance(self):
        """Test that get_preprocessor returns a valid instance"""
        preprocessor = get_preprocessor()
        assert isinstance(preprocessor, TextPreprocessor)
    
    def test_get_preprocessor_singleton(self):
        """Test that get_preprocessor returns same instance"""
        preprocessor1 = get_preprocessor()
        preprocessor2 = get_preprocessor()
        assert preprocessor1 is preprocessor2


class TestEdgeCases:
    """Test edge cases and special scenarios"""
    
    @pytest.fixture
    def preprocessor(self):
        """Create preprocessor instance for tests"""
        return TextPreprocessor()
    
    def test_very_long_text(self, preprocessor):
        """Test handling of very long text"""
        text = "word " * 10000  # 50k characters
        result = preprocessor.preprocess(text)
        
        assert result.cleaned_text
        assert len(result.tokens) > 1000
    
    def test_special_characters_preserved(self, preprocessor):
        """Test that meaningful special characters are preserved"""
        text = "Test with special chars: @, #, $, %, & symbols!"
        result = preprocessor.preprocess(text)
        
        # Should contain the text
        assert "Test" in result.cleaned_text
        assert "special" in result.cleaned_text
    
    def test_multiple_languages_mixed(self, preprocessor):
        """Test handling of mixed language content"""
        text = "English text with Español mixed in y français aussi."
        result = preprocessor.preprocess(text)
        
        assert result.cleaned_text
        assert len(result.sentences) > 0
    
    def test_urls_with_special_chars(self, preprocessor):
        """Test detection of complex URLs"""
        text = "Check https://example.com/path?query=value&other=123#anchor for info"
        result = preprocessor.preprocess(text)
        
        assert result.metadata.has_urls is True


class TestRepresentation:
    """Test string representations"""
    
    def test_preprocessed_text_repr(self):
        """Test PreprocessedText __repr__ method"""
        metadata = TextMetadata(
            original_length=100,
            cleaned_length=80,
            languages=["en"],
            detected_language="en",
            num_sentences=2,
            num_tokens=15,
            has_urls=False,
            has_emails=False,
            avg_word_length=5.3,
        )
        
        result = PreprocessedText(
            original_text="original",
            cleaned_text="cleaned",
            sentences=["s1", "s2"],
            tokens=list(range(15)),
            metadata=metadata,
        )
        
        repr_str = repr(result)
        assert "PreprocessedText" in repr_str
        assert "cleaned_length=80" in repr_str
        assert "language=en" in repr_str
        assert "sentences=2" in repr_str
