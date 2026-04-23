from typing import Literal
from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from app.finance_agent.configuration import Configuration
from app.finance_agent.state import State, InputState
from app.finance_agent.prompts import (
    SUPERVISOR_PROMPT,
    QA_AGENT_PROMPT,
    ANALYTICS_AGENT_PROMPT,
    REPORT_AGENT_PROMPT,
    get_system_prompt,
)
from app.finance_agent.tools import QA_TOOLS, ANALYTICS_TOOLS, REPORT_TOOLS
from app.finance_agent.utils import load_chat_model

AGENT_NAMES = ["qa_agent", "analytics_agent", "report_agent"]


# ── Supervisor ──────────────────────────────────────────────────────────────

async def supervisor_node(state: State, config: RunnableConfig) -> dict:
    cfg = Configuration.from_runnable_config(config)
    llm = load_chat_model(cfg.model)

    system = get_system_prompt(SUPERVISOR_PROMPT)
    messages = [SystemMessage(content=system)] + state["messages"]

    response = None
    async for chunk in llm.astream(messages):
        response = chunk if response is None else response + chunk

    return {"messages": [response], "active_agent": "supervisor"}


def route_supervisor(state: State) -> Literal["qa_agent", "analytics_agent", "report_agent", "__end__"]:
    last = state["messages"][-1]
    if not isinstance(last, AIMessage):
        return "__end__"

    content = last.content.strip().lower()

    if "analytics_agent" in content:
        return "analytics_agent"
    if "report_agent" in content:
        return "report_agent"
    if "qa_agent" in content:
        return "qa_agent"
    # Supervisor returned a final answer
    return "__end__"


# ── Specialist agent factory ─────────────────────────────────────────────────

def _make_agent_node(system_prompt_template: str, tools: list):
    tool_names = [t.name for t in tools]

    async def agent_node(state: State, config: RunnableConfig) -> dict:
        cfg = Configuration.from_runnable_config(config)
        llm = load_chat_model(cfg.model).bind_tools(tools)

        system = get_system_prompt(system_prompt_template)
        messages = [SystemMessage(content=system)] + state["messages"]

        response = await llm.ainvoke(messages)
        return {"messages": [response]}

    def route_agent(state: State) -> Literal["tools", "supervisor"]:
        last = state["messages"][-1]
        if isinstance(last, AIMessage) and last.tool_calls:
            return "tools"
        return "supervisor"

    return agent_node, route_agent, tool_names


qa_node, route_qa, _qa_tool_names = _make_agent_node(QA_AGENT_PROMPT, QA_TOOLS)
analytics_node, route_analytics, _analytics_tool_names = _make_agent_node(ANALYTICS_AGENT_PROMPT, ANALYTICS_TOOLS)
report_node, route_report, _report_tool_names = _make_agent_node(REPORT_AGENT_PROMPT, REPORT_TOOLS)


# ── Graph assembly ────────────────────────────────────────────────────────────

def build_graph(checkpointer=None):
    workflow = StateGraph(State, input=InputState, config_schema=Configuration)

    # Nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("qa_agent", qa_node)
    workflow.add_node("analytics_agent", analytics_node)
    workflow.add_node("report_agent", report_node)
    workflow.add_node("qa_tools", ToolNode(QA_TOOLS))
    workflow.add_node("analytics_tools", ToolNode(ANALYTICS_TOOLS))
    workflow.add_node("report_tools", ToolNode(REPORT_TOOLS))

    # Entry point
    workflow.set_entry_point("supervisor")

    # Supervisor routes to specialists or ends
    workflow.add_conditional_edges(
        "supervisor",
        route_supervisor,
        {
            "qa_agent": "qa_agent",
            "analytics_agent": "analytics_agent",
            "report_agent": "report_agent",
            "__end__": END,
        },
    )

    # QA agent ReAct loop
    workflow.add_conditional_edges("qa_agent", route_qa, {"tools": "qa_tools", "supervisor": "supervisor"})
    workflow.add_edge("qa_tools", "qa_agent")

    # Analytics agent ReAct loop
    workflow.add_conditional_edges("analytics_agent", route_analytics, {"tools": "analytics_tools", "supervisor": "supervisor"})
    workflow.add_edge("analytics_tools", "analytics_agent")

    # Report agent ReAct loop
    workflow.add_conditional_edges("report_agent", route_report, {"tools": "report_tools", "supervisor": "supervisor"})
    workflow.add_edge("report_tools", "report_agent")

    return workflow.compile(checkpointer=checkpointer)
