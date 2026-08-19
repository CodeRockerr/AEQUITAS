"""
AEQUITAS - Unit tests for SEC EDGAR filing auto-ingestion.

Mocks at the module's own internal async helpers - the same boundary
test_price_stream.py uses for its async orchestration tests - rather
than hitting real EDGAR endpoints or adding an HTTP-mocking dependency.
_extract_text is pure HTML-to-text and is tested directly against
synthetic filing snippets.
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.data.ingestion import edgar


class FakeResponse:
    """Minimal stand-in for httpx.Response in unit tests."""

    def __init__(self, json_data=None, content: bytes = b""):
        self._json = json_data
        self.content = content

    def raise_for_status(self) -> None:
        pass

    def json(self):
        return self._json


@pytest.fixture(autouse=True)
def reset_edgar_module_cache():
    """
    edgar.py caches the ticker->CIK map (and failure timestamp) at
    module scope for the process lifetime - reset between tests so
    one test's cache state can't leak into another's.
    """
    edgar._cik_cache = None
    edgar._cik_cache_failed_at = None
    yield
    edgar._cik_cache = None
    edgar._cik_cache_failed_at = None


# ── _extract_text: pure HTML -> readable prose ────────────────


@pytest.mark.unit
def test_extract_text_strips_ix_header_taxonomy_noise() -> None:
    html = (
        b"<html><body>"
        b"<ix:header>http://fasb.org/us-gaap/2025#LongTermDebt taxonomy noise</ix:header>"
        b"<p>UNITED STATES SECURITIES AND EXCHANGE COMMISSION</p>"
        b"</body></html>"
    )
    text = edgar._extract_text(html)
    assert "taxonomy noise" not in text
    assert "SECURITIES AND EXCHANGE COMMISSION" in text


@pytest.mark.unit
def test_extract_text_strips_hidden_divs() -> None:
    html = (
        b"<html><body>"
        b'<div style="display:none">hidden ixbrl facts should not appear</div>'
        b"<p>Apple Inc. Annual Report</p>"
        b"</body></html>"
    )
    text = edgar._extract_text(html)
    assert "hidden ixbrl facts" not in text
    assert "Apple Inc. Annual Report" in text


@pytest.mark.unit
def test_extract_text_strips_script_and_style() -> None:
    html = (
        b"<html><head><style>.a{color:red}</style></head>"
        b"<body><script>var x = 1;</script><p>Real filing text</p></body></html>"
    )
    text = edgar._extract_text(html)
    assert "color:red" not in text
    assert "var x" not in text
    assert "Real filing text" in text


# ── _load_cik_map / _get_cik: caching + backoff ───────────────


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_cik_map_caches_after_first_success() -> None:
    client = AsyncMock()
    client.get = AsyncMock(
        return_value=FakeResponse(
            json_data={
                "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}
            }
        )
    )

    first = await edgar._load_cik_map(client)
    assert first["AAPL"] == "0000320193"

    client.get.reset_mock()
    second = await edgar._load_cik_map(client)
    assert second == first
    client.get.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_cik_map_backs_off_after_failure() -> None:
    client = AsyncMock()
    client.get = AsyncMock(side_effect=RuntimeError("network down"))

    with pytest.raises(RuntimeError, match="network down"):
        await edgar._load_cik_map(client)

    client.get.reset_mock()
    with pytest.raises(RuntimeError, match="backing off"):
        await edgar._load_cik_map(client)
    client.get.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_cik_returns_none_for_unknown_ticker() -> None:
    client = AsyncMock()
    client.get = AsyncMock(
        return_value=FakeResponse(
            json_data={
                "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}
            }
        )
    )
    assert await edgar._get_cik(client, "ZZZZZ") is None


# ── _recent_filings: parses submissions JSON, dedupes forms ──


@pytest.mark.unit
@pytest.mark.asyncio
async def test_recent_filings_picks_most_recent_of_each_form() -> None:
    submissions_json = {
        "filings": {
            "recent": {
                "form": ["10-Q", "8-K", "10-Q", "10-K"],
                "accessionNumber": ["acc-q1", "acc-8k", "acc-q0", "acc-k0"],
                "primaryDocument": ["q1.htm", "8k.htm", "q0.htm", "k0.htm"],
                "filingDate": ["2026-05-01", "2026-04-01", "2026-01-30", "2025-10-31"],
            }
        }
    }
    client = AsyncMock()
    client.get = AsyncMock(return_value=FakeResponse(json_data=submissions_json))

    filings = await edgar._recent_filings(client, "0000320193")

    assert {f["form"] for f in filings} == {"10-Q", "10-K"}
    q_filing = next(f for f in filings if f["form"] == "10-Q")
    assert q_filing["accession"] == "acc-q1"  # first (newest) 10-Q, not the second one


@pytest.mark.unit
@pytest.mark.asyncio
async def test_recent_filings_empty_when_no_matching_forms() -> None:
    submissions_json = {
        "filings": {
            "recent": {
                "form": ["8-K", "4"],
                "accessionNumber": ["a", "b"],
                "primaryDocument": ["a.htm", "b.htm"],
                "filingDate": ["2026-01-01", "2026-01-02"],
            }
        }
    }
    client = AsyncMock()
    client.get = AsyncMock(return_value=FakeResponse(json_data=submissions_json))

    filings = await edgar._recent_filings(client, "123")
    assert filings == []


# ── _fetch_filing_text: fetch + extract + truncate ────────────


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fetch_filing_text_extracts_and_truncates() -> None:
    html_content = b"<html><body><p>" + b"word " * 20_000 + b"</p></body></html>"
    client = AsyncMock()
    client.get = AsyncMock(return_value=FakeResponse(content=html_content))

    text = await edgar._fetch_filing_text(
        client, "320193", "0000320193-25-000079", "aapl.htm"
    )

    assert "word" in text
    assert len(text) <= edgar.MAX_CHARS_PER_FILING


# ── ensure_filings_ingested: end-to-end control flow ──────────


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ensure_filings_ingested_skips_if_already_populated() -> None:
    with (
        patch(
            "app.data.ingestion.edgar.get_all_chunks_for_ticker",
            AsyncMock(return_value=[{"content": "already here"}]),
        ),
        patch("app.data.ingestion.edgar._get_cik") as mock_get_cik,
    ):
        await edgar.ensure_filings_ingested(AsyncMock(), "AAPL")
        mock_get_cik.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ensure_filings_ingested_noop_when_cik_not_found() -> None:
    with (
        patch(
            "app.data.ingestion.edgar.get_all_chunks_for_ticker",
            AsyncMock(return_value=[]),
        ),
        patch("app.data.ingestion.edgar._get_cik", AsyncMock(return_value=None)),
        patch("app.data.ingestion.edgar._recent_filings", AsyncMock()) as mock_recent,
        patch(
            "app.data.ingestion.edgar.store_document_chunks", AsyncMock()
        ) as mock_store,
    ):
        await edgar.ensure_filings_ingested(AsyncMock(), "ZZZZ")
        mock_recent.assert_not_called()
        mock_store.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ensure_filings_ingested_stores_chunks_for_each_filing() -> None:
    filings = [
        {
            "form": "10-K",
            "accession": "0000320193-25-000079",
            "primary_doc": "aapl.htm",
            "date": "2025-10-31",
        }
    ]
    long_text = "word " * 300  # comfortably over the 200-char minimum

    with (
        patch(
            "app.data.ingestion.edgar.get_all_chunks_for_ticker",
            AsyncMock(return_value=[]),
        ),
        patch(
            "app.data.ingestion.edgar._get_cik", AsyncMock(return_value="0000320193")
        ),
        patch(
            "app.data.ingestion.edgar._recent_filings",
            AsyncMock(return_value=filings),
        ),
        patch(
            "app.data.ingestion.edgar._fetch_filing_text",
            AsyncMock(return_value=long_text),
        ),
        patch(
            "app.data.ingestion.edgar.store_document_chunks", AsyncMock(return_value=5)
        ) as mock_store,
    ):
        await edgar.ensure_filings_ingested(AsyncMock(), "aapl")

        mock_store.assert_called_once()
        _, kwargs = mock_store.call_args
        assert kwargs["ticker"] == "AAPL"
        assert "10-K" in kwargs["source"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ensure_filings_ingested_skips_filing_below_min_length() -> None:
    filings = [
        {"form": "10-K", "accession": "a", "primary_doc": "b", "date": "2025-01-01"}
    ]

    with (
        patch(
            "app.data.ingestion.edgar.get_all_chunks_for_ticker",
            AsyncMock(return_value=[]),
        ),
        patch("app.data.ingestion.edgar._get_cik", AsyncMock(return_value="123")),
        patch(
            "app.data.ingestion.edgar._recent_filings",
            AsyncMock(return_value=filings),
        ),
        patch(
            "app.data.ingestion.edgar._fetch_filing_text",
            AsyncMock(return_value="too short"),
        ),
        patch(
            "app.data.ingestion.edgar.store_document_chunks", AsyncMock()
        ) as mock_store,
    ):
        await edgar.ensure_filings_ingested(AsyncMock(), "AAPL")
        mock_store.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ensure_filings_ingested_swallows_exceptions() -> None:
    with (
        patch(
            "app.data.ingestion.edgar.get_all_chunks_for_ticker",
            AsyncMock(return_value=[]),
        ),
        patch(
            "app.data.ingestion.edgar._get_cik",
            AsyncMock(side_effect=RuntimeError("boom")),
        ),
    ):
        # Must not raise - a slow/failed EDGAR fetch should never block
        # thesis generation.
        await edgar.ensure_filings_ingested(AsyncMock(), "AAPL")
