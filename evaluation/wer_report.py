"""WER (Word Error Rate) measurement for dialect ASR accuracy."""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def compute_wer(reference: str, hypothesis: str) -> float:
    """Compute Word Error Rate between reference and hypothesis."""
    ref_words = reference.lower().split()
    hyp_words = hypothesis.lower().split()

    if not ref_words:
        return 0.0 if not hyp_words else 1.0

    # Dynamic programming for edit distance
    d = [[0] * (len(hyp_words) + 1) for _ in range(len(ref_words) + 1)]

    for i in range(len(ref_words) + 1):
        d[i][0] = i
    for j in range(len(hyp_words) + 1):
        d[0][j] = j

    for i in range(1, len(ref_words) + 1):
        for j in range(1, len(hyp_words) + 1):
            if ref_words[i - 1] == hyp_words[j - 1]:
                d[i][j] = d[i - 1][j - 1]
            else:
                d[i][j] = min(
                    d[i - 1][j] + 1,      # deletion
                    d[i][j - 1] + 1,      # insertion
                    d[i - 1][j - 1] + 1,  # substitution
                )

    return d[len(ref_words)][len(hyp_words)] / len(ref_words)


def run_wer_report():
    """Run WER measurement on sample transcriptions."""
    print("=" * 60)
    print("CHAKRAVYUHA — Dialect WER Report")
    print("=" * 60)

    # Sample test data (reference vs ASR output)
    test_samples = [
        {
            "language": "Hindi",
            "reference": "मुझे कानूनी मदद चाहिए",
            "hypothesis": "मुझे कानूनी मदद चाहिए",
        },
        {
            "language": "Hindi",
            "reference": "किसी ने मेरा फोन चुरा लिया",
            "hypothesis": "किसी ने मेरा फोन चुरा लिया",
        },
        {
            "language": "Hindi (Bhojpuri dialect)",
            "reference": "हमरा से पैसा लूट लिहलस",
            "hypothesis": "हमरा से पैसा लूट लिहलस",
        },
        {
            "language": "Tamil",
            "reference": "எனக்கு சட்ட உதவி தேவை",
            "hypothesis": "எனக்கு சட்ட உதவி தேவை",
        },
        {
            "language": "Bengali",
            "reference": "আমার আইনি সাহায্য দরকার",
            "hypothesis": "আমার আইনি সাহায্য দরকার",
        },
    ]

    print(f"\nSample Size: {len(test_samples)} utterances")
    print("-" * 60)

    total_wer = 0.0
    for sample in test_samples:
        wer = compute_wer(sample["reference"], sample["hypothesis"])
        total_wer += wer
        status = "✓" if wer < 0.2 else "✗"
        print(f"  [{status}] {sample['language']}: WER = {wer:.2%}")
        if wer > 0:
            print(f"      Ref: {sample['reference']}")
            print(f"      Hyp: {sample['hypothesis']}")

    avg_wer = total_wer / len(test_samples)
    print(f"\n  Average WER: {avg_wer:.2%}")
    print(f"  Target: < 20%")
    print(f"  Status: {'PASS ✓' if avg_wer < 0.20 else 'NEEDS IMPROVEMENT'}")
    print("\nNote: Real WER requires actual audio samples processed through Sarvam ASR.")
    print("These are placeholder reference/hypothesis pairs for the evaluation framework.")


if __name__ == "__main__":
    run_wer_report()
