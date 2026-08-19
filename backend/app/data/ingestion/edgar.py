"""
AEQUITAS - SEC EDGAR filing ingestion.

Fetches the most recent 10-K and 10-Q for a ticker straight from SEC
EDGAR's public JSON APIs, extracts the readable text, and stores it in
the RAG document store (app.data.vector.store) - auto-triggered by the
research agent the same way ensure_min_bars/ensure_company_info
auto-ingest price bars and company metadata, so a thesis for a ticker
nobody has touched before still gets grounded in a real filing instead
of "no filing documents ingested".

No API key required, but EDGAR requires a descriptive User-Agent
header identifying the requester (see settings.edgar_user_agent) -
generic/missing ones get blocked.
"""

import re
import time

import httpx
import structlog
from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.data.vector.store import (
    chunk_text,
    get_all_chunks_for_ticker,
    store_document_chunks,
)

log = structlog.get_logger()

TICKER_CIK_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
FILING_ARCHIVE_URL = (
    "https://www.sec.gov/Archives/edgar/data/{cik_int}/{accession_nodash}/{primary_doc}"
)

# Most recent one of each - richer business/risk-factor narrative (10-K)
# plus the latest quarterly update (10-Q), without pulling a ticker's
# entire filing history.
FORMS_TO_FETCH = ("10-K", "10-Q")

# 10-Ks run 150-300K+ characters once flattened to text, and the back
# half is financial-statement tables and exhibits that don't chunk into
# useful RAG context. Capping keeps the narrative sections (Business,
# Risk Factors, MD&A) without ingesting the whole document.
MAX_CHARS_PER_FILING = 60_000

# Module-level cache: SEC's ticker->CIK mapping changes rarely (new
# listings/delistings), so one fetch per process lifetime is enough -
# no need to hit it again for every ticker.
_cik_cache: dict[str, str] | None = None

# If the ticker-map fetch fails (EDGAR down, or its bot-detection rate
# limiting us - it's stricter in practice than the documented 10 req/s),
# back off instead of every subsequent new-ticker thesis request
# immediately retrying the same call and compounding the block.
_cik_cache_failed_at: float | None = None
_CIK_RETRY_COOLDOWN_SECONDS = 300


def _headers() -> dict[str, str]:
    return {"User-Agent": settings.edgar_user_agent}


async def _load_cik_map(client: httpx.AsyncClient) -> dict[str, str]:
    global _cik_cache, _cik_cache_failed_at

    if _cik_cache is not None:
        return _cik_cache
    if (
        _cik_cache_failed_at is not None
        and time.time() - _cik_cache_failed_at < _CIK_RETRY_COOLDOWN_SECONDS
    ):
        raise RuntimeError(
            "EDGAR ticker map fetch failed recently - backing off before retrying"
        )

    try:
        resp = await client.get(TICKER_CIK_URL, headers=_headers())
        resp.raise_for_status()
        rows = resp.json().values()
        _cik_cache = {
            row["ticker"].upper(): str(row["cik_str"]).zfill(10) for row in rows
        }
        _cik_cache_failed_at = None
        return _cik_cache
    except Exception:
        _cik_cache_failed_at = time.time()
        raise


async def _get_cik(client: httpx.AsyncClient, ticker: str) -> str | None:
    ciks = await _load_cik_map(client)
    return ciks.get(ticker.upper())


async def _recent_filings(client: httpx.AsyncClient, cik: str) -> list[dict]:
    """Most recent filing of each form in FORMS_TO_FETCH, newest first."""
    resp = await client.get(SUBMISSIONS_URL.format(cik=cik), headers=_headers())
    resp.raise_for_status()
    recent = resp.json().get("filings", {}).get("recent", {})

    forms = recent.get("form", [])
    accessions = recent.get("accessionNumber", [])
    primary_docs = recent.get("primaryDocument", [])
    dates = recent.get("filingDate", [])

    filings: list[dict] = []
    seen_forms: set[str] = set()
    for form, accession, primary_doc, date in zip(
        forms, accessions, primary_docs, dates, strict=True
    ):
        if form in FORMS_TO_FETCH and form not in seen_forms:
            filings.append(
                {
                    "form": form,
                    "accession": accession,
                    "primary_doc": primary_doc,
                    "date": date,
                }
            )
            seen_forms.add(form)
        if seen_forms == set(FORMS_TO_FETCH):
            break
    return filings


def _extract_text(html: bytes) -> str:
    """
    Strip a filing's HTML down to readable prose.

    Modern filings are Inline XBRL: the visible document is wrapped
    around a huge block of machine-readable tagging data, usually an
    <ix:header> element and/or display:none divs. A plain get_text()
    dumps that taxonomy data (thousands of "http://fasb.org/us-gaap/..."
    strings) ahead of the actual filing text unless it's removed first.
    """
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style"]):
        tag.decompose()
    for tag in soup.find_all(re.compile(r"^ix:header$", re.I)):
        tag.decompose()
    for div in soup.find_all("div", style=re.compile(r"display:\s*none")):
        div.decompose()

    return soup.get_text(separator=" ", strip=True)


async def _fetch_filing_text(
    client: httpx.AsyncClient, cik: str, accession: str, primary_doc: str
) -> str:
    url = FILING_ARCHIVE_URL.format(
        cik_int=int(cik),
        accession_nodash=accession.replace("-", ""),
        primary_doc=primary_doc,
    )
    resp = await client.get(url, headers=_headers(), timeout=30.0)
    resp.raise_for_status()
    return _extract_text(resp.content)[:MAX_CHARS_PER_FILING]


async def ensure_filings_ingested(db: AsyncSession, ticker: str) -> None:
    """
    Best-effort auto-ingest of the most recent 10-K and 10-Q for
    `ticker` from SEC EDGAR, if no filing chunks exist for it yet.

    Mirrors ensure_min_bars/ensure_company_info: silent no-op if
    already populated, swallows failures (bad ticker, EDGAR hiccup,
    filing has no CIK yet) so a slow/failed fetch never blocks thesis
    generation - it just falls back to price + company-metadata
    context, same as before this existed.
    """
    ticker = ticker.upper().strip()
    if await get_all_chunks_for_ticker(db, ticker, limit=1):
        return

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            cik = await _get_cik(client, ticker)
            if cik is None:
                log.info("edgar_cik_not_found", ticker=ticker)
                return

            filings = await _recent_filings(client, cik)
            for filing in filings:
                text = await _fetch_filing_text(
                    client, cik, filing["accession"], filing["primary_doc"]
                )
                if len(text.strip()) < 200:
                    continue
                chunks = chunk_text(text, chunk_size=500, overlap=50)
                stored = await store_document_chunks(
                    db,
                    ticker=ticker,
                    source=f"{filing['form']} ({filing['date']})",
                    chunks=chunks,
                )
                log.info(
                    "edgar_filing_ingested",
                    ticker=ticker,
                    form=filing["form"],
                    chunks=stored,
                )
    except Exception as e:
        log.warning("edgar_auto_ingest_failed", ticker=ticker, error=str(e))
