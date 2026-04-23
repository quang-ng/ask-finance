import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime

from dotenv import load_dotenv
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.db import init_pool, close_pool, DATABASE_URL
    from app.knowledge.vector_store import init_vector_store
    from app.finance_agent.graph import build_graph
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

    # App-level pool for knowledge base
    pool = await init_pool()
    await init_vector_store(pool)

    # LangGraph checkpointer — manages its own connection pool
    async with AsyncPostgresSaver.from_conn_string(DATABASE_URL) as checkpointer:
        await checkpointer.setup()
        app.state.graph = build_graph(checkpointer=checkpointer)
        logger.info("Ask Finance agent ready (pgvector + checkpointer)")
        yield

    await close_pool()


app = FastAPI(title="Ask Finance", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")


ROLE_PROFILES = {
    "alice": {"role": "analyst",   "user_bu": "Electronics",    "user_region": "Asia"},
    "bob":   {"role": "bu_gm",     "user_bu": "Electronics",    "user_region": "All"},
    "carol": {"role": "bu_gm",     "user_bu": "Consumer Goods", "user_region": "All"},
    "david": {"role": "group_cfo", "user_bu": "All",            "user_region": "All"},
}


class ChatRequest(BaseModel):
    user: str = "alice"
    question: str
    thread_id: str = "default"


class ChatResponse(BaseModel):
    answer: str
    role: str
    user_bu: str
    timestamp: str
    tools_used: list[str] = []
    data_sources: list[str] = []


@app.get("/")
async def root():
    return FileResponse("static/index.html")


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    graph = app.state.graph
    profile = ROLE_PROFILES.get(request.user, ROLE_PROFILES["alice"])

    config = {
        "configurable": {
            "thread_id": request.thread_id,
            "role": profile["role"],
            "user_bu": profile["user_bu"],
            "user_region": profile["user_region"],
        }
    }

    try:
        from langchain_core.messages import HumanMessage, AIMessage

        result = await graph.ainvoke(
            {"messages": [HumanMessage(content=request.question)]},
            config=config,
        )

        answer = ""
        for msg in reversed(result.get("messages", [])):
            if isinstance(msg, AIMessage) and msg.content and not msg.tool_calls:
                content = msg.content
                if isinstance(content, list):
                    # Content blocks: [{'type': 'text', 'text': '...'}, ...]
                    content = "".join(
                        block.get("text", "") if isinstance(block, dict) else str(block)
                        for block in content
                    )
                answer = content
                break

        if not answer:
            answer = "I was unable to generate an answer. Please try rephrasing your question."

        # Collect which tools were called and which data types were accessed
        tools_used: list[str] = []
        data_sources: list[str] = []
        for msg in result.get("messages", []):
            if isinstance(msg, AIMessage) and msg.tool_calls:
                for tc in msg.tool_calls:
                    name = tc.get("name", "")
                    if name and name not in tools_used:
                        tools_used.append(name)
                    if name in ("retrieve_financial_data", "summarize_financial_data"):
                        dt = tc.get("args", {}).get("data_type", "")
                        if dt and dt not in data_sources:
                            data_sources.append(dt.upper())

    except Exception as e:
        logger.error(f"Agent error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

    return ChatResponse(
        answer=answer,
        role=profile["role"],
        user_bu=profile["user_bu"],
        timestamp=datetime.now().isoformat(),
        tools_used=tools_used,
        data_sources=data_sources,
    )


_ROUTING_NAMES = ("qa_agent", "analytics_agent", "report_agent")


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    graph = app.state.graph
    profile = ROLE_PROFILES.get(request.user, ROLE_PROFILES["alice"])

    config = {
        "configurable": {
            "thread_id": request.thread_id,
            "role": profile["role"],
            "user_bu": profile["user_bu"],
            "user_region": profile["user_region"],
        }
    }

    async def generate():
        from langchain_core.messages import HumanMessage

        tools_used: list[str] = []
        data_sources: list[str] = []

        sup_buf: list[str] = []
        sup_decided = False
        sup_streaming = False
        tokens_yielded = False
        specialist_final_content = ""

        def _is_routing_prefix(text: str) -> bool:
            t = text.strip().lower()
            return any(name.startswith(t) for name in _ROUTING_NAMES)

        def _extract_content(obj) -> str:
            c = obj.content if hasattr(obj, "content") else obj
            if isinstance(c, list):
                return "".join(
                    b.get("text", "") if isinstance(b, dict) else str(b) for b in c
                )
            return c if isinstance(c, str) else ""

        try:
            async for event in graph.astream_events(
                {"messages": [HumanMessage(content=request.question)]},
                config=config,
                version="v2",
            ):
                kind = event["event"]
                node = event.get("metadata", {}).get("langgraph_node", "")

                if kind == "on_chat_model_stream" and node == "supervisor":
                    chunk = event["data"]["chunk"]
                    content = _extract_content(chunk)
                    if not content:
                        continue
                    if sup_decided:
                        if sup_streaming:
                            tokens_yielded = True
                            yield f"data: {json.dumps({'type': 'token', 'content': content})}\n\n"
                    else:
                        sup_buf.append(content)
                        accumulated = "".join(sup_buf).strip()
                        if not _is_routing_prefix(accumulated) and len(accumulated) >= 5:
                            sup_decided = True
                            sup_streaming = True
                            tokens_yielded = True
                            yield f"data: {json.dumps({'type': 'token', 'content': accumulated})}\n\n"
                            sup_buf.clear()

                elif kind == "on_chat_model_end" and node == "supervisor":
                    if sup_buf:
                        text = "".join(sup_buf).strip().lower()
                        if text not in _ROUTING_NAMES:
                            tokens_yielded = True
                            yield f"data: {json.dumps({'type': 'token', 'content': ''.join(sup_buf)})}\n\n"
                    sup_buf.clear()
                    sup_decided = False
                    sup_streaming = False

                elif kind == "on_chat_model_end" and node in _ROUTING_NAMES:
                    output = event["data"].get("output", None)
                    if output is not None:
                        has_tool_calls = bool(getattr(output, "tool_calls", []))
                        if not has_tool_calls:
                            specialist_final_content = _extract_content(output)

                elif kind == "on_tool_start":
                    name = event.get("name", "")
                    if name:
                        if name not in tools_used:
                            tools_used.append(name)
                        args = event["data"].get("input", {})
                        if isinstance(args, dict):
                            dt = args.get("data_type", "")
                            if dt and dt not in data_sources:
                                data_sources.append(dt.upper())
                        yield f"data: {json.dumps({'type': 'status', 'message': f'Using {name}…'})}\n\n"

                elif kind == "on_tool_end":
                    name = event.get("name", "")
                    output = event["data"].get("output", "")
                    content = _extract_content(output)
                    if name and content:
                        yield f"data: {json.dumps({'type': 'tool_result', 'name': name, 'content': content})}\n\n"

            if not tokens_yielded and specialist_final_content:
                yield f"data: {json.dumps({'type': 'token', 'content': specialist_final_content})}\n\n"

            yield f"data: {json.dumps({'type': 'done', 'role': profile['role'], 'user_bu': profile['user_bu'], 'timestamp': datetime.now().isoformat(), 'tools_used': tools_used, 'data_sources': data_sources})}\n\n"

        except Exception as e:
            logger.error(f"Stream error: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/dashboard")
async def dashboard(user: str = Query("alice")):
    profile = ROLE_PROFILES.get(user, ROLE_PROFILES["alice"])
    user_bu = profile["user_bu"]
    user_region = profile["user_region"]

    pl = pd.read_csv("data/pl_report.csv")
    opex_df = pd.read_csv("data/opex_detail.csv")

    if user_bu != "All":
        pl = pl[pl["business_unit"] == user_bu]
        opex_df = opex_df[opex_df["business_unit"] == user_bu]
    if user_region != "All":
        pl = pl[pl["region"] == user_region]
        opex_df = opex_df[opex_df["region"] == user_region]

    periods = sorted(pl["period"].unique())
    latest, prev = periods[-1], periods[-2]

    def agg(df, period, col):
        return float(df[df["period"] == period][col].sum())

    def pct(curr, prior):
        return round((curr - prior) / prior * 100, 1) if prior else 0.0

    rev_l, rev_p     = agg(pl, latest, "revenue"),    agg(pl, prev, "revenue")
    ebit_l, ebit_p   = agg(pl, latest, "ebit"),       agg(pl, prev, "ebit")
    opex_l, opex_p   = agg(pl, latest, "opex"),       agg(pl, prev, "opex")
    ni_l, ni_p       = agg(pl, latest, "net_income"),  agg(pl, prev, "net_income")

    opex_latest = opex_df[opex_df["period"] == latest]

    return {
        "latest_period": latest,
        "prev_period": prev,
        "kpis": {
            "revenue":    {"value": round(rev_l  / 1e6, 2), "change": pct(rev_l,  rev_p)},
            "ebit":       {"value": round(ebit_l / 1e6, 2), "change": pct(ebit_l, ebit_p)},
            "opex":       {"value": round(opex_l / 1e6, 2), "change": pct(opex_l, opex_p)},
            "net_income": {"value": round(ni_l   / 1e6, 2), "change": pct(ni_l,   ni_p)},
        },
        "ebit_trend": [
            {"period": p, "ebit": round(agg(pl, p, "ebit") / 1e6, 2)}
            for p in periods
        ],
        "opex_breakdown": {
            "Headcount": round(float(opex_latest["headcount"].sum()) / 1e6, 2),
            "Marketing": round(float(opex_latest["marketing"].sum())  / 1e6, 2),
            "IT":        round(float(opex_latest["it"].sum())         / 1e6, 2),
            "Travel":    round(float(opex_latest["travel"].sum())     / 1e6, 2),
            "Other":     round(float(opex_latest["other"].sum())      / 1e6, 2),
        },
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
