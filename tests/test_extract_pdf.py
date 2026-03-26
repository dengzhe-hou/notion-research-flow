#!/usr/bin/env python3
"""Unit tests for the PDF extraction module (section detection only — no actual PDF needed)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "paper-analyze" / "scripts"))

from extract_pdf import _detect_sections

SAMPLE_PAPER_TEXT = """
Some preamble and title content here.

Abstract
We present a novel method for large language model alignment.
Our approach achieves state-of-the-art results on multiple benchmarks.

1. Introduction
Language models have become increasingly powerful.
However, aligning them with human preferences remains a challenge.

2. Related Work
RLHF was first proposed by Christiano et al.
InstructGPT applied RLHF to large language models.

3. Method
We propose a new alignment technique called DPO.
It directly optimizes the policy without training a reward model.

3.1 Problem Formulation
Given a dataset of preference pairs, we optimize...

4. Experiments
We evaluate our method on three benchmarks.

4.1 Results
Our method achieves 92.3% accuracy on SuperGLUE.
It outperforms the baseline by 5.2 percentage points.

5. Conclusion
We have presented a simple yet effective alignment method.
Future work includes scaling to larger models.

References
[1] Christiano et al. Deep reinforcement learning from human preferences.
[2] Ouyang et al. Training language models to follow instructions.
"""


def test_detect_standard_sections():
    """Should detect standard paper sections."""
    sections = _detect_sections(SAMPLE_PAPER_TEXT)
    section_titles = [s["title"] for s in sections]

    assert "Abstract" in section_titles
    assert "Introduction" in section_titles
    assert "Related Work" in section_titles
    assert "Conclusion" in section_titles or "Conclusions" in section_titles


def test_method_section_detected():
    """Method/Methodology section should be detected."""
    sections = _detect_sections(SAMPLE_PAPER_TEXT)
    section_titles = [s["title"].lower() for s in sections]
    assert any("method" in t for t in section_titles)


def test_experiments_section_detected():
    """Experiments section should be detected."""
    sections = _detect_sections(SAMPLE_PAPER_TEXT)
    section_titles = [s["title"].lower() for s in sections]
    assert any("experiment" in t for t in section_titles)


def test_references_detected():
    """References section should be detected."""
    sections = _detect_sections(SAMPLE_PAPER_TEXT)
    section_titles = [s["title"] for s in sections]
    assert "References" in section_titles


def test_section_content_not_empty():
    """Detected sections should have non-empty content."""
    sections = _detect_sections(SAMPLE_PAPER_TEXT)
    for s in sections:
        if s["title"] != "Preamble":
            assert len(s["content"]) > 0, f"Section '{s['title']}' has empty content"


def test_preamble_captured():
    """Text before the first section heading should be captured as 'Preamble'."""
    sections = _detect_sections(SAMPLE_PAPER_TEXT)
    assert sections[0]["title"] == "Preamble"


def test_empty_text():
    """Empty text should return empty or minimal sections."""
    sections = _detect_sections("")
    # Should have at most a Preamble
    assert len(sections) <= 1


def test_numbered_sections():
    """Section headings with numbers (e.g., '1. Introduction') should be detected."""
    text = "1. Introduction\nSome intro text.\n2. Related Work\nSome related work."
    sections = _detect_sections(text)
    titles = [s["title"] for s in sections]
    assert "Introduction" in titles
    assert "Related Work" in titles


if __name__ == "__main__":
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    passed = failed = 0
    for t in tests:
        try:
            t()
            passed += 1
            print(f"  PASS  {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"  FAIL  {t.__name__}: {e}")
        except Exception as e:
            failed += 1
            print(f"  ERROR {t.__name__}: {e}")
    print(f"\n{passed} passed, {failed} failed out of {passed + failed}")
    sys.exit(1 if failed else 0)
