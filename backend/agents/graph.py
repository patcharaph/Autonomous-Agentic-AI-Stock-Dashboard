import json
import logging
import os
from typing import Any, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from openai import OpenAI

from backend.agents.tools import fetch_news, fetch_prices
from backend.calculations import compute_indicators


logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    ticker: str
    raw_prices: Any
    technical_indicators: dict
    news_data: list[dict]
    draft_report: dict
    critic_feedback: str
    revision_count: int


def researcher_node(state: AgentState) -> AgentState:
    ticker = state["ticker"]
    prices = fetch_prices(ticker)
    news = fetch_news(ticker)
    return {
        **state,
        "raw_prices": prices,
        "news_data": news,
    }


def analyst_node(state: AgentState) -> AgentState:
    indicators = compute_indicators(state["raw_prices"])
    return {**state, "technical_indicators": indicators}


def writer_node(state: AgentState, config: dict | None = None, client: OpenAI | None = None) -> AgentState:
    """
    Uses GPT-4o (or model override) to craft a Thai report.
    Enforces JSON-only output and injects exact indicator values for the critic to verify.
    """
    model = os.getenv("REPORT_MODEL", "gpt-4o")
    cfg_client = (config or {}).get("configurable", {}).get("client") if config else None
    client = client or cfg_client or OpenAI(
        api_key=os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
    )

    system_prompt = (
        "คุณคือ Senior Investment Analyst. "
        "เขียนรายงานการวิเคราะห์หุ้นอย่างมืออาชีพเป็นภาษาไทย แต่เก็บคำ technical เป็นภาษาอังกฤษ. "
        "ห้ามคำนวณตัวเลขใหม่ ใช้ค่าที่ให้มาเท่านั้น."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": (
                "ข้อมูลตัวชี้วัด:\n"
                f"{json.dumps(state['technical_indicators'], ensure_ascii=False)}\n\n"
                "ข่าวสารล่าสุด:\n"
                f"{json.dumps(state['news_data'], ensure_ascii=False)}\n\n"
                "ข้อเสนอแนะจาก Critic (ถ้ามี): "
                f"{state.get('critic_feedback') or 'None'}\n\n"
                "โปรดส่ง JSON เท่านั้น โครงสร้าง:\n"
                "{"
                '"executive_summary": "...",'
                '"technical_outlook": "...",'
                '"risks": "...",'
                '"strategy": "...",'
                '"technical_indicators": <ใส่ค่าตัวเลขตรงนี้จงตรงกับข้อมูลด้านบน>,'
                '"confidence": "High"'
                "}"
            ),
        },
    ]

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    content = response.choices[0].message.content or "{}"
    draft = json.loads(content)
    # Ensure indicators are injected exactly
    draft["technical_indicators"] = state["technical_indicators"]
    return {
        **state,
        "draft_report": draft,
    }


def critic_node(state: AgentState) -> AgentState:
    draft = state.get("draft_report") or {}
    indicators = state["technical_indicators"]
    feedback_parts: list[str] = []

    # JSON structure validation
    required_keys = {"executive_summary", "technical_outlook", "risks", "strategy", "technical_indicators"}
    missing = required_keys - set(draft.keys())
    if missing:
        feedback_parts.append(f"Missing keys: {', '.join(sorted(missing))}")

    # Numeric consistency check
    if draft.get("technical_indicators") != indicators:
        feedback_parts.append("technical_indicators mismatch with computed values.")

    # Limit loop depth
    revision_count = state.get("revision_count", 0)
    if feedback_parts and revision_count >= 2:
        draft["confidence"] = "Low"
        return {**state, "draft_report": draft, "critic_feedback": "; ".join(feedback_parts)}

    if feedback_parts:
        return {
            **state,
            "critic_feedback": "; ".join(feedback_parts),
            "revision_count": revision_count + 1,
        }

    draft["confidence"] = "High"
    return {**state, "draft_report": draft, "critic_feedback": "", "revision_count": revision_count}


def quality_gate(state: AgentState) -> str:
    if state.get("critic_feedback"):
        if state.get("revision_count", 0) >= 2:
            return "force_end"
        return "retry"
    return "pass"


def build_graph() -> Any:
    graph = StateGraph(AgentState)
    graph.add_node("researcher", researcher_node)
    graph.add_node("analyst", analyst_node)
    graph.add_node("writer", writer_node)
    graph.add_node("critic", critic_node)

    graph.add_edge("researcher", "analyst")
    graph.add_edge("analyst", "writer")
    graph.add_edge("writer", "critic")

    graph.add_conditional_edges(
        "critic",
        quality_gate,
        {
            "retry": "writer",
            "pass": END,
            "force_end": END,
        },
    )
    graph.set_entry_point("researcher")
    memory = MemorySaver()
    return graph.compile(checkpointer=memory)


def run_workflow(ticker: str, client: OpenAI | None = None) -> AgentState:
    app = build_graph()
    initial_state: AgentState = {
        "ticker": ticker,
        "raw_prices": None,
        "technical_indicators": {},
        "news_data": [],
        "draft_report": {},
        "critic_feedback": "",
        "revision_count": 0,
    }
    return app.invoke(initial_state, config={"configurable": {"client": client}})
