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
    print("FAKELYTICS COMPLETE PIPELINE TEST")
    print("=" * 80)
    print(f"URL: {url}")
    print(f"Text: {text[:100]}..." if len(text) > 100 else f"Text: {text}")
    print("=" * 80)

    try:
        # Stage 1: Text Preprocessing
        print("\n[STAGE 1] TEXT PREPROCESSING")
        print("-" * 80)
        preprocessor = get_preprocessor()
        preprocessed = preprocessor.preprocess(text, language="en")
        print(f"? Tokenized into {len(preprocessed.tokens)} tokens")
        print(f"? Detected language: {preprocessed.metadata.detected_language}")
        print(f"? Total sentences: {preprocessed.metadata.num_sentences}")

        # Stage 2: Fact-Checking
        print("\n[STAGE 2] FACT-CHECKING")
        print("-" * 80)
        fact_checker = get_fact_checker()
        fact_check_results = await fact_checker.check_text(text)
        print(f"? Extracted {len(fact_check_results)} claim finding(s)")
        
        if fact_check_results:
            for i, finding in enumerate(fact_check_results, 1):
                print(f"  Finding {i}: {finding.claim[:60]}...")
                print(f"    Verdict: {finding.verdict.value}, Confidence: {finding.confidence}%")
        else:
            print("  No claims found to fact-check")

        # Stage 3: NLP Analysis
        print("\n[STAGE 3] NLP ANALYSIS WITH PATTERN DETECTION")
        print("-" * 80)
        nlp_analyzer = get_nlp_analyzer()
        nlp_result = await nlp_analyzer.analyze(text)
        print(f"? Detected {len(nlp_result.patterns)} misinformation pattern(s)")
        for pattern in nlp_result.patterns:
            print(f"  - {pattern.name}: {pattern.confidence}% confidence")
        print(f"? Overall verdict: {nlp_result.verdict.value}")
        print(f"? Confidence: {nlp_result.confidence}%")

        # Stage 4: Evidence Validation
        print("\n[STAGE 4] EVIDENCE VALIDATION")
        print("-" * 80)
        evidence_processor = get_evidence_processor(timeout=10, max_concurrent=5)
        # Collect evidence URLs from fact check findings
        evidence_urls = []
        if fact_check_results:
            for finding in fact_check_results:
                for evidence in finding.evidence:
                    if hasattr(evidence, 'url') and evidence.url:
                        evidence_urls.append(evidence.url)
        
        if evidence_urls:
            print(f"? Found {len(evidence_urls)} evidence URL(s)")
            print(f"  Sample URLs:")
            for url_item in evidence_urls[:2]:
                print(f"    - {url_item}")
        else:
            print("? No evidence URLs to validate")

        # Stage 5: Source Credibility Analysis
        print("\n[STAGE 5] SOURCE CREDIBILITY ANALYSIS")
        print("-" * 80)
        source_analyzer = get_source_analyzer()
        source_score = await source_analyzer.analyze_url(url)
        print(f"? Domain: {source_score.domain}")
        print(f"? Credibility level: {source_score.credibility_level.value}")
        print(f"? Credibility score: {source_score.credibility_score}/100")
        print(f"? SSL/HTTPS: {'Yes' if source_score.ssl_info.has_ssl else 'No'}")
        print(f"? Domain age: {source_score.domain_info.age_years:.1f} years")

        # Stage 6: Spam Detection
        print("\n[STAGE 6] SPAM DETECTION")
        print("-" * 80)
        spam_detector = get_spam_detector()
        spam_result = await spam_detector.detect_spam(text)
        print(f"? Is spam: {spam_result.is_spam}")
        print(f"? Spam classification: {spam_result.spam_classification.value}")
        print(f"? Spam score: {spam_result.spam_score}/100")
        print(f"? Detected {len(spam_result.indicators)} spam indicator(s)")

        # Stage 7: Finding Aggregation
        print("\n[STAGE 7] FINDING AGGREGATION")
        print("-" * 80)
        finding_aggregator = get_finding_aggregator()
        
        # Prepare findings from all stages
        all_findings = []
        if fact_check_results:
            all_findings.extend(fact_check_results)
        
        aggregated = finding_aggregator.aggregate_findings(all_findings)
        print(f"? Aggregated {len(aggregated.findings)} finding(s)")
        print(f"? Primary verdict: {aggregated.primary_verdict.value}")
        print(f"? Confidence: {aggregated.confidence}%")

        # Stage 8: Score Calculation
        print("\n[STAGE 8] SCORE CALCULATION & FINAL VERDICT")
        print("-" * 80)
        score_calculator = get_score_calculator()
        
        # Calculate final scores
        final_scores = score_calculator.calculate_scores(
            findings=aggregated.findings,
            source_score=source_score,
            spam_detection=spam_result,
            nlp_analysis=nlp_result
        )
        
        print(f"? Overall reliability score: {final_scores.reliability_score}/100")
        print(f"? Misinformation risk: {final_scores.misinformation_risk_level.value}")
        print(f"? Credibility assessment: {final_scores.credibility_level.value}")
        print(f"? Recommendation: {final_scores.recommendation}")

        print("\n" + "=" * 80)
        print("PIPELINE COMPLETED SUCCESSFULLY")
        print("=" * 80)
        
        return {
            "status": "success",
            "findings": len(aggregated.findings),
            "reliability_score": final_scores.reliability_score
        }
        
    except Exception as e:
        print(f"\nERROR in pipeline: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return {"status": "error", "error": str(e)}


# Test data for 3 scenarios
test_scenarios = [
    {
        "name": "Trustworthy News",
        "url": "https://trustworthy-news.com",
        "text": "According to scientific research published in Nature, climate change is caused by human activities. Multiple peer-reviewed studies confirm this finding."
    },
    {
        "name": "Suspicious Website",
        "url": "https://suspicious-site.net",
        "text": "BREAKING NEWS!!! ALL experts are LYING about vaccines!!! Click here now to discover the SHOCKING truth they don't want you to know!!!"
    },
    {
        "name": "Neutral Blog",
        "url": "https://neutral-blog.com",
        "text": "Some experts believe that technology is changing society. Many people might find this interesting. Another thought to consider."
    }
]


async def main():
    """Run complete pipeline test for all scenarios."""
    results = []
    
    for scenario in test_scenarios:
        result = await run_complete_pipeline(scenario["url"], scenario["text"])
        results.append(result)
    
    print("\n\n" + "=" * 80)
    print("SUMMARY OF ALL SCENARIOS")
    print("=" * 80)
    for scenario, result in zip(test_scenarios, results):
        print(f"\n{scenario['name']}:")
        print(f"  Status: {result['status']}")
        if result['status'] == 'success':
            print(f"  Findings: {result['findings']}")
            print(f"  Reliability Score: {result['reliability_score']}/100")


if __name__ == "__main__":
    asyncio.run(main())
