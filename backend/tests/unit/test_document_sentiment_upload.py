"""
AEQUITAS - Unit tests for the document-sentiment upload/paste endpoints.

extract_text_from_upload does its own file-type dispatch, size check,
and text extraction (pypdf for .pdf, decode for .txt/.md) with no
database or LLM involved, so it's tested for real through the FastAPI
TestClient rather than mocked. news_sentiment_from_text's validation
branch (text too short) is likewise reachable without an LLM call;
the actual sentiment-scoring path is out of scope here for the same
reason test_extended_agents.py gives for the Finnhub-backed agent -
that's integration-tested manually, not unit-tested against a real
Groq call.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

# A hand-written minimal single-page PDF with a real text-showing
# operator (BT/Tj/ET) - small enough to inline, but exercises pypdf's
# actual extraction path rather than a mocked one. pypdf tolerates the
# imprecise xref table below by falling back to a full-file scan,
# which is representative of how it behaves on real-world PDFs too.
_MINIMAL_PDF = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> /MediaBox [0 0 300 144] /Contents 5 0 R >>
endobj
4 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
5 0 obj
<< /Length 73 >>
stream
BT /F1 18 Tf 10 100 Td (Hello from a real PDF report.) Tj ET
endstream
endobj
xref
0 6
0000000000 65535 f
trailer
<< /Size 6 /Root 1 0 R >>
startxref
0
%%EOF"""

_BLANK_PDF_NO_TEXT = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /Resources << >> /MediaBox [0 0 200 200] >>
endobj
xref
0 4
0000000000 65535 f
trailer
<< /Size 4 /Root 1 0 R >>
startxref
0
%%EOF"""

EXTRACT_URL = "/api/v1/agents/news-sentiment/extract-text"
ANALYZE_URL = "/api/v1/agents/news-sentiment/analyze-text"


@pytest.mark.unit
def test_extract_text_from_txt_file(client: TestClient) -> None:
    content = b"Apple reported record iPhone sales this quarter."
    response = client.post(
        EXTRACT_URL,
        files={"file": ("report.txt", content, "text/plain")},
    )
    assert response.status_code == 200
    data = response.json()
    assert "record iPhone sales" in data["text"]
    assert data["truncated"] is False


@pytest.mark.unit
def test_extract_text_from_md_file(client: TestClient) -> None:
    content = b"# Analyst Note\n\nBullish on NVDA given AI demand."
    response = client.post(
        EXTRACT_URL,
        files={"file": ("note.md", content, "text/markdown")},
    )
    assert response.status_code == 200
    assert "Bullish on NVDA" in response.json()["text"]


@pytest.mark.unit
def test_extract_text_from_pdf_file(client: TestClient) -> None:
    response = client.post(
        EXTRACT_URL,
        files={"file": ("report.pdf", _MINIMAL_PDF, "application/pdf")},
    )
    assert response.status_code == 200
    assert "Hello from a real PDF report." in response.json()["text"]


@pytest.mark.unit
def test_extract_text_pdf_with_no_text_returns_422(client: TestClient) -> None:
    response = client.post(
        EXTRACT_URL,
        files={"file": ("blank.pdf", _BLANK_PDF_NO_TEXT, "application/pdf")},
    )
    assert response.status_code == 422
    assert "no extractable text" in response.json()["detail"].lower()


@pytest.mark.unit
def test_extract_text_rejects_unsupported_extension(client: TestClient) -> None:
    response = client.post(
        EXTRACT_URL,
        files={"file": ("report.docx", b"whatever", "application/octet-stream")},
    )
    assert response.status_code == 422
    assert "unsupported file type" in response.json()["detail"].lower()


@pytest.mark.unit
def test_extract_text_rejects_oversized_file(client: TestClient) -> None:
    oversized = b"a" * (10 * 1024 * 1024 + 1)  # 1 byte over the 10MB cap
    response = client.post(
        EXTRACT_URL,
        files={"file": ("huge.txt", oversized, "text/plain")},
    )
    assert response.status_code == 413


@pytest.mark.unit
def test_extract_text_decodes_non_utf8_gracefully(client: TestClient) -> None:
    # Latin-1 encoded bytes that aren't valid UTF-8 (e.g. a smart quote)
    content = "Café earnings beat expectations".encode("latin-1")
    response = client.post(
        EXTRACT_URL,
        files={"file": ("report.txt", content, "text/plain")},
    )
    assert response.status_code == 200
    assert "earnings beat expectations" in response.json()["text"]


@pytest.mark.unit
def test_analyze_text_rejects_short_text(client: TestClient) -> None:
    response = client.post(
        ANALYZE_URL,
        json={"ticker": "AAPL", "text": "too short"},
    )
    assert response.status_code == 422
    assert "50 characters" in response.json()["detail"]


@pytest.mark.unit
def test_analyze_text_returns_scored_sentiment(client: TestClient) -> None:
    fake_llm_response = (
        "SENTIMENT: bullish\n"
        "SCORE: 0.6\n"
        "CONFIDENCE: 0.7\n"
        "THEMES: growth\n"
        "SUMMARY: Positive outlook."
    )
    with patch(
        "app.api.v1.extended_agents._llm",
        AsyncMock(return_value=fake_llm_response),
    ):
        response = client.post(
            ANALYZE_URL,
            json={
                "ticker": "AAPL",
                "text": "Apple reported strong quarterly earnings across all segments today.",
            },
        )
    assert response.status_code == 200
    data = response.json()
    assert data["ticker"] == "AAPL"
    assert data["sentiment"] == "bullish"
    assert data["trend"] == "stable"
    assert data["recent_articles"] == []
    assert data["finnhub_sentiment_available"] is False


@pytest.mark.unit
def test_extract_text_from_corrupt_pdf_returns_422(client: TestClient) -> None:
    response = client.post(
        EXTRACT_URL,
        files={
            "file": (
                "corrupt.pdf",
                b"not actually a pdf file at all",
                "application/pdf",
            )
        },
    )
    assert response.status_code == 422
    assert "could not read pdf" in response.json()["detail"].lower()
