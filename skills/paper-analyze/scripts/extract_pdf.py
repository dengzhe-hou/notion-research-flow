#!/usr/bin/env python3
"""Download and extract text from an arXiv PDF.

Usage:
    python3 extract_pdf.py --arxiv-id 2301.07041
    python3 extract_pdf.py --url https://arxiv.org/pdf/2301.07041.pdf

Output:
    JSON dict to stdout with keys: arxiv_id, full_text, page_count, sections.
"""

import argparse
import json
import os
import re
import sys
import tempfile
import urllib.request


def download_pdf(arxiv_id: str = "", url: str = "") -> str:
    """Download a PDF and return the local file path.

    Args:
        arxiv_id: arXiv paper ID (e.g., "2301.07041").
        url: Direct PDF URL.

    Returns:
        Path to the downloaded PDF file.
    """
    if not url and arxiv_id:
        url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"

    if not url:
        raise ValueError("Either arxiv_id or url must be provided")

    print(f"Downloading PDF from {url}...", file=sys.stderr)

    tmp_dir = tempfile.mkdtemp(prefix="nrf_pdf_")
    filename = arxiv_id.replace("/", "_") if arxiv_id else "paper"
    pdf_path = os.path.join(tmp_dir, f"{filename}.pdf")

    req = urllib.request.Request(url, headers={"User-Agent": "notion-research-flow/1.0"})
    with urllib.request.urlopen(req, timeout=60) as response:
        with open(pdf_path, "wb") as f:
            f.write(response.read())

    print(f"Downloaded to {pdf_path} ({os.path.getsize(pdf_path)} bytes)", file=sys.stderr)
    return pdf_path


def extract_text(pdf_path: str) -> dict:
    """Extract text from a PDF using PyMuPDF.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        Dict with full_text, page_count, and sections.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        print("Error: PyMuPDF not installed. Run: pip install PyMuPDF", file=sys.stderr)
        sys.exit(1)

    doc = fitz.open(pdf_path)
    page_count = len(doc)
    full_text = ""

    for page in doc:
        full_text += page.get_text() + "\n"

    doc.close()

    # Detect sections
    sections = _detect_sections(full_text)

    return {
        "full_text": full_text,
        "page_count": page_count,
        "sections": sections,
    }


def _detect_sections(text: str) -> list[dict]:
    """Detect paper sections from extracted text.

    Returns:
        List of dicts with 'title' and 'content' for each section.
    """
    # Common section headings in academic papers
    section_patterns = [
        r"^(?:\d+\.?\s+)?(Abstract)\s*$",
        r"^(?:\d+\.?\s+)?(Introduction)\s*$",
        r"^(?:\d+\.?\s+)?(Related\s+Work)\s*$",
        r"^(?:\d+\.?\s+)?(Background)\s*$",
        r"^(?:\d+\.?\s+)?(Preliminaries)\s*$",
        r"^(?:\d+\.?\s+)?(Method(?:ology)?|(?:Proposed\s+)?Approach|(?:Our\s+)?Framework)\s*$",
        r"^(?:\d+\.?\s+)?(Experiment(?:s|al\s+Results?)?)\s*$",
        r"^(?:\d+\.?\s+)?(Results?(?:\s+and\s+Discussion)?)\s*$",
        r"^(?:\d+\.?\s+)?(Discussion)\s*$",
        r"^(?:\d+\.?\s+)?(Analysis|Ablation\s+Stud(?:y|ies))\s*$",
        r"^(?:\d+\.?\s+)?(Conclusion(?:s)?)\s*$",
        r"^(?:\d+\.?\s+)?(Limitation(?:s)?)\s*$",
        r"^(?:\d+\.?\s+)?(Acknowledgement(?:s)?)\s*$",
        r"^(?:\d+\.?\s+)?(References|Bibliography)\s*$",
        r"^(?:\d+\.?\s+)?(Appendi(?:x|ces))\s*$",
    ]

    combined_pattern = "|".join(f"(?:{p})" for p in section_patterns)
    lines = text.split("\n")

    sections = []
    current_title = "Preamble"
    current_content = []

    for line in lines:
        stripped = line.strip()
        match = re.match(combined_pattern, stripped, re.IGNORECASE)
        if match:
            # Save previous section
            if current_content:
                sections.append({
                    "title": current_title,
                    "content": "\n".join(current_content).strip(),
                })
            # Start new section
            current_title = next(g for g in match.groups() if g is not None)
            current_content = []
        else:
            current_content.append(line)

    # Save last section
    if current_content:
        sections.append({
            "title": current_title,
            "content": "\n".join(current_content).strip(),
        })

    return sections


def main():
    parser = argparse.ArgumentParser(description="Download and extract text from arXiv PDFs")
    parser.add_argument("--arxiv-id", type=str, default="", help="arXiv paper ID (e.g., 2301.07041)")
    parser.add_argument("--url", type=str, default="", help="Direct PDF URL")
    parser.add_argument("--keep-pdf", action="store_true", help="Don't delete the downloaded PDF")
    args = parser.parse_args()

    if not args.arxiv_id and not args.url:
        print("Error: Either --arxiv-id or --url must be specified", file=sys.stderr)
        sys.exit(1)

    pdf_path = download_pdf(arxiv_id=args.arxiv_id, url=args.url)

    try:
        result = extract_text(pdf_path)
        result["arxiv_id"] = args.arxiv_id
        result["pdf_path"] = pdf_path if args.keep_pdf else ""

        print(json.dumps(result, ensure_ascii=False))
        print(f"\n# Extracted {result['page_count']} pages, "
              f"{len(result['sections'])} sections, "
              f"{len(result['full_text'])} chars", file=sys.stderr)
    finally:
        if not args.keep_pdf and os.path.exists(pdf_path):
            os.unlink(pdf_path)
            os.rmdir(os.path.dirname(pdf_path))


if __name__ == "__main__":
    main()
