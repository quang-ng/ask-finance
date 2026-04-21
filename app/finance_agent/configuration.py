from dataclasses import dataclass, field
from typing import Annotated, Optional
from langchain_core.runnables import RunnableConfig


@dataclass(kw_only=True)
class Configuration:
    model: Annotated[str, {"__template_metadata__": {"kind": "llm"}}] = field(
        default="gemini-2.0-flash",
        metadata={"description": "The Gemini model to use"},
    )
    role: str = field(
        default="analyst",
        metadata={"description": "User role: analyst | bu_gm | group_cfo"},
    )
    user_bu: str = field(
        default="Electronics",
        metadata={"description": "The user's assigned business unit"},
    )
    user_region: str = field(
        default="Asia",
        metadata={"description": "The user's assigned region (or 'All')"},
    )
    max_search_results: int = field(
        default=3,
        metadata={"description": "Max knowledge base search results"},
    )

    @classmethod
    def from_runnable_config(cls, config: Optional[RunnableConfig] = None) -> "Configuration":
        configurable = (config or {}).get("configurable", {})
        return cls(
            model=configurable.get("model", "gemini-2.0-flash"),
            role=configurable.get("role", "analyst"),
            user_bu=configurable.get("user_bu", "Electronics"),
            user_region=configurable.get("user_region", "Asia"),
            max_search_results=configurable.get("max_search_results", 3),
        )
