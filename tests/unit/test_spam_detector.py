"""Unit tests for spam detection module (T-602)."""

import pytest

from src.workers.pipelines.spam.spam_detector import (
    SpamClassification,
    SpamIndicator,
    SpamDetectionResult,
    PatternDetector,
    SpamDetector,
    get_spam_detector,
    spam_detection_task,
)


class TestSpamIndicator:
    """Tests for SpamIndicator dataclass."""

    def test_spam_indicator_creation(self):
        """Test creating spam indicator."""
        indicator = SpamIndicator(
            indicator_type="phishing",
            name="Account verification",
            matched_text="verify account",
            confidence=70,
            severity="high",
            explanation="Phishing attempt"
        )
        assert indicator.indicator_type == "phishing"
        assert indicator.confidence == 70

    def test_spam_indicator_to_dict(self):
        """Test converting indicator to dict."""
        indicator = SpamIndicator(
            indicator_type="spam_word",
            name="Free money",
            matched_text="free money",
            confidence=60,
            severity="high",
            explanation="Common spam phrase"
        )
        d = indicator.to_dict()
        assert d["indicator_type"] == "spam_word"
        assert d["confidence"] == 60


class TestSpamDetectionResult:
    """Tests for SpamDetectionResult dataclass."""

    def test_result_creation(self):
        """Test creating spam detection result."""
        result = SpamDetectionResult(
            text="Click here now!",
            is_spam=True,
            spam_classification=SpamClassification.LIKELY_SPAM,
            spam_score=65,
            indicators=[],
            risk_level="high",
            recommended_action="Quarantine for review",
            summary="Content classified as likely spam"
        )
        assert result.is_spam is True
        assert result.spam_score == 65

    def test_result_to_dict(self):
        """Test converting result to dict."""
        result = SpamDetectionResult(
            text="Test",
            is_spam=False,
            spam_classification=SpamClassification.NOT_SPAM,
            spam_score=10,
            indicators=[],
            risk_level="low",
            recommended_action="Allow",
            summary="Not spam"
        )
        d = result.to_dict()
        assert d["is_spam"] is False
        assert d["spam_classification"] == "not_spam"


class TestPatternDetector:
    """Tests for PatternDetector class."""

    def test_find_phishing_patterns_verify(self):
        """Test finding phishing patterns - verify."""
        patterns = PatternDetector.find_phishing_patterns("Please verify your account security now")
        assert len(patterns) > 0
        # Should detect either the verify pattern or confirmation pattern
        assert any("verify" in p.name.lower() or "verification" in p.name.lower() for p in patterns)

    def test_find_phishing_patterns_confirm(self):
        """Test finding phishing patterns - confirm."""
        patterns = PatternDetector.find_phishing_patterns("Confirm password immediately")
        assert len(patterns) > 0

    def test_find_phishing_patterns_update(self):
        """Test finding phishing patterns - update."""
        patterns = PatternDetector.find_phishing_patterns("Update payment information")
        assert len(patterns) > 0

    def test_find_phishing_patterns_none(self):
        """Test finding no phishing patterns."""
        patterns = PatternDetector.find_phishing_patterns("This is a normal message")
        assert len(patterns) == 0

    def test_find_keyword_spam_free_money(self):
        """Test finding keyword spam - free money."""
        indicators = PatternDetector.find_keyword_spam("Get free money now!")
        assert len(indicators) > 0

    def test_find_keyword_spam_work_from_home(self):
        """Test finding keyword spam - work from home."""
        indicators = PatternDetector.find_keyword_spam("Work from home and earn")
        assert len(indicators) > 0

    def test_find_keyword_spam_none(self):
        """Test finding no keyword spam."""
        indicators = PatternDetector.find_keyword_spam("Hello world")
        assert len(indicators) == 0

    def test_find_spam_words_viagra(self):
        """Test finding spam words - viagra."""
        indicators = PatternDetector.find_spam_words("Buy viagra online")
        assert len(indicators) > 0
        assert any("viagra" in i.matched_text.lower() for i in indicators)

    def test_find_spam_words_cialis(self):
        """Test finding spam words - cialis."""
        indicators = PatternDetector.find_spam_words("Cialis for sale")
        assert len(indicators) > 0

    def test_find_spam_words_casino(self):
        """Test finding spam words - casino."""
        indicators = PatternDetector.find_spam_words("Join our online casino")
        assert len(indicators) > 0

    def test_find_spam_words_none(self):
        """Test finding no spam words."""
        indicators = PatternDetector.find_spam_words("Normal news article")
        assert len(indicators) == 0

    def test_find_url_spam_patterns_shortener(self):
        """Test finding URL spam patterns - shortener."""
        patterns = PatternDetector.find_url_spam_patterns("Visit bit.ly/abc123")
        assert len(patterns) > 0

    def test_find_url_spam_patterns_ip_address(self):
        """Test finding URL spam patterns - IP address."""
        patterns = PatternDetector.find_url_spam_patterns("Go to 192.168.1.1")
        assert len(patterns) > 0

    def test_find_url_spam_patterns_none(self):
        """Test finding no URL spam patterns."""
        patterns = PatternDetector.find_url_spam_patterns("Visit google.com")
        assert len(patterns) == 0

    def test_find_excessive_punctuation_exclamation(self):
        """Test finding excessive exclamation marks."""
        indicators = PatternDetector.find_excessive_punctuation("Amazing!!!!! Great!!!!")
        assert any(i.indicator_type == "excessive_punctuation" for i in indicators)

    def test_find_excessive_punctuation_caps(self):
        """Test finding excessive capitalization."""
        indicators = PatternDetector.find_excessive_punctuation(
            "THIS IS VERY IMPORTANT MESSAGE"
        )
        assert any(i.indicator_type == "excessive_caps" for i in indicators)

    def test_find_excessive_punctuation_none(self):
        """Test finding no excessive punctuation."""
        indicators = PatternDetector.find_excessive_punctuation("This is normal text")
        assert len(indicators) == 0


class TestSpamDetector:
    """Tests for SpamDetector class."""

    @pytest.mark.asyncio
    async def test_detect_spam_empty_text_raises_error(self):
        """Test that empty text raises ValueError."""
        detector = SpamDetector()
        with pytest.raises(ValueError, match="Invalid text"):
            await detector.detect_spam("")

    @pytest.mark.asyncio
    async def test_detect_spam_none_text_raises_error(self):
        """Test that None text raises ValueError."""
        detector = SpamDetector()
        with pytest.raises(ValueError, match="Invalid text"):
            await detector.detect_spam(None)

    @pytest.mark.asyncio
    async def test_detect_spam_whitespace_only_raises_error(self):
        """Test that whitespace-only text raises ValueError."""
        detector = SpamDetector()
        with pytest.raises(ValueError, match="Invalid text"):
            await detector.detect_spam("   ")

    @pytest.mark.asyncio
    async def test_detect_spam_legitimate_text(self):
        """Test detecting legitimate text."""
        detector = SpamDetector()
        result = await detector.detect_spam("This is a normal message")
        assert result.is_spam is False
        assert result.spam_classification == SpamClassification.NOT_SPAM

    @pytest.mark.asyncio
    async def test_detect_spam_phishing_email(self):
        """Test detecting phishing email."""
        detector = SpamDetector()
        result = await detector.detect_spam(
            "Please verify your password account now or it will be disabled"
        )
        assert result.is_spam is True
        assert result.spam_score >= 40

    @pytest.mark.asyncio
    async def test_detect_spam_keyword_spam(self):
        """Test detecting keyword spam."""
        detector = SpamDetector()
        result = await detector.detect_spam("Get free money work from home!")
        assert result.is_spam is True
        assert result.spam_score >= 40

    @pytest.mark.asyncio
    async def test_detect_spam_spam_words(self):
        """Test detecting spam words."""
        detector = SpamDetector()
        result = await detector.detect_spam("Buy viagra and cialis online")
        assert result.is_spam is True
        assert len(result.indicators) > 0

    @pytest.mark.asyncio
    async def test_detect_spam_url_spam(self):
        """Test detecting URL spam patterns."""
        detector = SpamDetector()
        result = await detector.detect_spam("Visit bit.ly/malicious for free stuff")
        assert result.is_spam is True

    @pytest.mark.asyncio
    async def test_detect_spam_excessive_punctuation(self):
        """Test detecting excessive punctuation."""
        detector = SpamDetector()
        result = await detector.detect_spam("Buy NOW!!! LIMITED TIME!!! AMAZING DEAL!!!")
        # Should detect as suspicious or likely spam with sufficient indicators
        assert result.spam_score >= 30

    @pytest.mark.asyncio
    async def test_detect_spam_mixed_indicators(self):
        """Test detecting multiple spam indicators."""
        detector = SpamDetector()
        result = await detector.detect_spam(
            "CLICK HERE NOW!!! Get free money work from home! verify account"
        )
        assert result.is_spam is True
        assert len(result.indicators) > 2

    @pytest.mark.asyncio
    async def test_spam_score_in_range(self):
        """Test that spam score is 0-100."""
        detector = SpamDetector()
        texts = [
            "Normal message",
            "Buy viagra now",
            "Click here for free money!!!",
        ]
        for text in texts:
            result = await detector.detect_spam(text)
            assert 0 <= result.spam_score <= 100

    @pytest.mark.asyncio
    async def test_result_structure(self):
        """Test that result has valid structure."""
        detector = SpamDetector()
        result = await detector.detect_spam("Test message")
        assert hasattr(result, "text")
        assert hasattr(result, "is_spam")
        assert hasattr(result, "spam_classification")
        assert hasattr(result, "spam_score")
        assert hasattr(result, "indicators")
        assert hasattr(result, "risk_level")
        assert hasattr(result, "recommended_action")
        assert hasattr(result, "summary")

    def test_determine_classification_definite_spam(self):
        """Test classification - definite spam."""
        classification = SpamDetector._determine_classification(80)
        assert classification == SpamClassification.DEFINITE_SPAM

    def test_determine_classification_likely_spam(self):
        """Test classification - likely spam."""
        classification = SpamDetector._determine_classification(65)
        assert classification == SpamClassification.LIKELY_SPAM

    def test_determine_classification_suspicious(self):
        """Test classification - suspicious."""
        classification = SpamDetector._determine_classification(50)
        assert classification == SpamClassification.SUSPICIOUS

    def test_determine_classification_not_spam(self):
        """Test classification - not spam."""
        classification = SpamDetector._determine_classification(20)
        assert classification == SpamClassification.NOT_SPAM

    def test_determine_risk_level_high(self):
        """Test risk level - high."""
        risk = SpamDetector._determine_risk_level(75)
        assert risk == "high"

    def test_determine_risk_level_medium(self):
        """Test risk level - medium."""
        risk = SpamDetector._determine_risk_level(50)
        assert risk == "medium"

    def test_determine_risk_level_low(self):
        """Test risk level - low."""
        risk = SpamDetector._determine_risk_level(25)
        assert risk == "low"


class TestGlobalInstances:
    """Tests for global singleton instances."""

    @pytest.mark.asyncio
    async def test_get_spam_detector_singleton(self):
        """Test that get_spam_detector returns same instance."""
        detector1 = get_spam_detector()
        detector2 = get_spam_detector()
        assert detector1 is detector2

    @pytest.mark.asyncio
    async def test_spam_detection_task(self):
        """Test async task wrapper."""
        result = await spam_detection_task("Click here now for free money!")
        assert isinstance(result, dict)
        assert "is_spam" in result
        assert "spam_score" in result
        assert "spam_classification" in result


class TestRealWorldScenarios:
    """Tests for real-world spam detection scenarios."""

    @pytest.mark.asyncio
    async def test_nigerian_prince_scam(self):
        """Test detecting Nigerian prince scam."""
        detector = SpamDetector()
        text = "I am a Nigerian prince with access to millions. Click here to claim your share now!"
        result = await detector.detect_spam(text)
        assert result.is_spam is True
        assert result.spam_score >= 50

    @pytest.mark.asyncio
    async def test_phishing_email(self):
        """Test detecting phishing email."""
        detector = SpamDetector()
        text = "ACTION REQUIRED: Verify your password account or it will be suspended!"
        result = await detector.detect_spam(text)
        assert result.is_spam is True

    @pytest.mark.asyncio
    async def test_lottery_scam(self):
        """Test detecting lottery scam."""
        detector = SpamDetector()
        text = "Congratulations! You have won a free prize! Click here to claim now!!!"
        result = await detector.detect_spam(text)
        assert result.is_spam is True

    @pytest.mark.asyncio
    async def test_weight_loss_spam(self):
        """Test detecting weight loss spam."""
        detector = SpamDetector()
        text = "Lose weight fast with our miraculous weight loss pill! Limited time offer now!!!"
        result = await detector.detect_spam(text)
        assert result.is_spam is True
        assert result.spam_score >= 40

    @pytest.mark.asyncio
    async def test_legitimate_marketing_email(self):
        """Test not flagging legitimate marketing."""
        detector = SpamDetector()
        text = "New products available at our store. Visit us online for details."
        result = await detector.detect_spam(text)
        assert result.spam_score < 40

    @pytest.mark.asyncio
    async def test_news_article(self):
        """Test not flagging news article."""
        detector = SpamDetector()
        text = "Breaking news: Scientists discover new treatment for disease. Read the full article on our website."
        result = await detector.detect_spam(text)
        assert result.spam_score < 40
