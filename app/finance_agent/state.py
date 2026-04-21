from typing import Optional
from typing_extensions import TypedDict, Annotated
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class InputState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


class State(InputState):
    user_role: str
    user_bu: str
    user_region: str
    active_agent: str
    retrieved_data: Optional[str]
    chart_specs: Optional[list[str]]
    report_path: Optional[str]
