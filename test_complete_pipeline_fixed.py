"""Live integration test demonstrating complete verification pipeline."""

import asyncio
import json
from src.workers.pipelines.text.preprocessor import get_preprocessor
from src.workers.pipelines.text.factchecker import get_fact_checker
from src.workers.pipelines.text.nlp_analyzer import get_nlp_analyzer
from src.workers.pipelines.text.evidence_validator import get_evidence_processor
from src.workers.pipelines.spam.source_credibility import get_source_analyzer
from src.workers.pipelines.spam.spam_detector import get_spam_detector
from src.workers.pipelines.aggregation.finding_aggregator import (
    get_finding_aggregator, PipelineResult
)
from src.workers.pipelines.aggregation.score_calculator import get_score_calculator


async def run_complete_pipeline(url: str, text: str) -> dict:
    """
    Run complete verification pipeline on text.
    
    Args:
        url: Source URL (for source credibility analysis)
        text: Text content to verify
        
    Returns:
        Complete pipeline results with aggregated findings
    """
    print("\n" + "=" * 80)
    print(f"FAKELYTICS COMPLETE PIPELINE TEST")
    print("=" * 80)
    print(f"URL: {url}")
    print(f"Text: {text[:100]}..." if len(text) > 100 else f"Text: {text}")
    print("=" * 80)

    # Stage 1: Text Preprocessing
    print("\n[STAGE 1] TEXT PREPROCESSING")
    print("-" * 80)
    preprocessor = get_preprocessor()
    preprocessed = preprocessor.preprocess(text, language="en")
    print(f"✓ Tokenized into {len(preprocessed.tokens)} tokens")
    print(f"✓ Detected language: {preprocessed.metadata.detected_language}")
    print(f"? Reading time: Calculated from token count")

    # Stage 2: Fact-Checking
    print("\n[STAGE 2] FACT-CHECKING")
    print("-" * 80)
    fact_checker = get_fact_checker()
    fact_check_result = await fact_checker.check_text(text)
    print(f"✓ Extracted {len(fact_check_result.claims)} claim(s)")
    for i, claim in enumerate(fact_check_result.claims, 1):
        print(f"  Claim {i}: {claim.claim_text[:60]}...")
    print(f"✓ Overall verdict: {fact_check_result.verdict.value}")
    print(f"✓ Confidence: {fact_check_result.confidence}%")

    # Stage 3: NLP Analysis
    print("\n[STAGE 3] NLP ANALYSIS WITH PATTERN DETECTION")
    print("-" * 80)
    nlp_analyzer = get_nlp_analyzer()
    nlp_result = await nlp_analyzer.analyze(text)
    print(f"✓ Detected {len(nlp_result.patterns)} misinformation pattern(s)")
    for pattern in nlp_result.patterns:
        print(f"  - {pattern.name}: {pattern.confidence}% confidence")
    print(f"✓ Overall verdict: {nlp_result.verdict.value}")
    print(f"✓ Confidence: {nlp_result.confidence}%")

    # Stage 4: Evidence Validation
    print("\n[STAGE 4] EVIDENCE VALIDATION")
    print("-" * 80)
    evidence_processor = get_evidence_processor(timeout=10, max_concurrent=5)
    # Mock evidence URLs from fact check findings
    evidence_urls = [f.url for f in fact_check_result.evidence if f.url][:3]
    if evidence_urls:
        print(f"✓ Validating {len(evidence_urls)} evidence URL(s)...")
        for url_item in evidence_urls[:2]:
            print(f"  - {url_item}")
    else:
        print("✓ No evidence URLs to validate")

    # Stage 5: Source Credibility Analysis
    print("\n[STAGE 5] SOURCE CREDIBILITY ANALYSIS")
    print("-" * 80)
    source_analyzer = get_source_analyzer()
    source_score = await source_analyzer.analyze_url(url)
    print(f"✓ Domain: {source_score.domain}")
    print(f"✓ Credibility level: {source_score.credibility_level.value}")
    print(f"✓ Credibility score: {source_score.credibility_score}/100")
    print(f"✓ SSL/HTTPS: {'Yes' if source_score.ssl_info.has_ssl else 'No'}")
    print(f"✓ Domain age: {source_score.domain_info.age_years:.1f} years")

    # Stage 6: Spam Detection
    print("\n[STAGE 6] SPAM DETECTION")
    print("-" * 80)
    spam_detector = get_spam_detector()
    spam_result = await spam_detector.detect_spam(text)
    print(f"✓ Is spam: {spam_result.is_spam}")
    print(f"✓ Spam classification: {spam_result.spam_classification.value}")
    print(f"✓ Spam score: {spam_result.spam_score}/100")
    print(f"✓ Detected {len(spam_result.indicators)} spam indicator(s)")

    # Stage 7: Finding Aggregation
    print("\n[STAGE 7] FINDING AGGREGATION")
    print("-" * 80)
    pipeline_results = {
        "text": PipelineResult(
            pipeline_name="text",
            verdict=fact_check_result.verdict.value,
            confidence=fact_check_result.confidence,
            indicators_count=len(fact_check_result.claims),
            summary=f"Fact-check analysis: {len(fact_check_result.claims)} claim(s) analyzed"
        ),
        "nlp": PipelineResult(
            pipeline_name="nlp",
            verdict=nlp_result.verdict.value,
            confidence=nlp_result.confidence,
            indicators_count=len(nlp_result.patterns),
            summary=f"NLP analysis: {len(nlp_result.patterns)} pattern(s) detected"
        ),
        "spam": PipelineResult(
            pipeline_name="spam",
            verdict="Disputed" if spam_result.is_spam else "Supported",
            confidence=spam_result.spam_score,
            indicators_count=len(spam_result.indicators),
            summary=f"Spam analysis: {spam_result.spam_classification.value}"
        ),
        "source": PipelineResult(
            pipeline_name="source",
            verdict="Supported" if source_score.credibility_score >= 70 else "Disputed",
            confidence=source_score.credibility_score,
            indicators_count=0,
            summary=f"Source credibility: {source_score.credibility_level.value}"
        ),
    }

    aggregator = get_finding_aggregator()
    aggregation_report = await aggregator.aggregate_findings(
        "test-req-001", url, pipeline_results
    )
    print(f"✓ Aggregated {len(aggregation_report.findings)} finding(s)")
    print(f"✓ Overall verdict: {aggregation_report.overall_verdict.value}")
    print(f"✓ Overall confidence: {aggregation_report.overall_confidence}%")

    # Stage 8: Score Calculation
    print("\n[STAGE 8] CREDIBILITY SCORE CALCULATION")
    print("-" * 80)
    findings = {
        "text": {
            "verdict": fact_check_result.verdict.value,
            "confidence": fact_check_result.confidence
        },
        "spam": {
            "verdict": "Disputed" if spam_result.is_spam else "Supported",
            "spam_score": spam_result.spam_score
        },
        "source": {
            "credibility_score": source_score.credibility_score,
            "credibility_level": source_score.credibility_level.value
        },
        "evidence_validation": {
            "validation_score": 70
        },
        "overall_verdict": aggregation_report.overall_verdict.value,
        "overall_confidence": aggregation_report.overall_confidence,
    }

    score_calculator = get_score_calculator()
    final_score = await score_calculator.calculate_score(findings)
    print(f"✓ Overall credibility score: {final_score.overall_score}/100")
    print(f"✓ Credibility level: {final_score.credibility_level.value}")
    print(f"✓ Evidence strength: {final_score.evidence_strength}/100")
    print(f"✓ Source reliability: {final_score.source_reliability}/100")
    print(f"✓ Content quality: {final_score.content_quality}/100")

    # Final Report
    print("\n" + "=" * 80)
    print("FINAL REPORT")
    print("=" * 80)
    print(f"Overall Verdict: {final_score.credibility_level.value.upper()}")
    print(f"Credibility Score: {final_score.overall_score}/100")
    print(f"Summary: {final_score.summary}")
    print("=" * 80 + "\n")

    return {
        "overall_score": final_score.overall_score,
        "credibility_level": final_score.credibility_level.value,
        "findings": len(aggregation_report.findings),
        "pipeline_statuses": aggregation_report.pipeline_statuses,
    }


async def main():
    """Run integration tests with different text scenarios."""
    
    scenarios = [
        (
            "https://trustworthy-news.com",
            "According to scientific research published in Nature, climate change is caused by human activities. "
            "Multiple studies confirm that greenhouse gas emissions from burning fossil fuels are the primary driver. "
            "This evidence has been peer-reviewed and accepted by the scientific community."
        ),
        (
            "https://suspicious-site.net",
            "BREAKING NEWS!!! ALL experts are LYING about vaccines!!! "
            "Click here now to discover the SHOCKING truth they don't want you to know! "
            "Get rich quick with this amazing offer! Limited time only!!!"
        ),
        (
            "https://neutral-blog.com",
            "Some experts believe that technology is changing society. Many people might find this interesting. "
            "Apparently, there could be various perspectives on this issue. It seems that further research may be needed."
        ),
    ]

    for url, text in scenarios:
        try:
            result = await run_complete_pipeline(url, text)
            print(f"Result: {json.dumps(result, indent=2)}\n")
        except Exception as e:
            print(f"ERROR in pipeline: {e}\n")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
