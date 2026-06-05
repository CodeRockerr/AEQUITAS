"""
AEQUITAS — Unit tests for agent components.

We test the pure, non-LLM parts of the agent system:
  - State structure validation
  - Document chunking
  - Vector store utilities

The LLM-calling nodes (research, thesis, critic) are integration
tests — they require a real API key and are tested manually.
"""

import pytest

from app.agents.state import ResearchState
from app.data.vector.store import chunk_text

# ── State tests ───────────────────────────────────────────────


@pytest.mark.unit
def test_research_state_accepts_ticker() -> None:
    """ResearchState should accept a ticker field."""
    state: ResearchState = {"ticker": "AAPL"}
    assert state["ticker"] == "AAPL"


@pytest.mark.unit
def test_research_state_all_optional() -> None:
    """ResearchState with total=False means all fields optional."""
    state: ResearchState = {}
    assert state.get("ticker") is None
    assert state.get("thesis") is None


@pytest.mark.unit
def test_research_state_revision_count() -> None:
    state: ResearchState = {"revision_count": 0}
    assert state["revision_count"] == 0


# ── Document chunking tests ───────────────────────────────────


@pytest.mark.unit
def test_chunk_text_basic() -> None:
    """Short text should produce one chunk."""
    text = "This is a short document about AAPL earnings."
    chunks = chunk_text(text, chunk_size=100, overlap=10)
    assert len(chunks) == 1
    assert chunks[0] == text


@pytest.mark.unit
def test_chunk_text_splits_long_document() -> None:
    """Long text should be split into multiple chunks."""
    words = ["word"] * 1200
    text = " ".join(words)
    chunks = chunk_text(text, chunk_size=500, overlap=50)
    assert len(chunks) > 1


@pytest.mark.unit
def test_chunk_text_overlap() -> None:
    """Overlapping chunks should share words at boundaries."""
    words = [f"word{i}" for i in range(600)]
    text = " ".join(words)
    chunks = chunk_text(text, chunk_size=500, overlap=50)
    assert len(chunks) >= 2

    # Last 50 words of chunk 0 should appear in chunk 1
    chunk0_words = chunks[0].split()
    chunk1_words = chunks[1].split()
    overlap_words = chunk0_words[-50:]
    assert overlap_words == chunk1_words[:50]


@pytest.mark.unit
def test_chunk_text_empty_input() -> None:
    """Empty text should return empty list."""
    assert chunk_text("") == []
    assert chunk_text("   ") == []


@pytest.mark.unit
def test_chunk_text_preserves_content() -> None:
    """All words should be present across all chunks."""
    words = [f"word{i}" for i in range(1000)]
    text = " ".join(words)
    chunks = chunk_text(text, chunk_size=300, overlap=30)

    # Every unique word in original should appear somewhere in chunks
    # (overlap means some appear twice — that's correct)
    all_chunk_words = set(" ".join(chunks).split())
    original_words = set(words)
    assert original_words.issubset(all_chunk_words)


@pytest.mark.unit
def test_chunk_size_respected() -> None:
    """Each chunk should not significantly exceed chunk_size words."""
    words = [f"word{i}" for i in range(2000)]
    text = " ".join(words)
    chunk_size = 500
    chunks = chunk_text(text, chunk_size=chunk_size, overlap=50)

    for chunk in chunks:
        word_count = len(chunk.split())
        # Allow up to chunk_size words (last chunk may be smaller)
        assert (
            word_count <= chunk_size
        ), f"Chunk has {word_count} words, expected <= {chunk_size}"


# ── Graph routing tests ───────────────────────────────────────


@pytest.mark.unit
def test_should_revise_when_revision_needed() -> None:
    """_should_revise should return 'research' when revision is needed."""
    from app.agents.graph import _should_revise

    state: ResearchState = {"revision_needed": True, "revision_count": 0}
    assert _should_revise(state) == "research"


@pytest.mark.unit
def test_should_not_revise_when_approved() -> None:
    """_should_revise should return END when thesis is approved."""
    from langgraph.graph import END

    from app.agents.graph import _should_revise

    state: ResearchState = {"revision_needed": False, "revision_count": 1}
    assert _should_revise(state) == END


@pytest.mark.unit
def test_should_not_revise_when_no_flag() -> None:
    """_should_revise defaults to END when revision_needed is absent."""
    from langgraph.graph import END

    from app.agents.graph import _should_revise

    state: ResearchState = {}
    assert _should_revise(state) == END
