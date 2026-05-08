"""Live test of Fakelytics text verification pipeline."""

import asyncio
import json
import pytest
from src.workers.pipelines.text.preprocessor import get_preprocessor
from src.workers.pipelines.text.factchecker import get_fact_checker
from src.workers.pipelines.text.nlp_analyzer import get_nlp_analyzer
from src.workers.pipelines.text.evidence_validator import get_evidence_processor


@pytest.mark.asyncio
async def test_live_verification():
    """Test live verification pipeline with sample text claims."""
    
    print("\n" + "="*80)
    print("FAKELYTICS LIVE TEXT VERIFICATION PIPELINE TEST")
    print("="*80 + "\n")
    
    # Test Case 1: Suspicious Misinformation Claim
    claim_1 = (
        "BREAKING NEWS!!! Shocking evidence shows that ALL experts are lying "
        "because obviously they don't want you to know the truth! "
        "Some sources might prove that water is not wet. Everyone should read this EXCLUSIVE report!"
    )
    
    # Test Case 2: Balanced Factual Text
    claim_2 = (
        "Water is a chemical compound that consists of hydrogen and oxygen. "
        "According to scientific research, water boils at 100 degrees Celsius at sea level. "
        "Some studies suggest that water may play an important role in various biological processes."
    )
    
    # Test Case 3: Mixed Quality Text
    claim_3 = (
        "Allegedly, the company improved performance. Some analysts suggest it might be "
        "due to new strategy. The data clearly shows growth in several areas."
    )
    
    test_cases = [
        ("Misinformation with Emotional Language", claim_1),
        ("Factual Scientific Text", claim_2),
        ("Mixed Quality Text", claim_3),
    ]
    
    for test_name, text in test_cases:
        print(f"\n{'─'*80}")
        print(f"TEST: {test_name}")
        print(f"{'─'*80}")
        print(f"\nInput Text:\n{text}\n")
        
        # Step 1: Text Preprocessing
        print("📋 STEP 1: TEXT PREPROCESSING")
        print("─" * 40)
        try:
            preprocessor = get_preprocessor()
            preprocessed = preprocessor.preprocess(text)  # Not async
            print(f"✓ Language: {preprocessed.metadata.detected_language}")
            print(f"✓ Sentences: {preprocessed.metadata.num_sentences}")
            print(f"✓ Tokens: {preprocessed.metadata.num_tokens}")
            print(f"✓ Cleaned Text (first 100 chars): {preprocessed.cleaned_text[:100]}...")
        except Exception as e:
            print(f"✗ Error: {e}")
            continue
        
        # Step 2: Fact-Checking
        print("\n🔍 STEP 2: FACT-CHECKING")
        print("─" * 40)
        try:
            fact_checker = get_fact_checker()
            fact_check_result = await fact_checker.check_text(text, timeout=5)
            print(f"✓ Verdict: {fact_check_result.verdict.value}")
            print(f"✓ Confidence: {fact_check_result.confidence}%")
            print(f"✓ Summary: {fact_check_result.summary}")
            print(f"✓ Findings: {len(fact_check_result.findings)} claims checked")
            for i, finding in enumerate(fact_check_result.findings[:2], 1):
                print(f"  - Claim {i}: {finding.claim}")
                print(f"    Verdict: {finding.verdict.value} (Confidence: {finding.confidence}%)")
        except Exception as e:
            print(f"✗ Error: {e}")
        
        # Step 3: NLP Analysis
        print("\n🧠 STEP 3: NLP MISINFORMATION PATTERN DETECTION")
        print("─" * 40)
        try:
            nlp_analyzer = get_nlp_analyzer()
            nlp_result = await nlp_analyzer.analyze(text, timeout=5)
            print(f"✓ Verdict: {nlp_result.verdict.value}")
            print(f"✓ Confidence: {nlp_result.confidence}%")
            print(f"✓ Summary: {nlp_result.summary}")
            print(f"✓ Patterns Detected: {len(nlp_result.patterns)}")
            for i, pattern in enumerate(nlp_result.patterns[:3], 1):
                print(f"  - Pattern {i}: {pattern.pattern.value}")
                print(f"    Text: '{pattern.text_span}'")
                print(f"    Explanation: {pattern.explanation}")
                print(f"    Confidence: {pattern.confidence}%")
            if nlp_result.language_indicators:
                print(f"✓ Language Indicators: {nlp_result.language_indicators}")
            print(f"✓ Recommendation: {nlp_result.recommendation}")
        except Exception as e:
            print(f"✗ Error: {e}")
        
        # Step 4: Evidence Validation (simulated)
        print("\n🔗 STEP 4: EVIDENCE VALIDATION")
        print("─" * 40)
        try:
            processor = get_evidence_processor()
            # Simulate evidence URLs from fact checking
            sample_evidence = {
                "evidence": [
                    {"url": "http://192.168.1.1", "snippet": "Sample evidence"},
                    {"url": "http://127.0.0.1/test", "snippet": "Local test"},
                ]
            }
            enriched = await processor.validate_and_enrich(sample_evidence)
            print(f"✓ Evidence URLs Validated: {len(enriched.get('evidence', []))}")
            for i, ev in enumerate(enriched.get('evidence', [])[:2], 1):
                validation = ev.get('validation', {})
                if validation:
                    print(f"  - URL {i}: {ev.get('url')}")
                    print(f"    Accessible: {validation.get('is_accessible')}")
                    if validation.get('validation_error'):
                        print(f"    Error: {validation.get('validation_error')}")
        except Exception as e:
            print(f"✗ Error: {e}")
        
        # Final Summary
        print("\n" + "="*40)
        print("VERIFICATION COMPLETE")
        print("="*40)


if __name__ == "__main__":
    asyncio.run(test_live_verification())
