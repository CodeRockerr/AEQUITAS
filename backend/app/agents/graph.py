"""
AEQUITAS — LangGraph research agent graph.

Graph structure:
  START → research → quant → thesis → critic
                                          ↓
                                (revision?) → research (loop)
                                (approved?) → END
"""

from typing import Any

from langgraph.graph import END, START, StateGraph  # type: ignore[import-untyped]

from app.agents.nodes import (
    critic_node,
    quant_node,
    research_node,
    thesis_node,
)
from app.agents.state import ResearchState


def _should_revise(state: ResearchState) -> str:
    """
    Conditional edge: routes to 'research' for revision or END if approved.
    """
    if state.get("revision_needed", False):
        return "research"
    return END


def build_research_graph(db: Any) -> Any:
    """
    Build and compile the LangGraph research agent.

    Returns Any to avoid Pylance issues with CompiledStateGraph
    vs StateGraph — at runtime this is a CompiledStateGraph.

    Args:
        db: AsyncSession injected from FastAPI
    """

    # Node wrappers that close over the db session
    async def research(state: ResearchState) -> dict:  # type: ignore[type-arg]
        return await research_node(dict(state), db)

    async def quant(state: ResearchState) -> dict:  # type: ignore[type-arg]
        return await quant_node(dict(state), db)

    async def thesis_gen(state: ResearchState) -> dict:  # type: ignore[type-arg]
        return await thesis_node(dict(state))

    async def critic(state: ResearchState) -> dict:  # type: ignore[type-arg]
        return await critic_node(dict(state))

    graph: StateGraph = StateGraph(ResearchState)

    graph.add_node("research", research)
    graph.add_node("quant", quant)
    graph.add_node("thesis_gen", thesis_gen)
    graph.add_node("critic", critic)

    graph.add_edge(START, "research")
    graph.add_edge("research", "quant")
    graph.add_edge("quant", "thesis_gen")
    graph.add_edge("thesis_gen", "critic")

    graph.add_conditional_edges(
        "critic",
        _should_revise,
        {
            "research": "research",
            END: END,
        },
    )

    return graph.compile()


async def run_research_agent(
    ticker: str,
    db: Any,
    research_depth: str = "quick",
) -> ResearchState:
    """
    Run the full research agent pipeline for a ticker.
    """
    compiled = build_research_graph(db)

    initial_state: ResearchState = {
        "ticker": ticker.upper(),
        "research_depth": research_depth,
        "revision_count": 0,
        "errors": [],
    }

    # ainvoke is available on CompiledStateGraph — Pylance doesn't
    # know this because the return type is typed as StateGraph
    final_state: ResearchState = await compiled.ainvoke(initial_state)  # type: ignore[union-attr]
    return final_state
