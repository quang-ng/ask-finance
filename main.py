import logging
from contextlib import asynccontextmanager
from datetime import datetime

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
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
                answer = msg.content
                break

        if not answer:
            answer = "I was unable to generate an answer. Please try rephrasing your question."

    except Exception as e:
        logger.error(f"Agent error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

    return ChatResponse(
        answer=answer,
        role=profile["role"],
        user_bu=profile["user_bu"],
        timestamp=datetime.now().isoformat(),
    )


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
