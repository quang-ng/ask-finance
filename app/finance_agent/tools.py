import os
import pandas as pd
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig

from app.finance_agent.configuration import Configuration
from app.finance_agent.rbac import get_permissions, is_data_type_allowed
from app.data_ingestion.csv_loader import (
    load_pl_report,
    load_opex_detail,
    load_project_roi,
    filter_dataframe,
    dataframe_to_markdown,
)
from app.data_ingestion.csv_analyzer import summarize_dataframe
from app.knowledge.vector_store import search_knowledge

OUTPUTS_DIR = os.path.join(os.path.dirname(__file__), "../../outputs")
os.makedirs(OUTPUTS_DIR, exist_ok=True)


def _get_filtered_df(data_type: str, config: Configuration) -> tuple[pd.DataFrame, str]:
    perms = get_permissions(config.role, config.user_bu, config.user_region)

    if not is_data_type_allowed(config.role, data_type):
        return pd.DataFrame(), f"Access denied: role '{config.role}' cannot access {data_type} data."

    data_type_upper = data_type.upper()
    if data_type_upper == "PNL":
        df = load_pl_report()
    elif data_type_upper == "OPEX":
        df = load_opex_detail()
    elif data_type_upper == "ROI":
        df = load_project_roi()
    else:
        return pd.DataFrame(), f"Unknown data type: {data_type}. Use PNL, OPEX, or ROI."

    df = filter_dataframe(df, perms["allowed_bus"], perms.get("allowed_regions", ["*"]))
    return df, ""


@tool
def retrieve_financial_data(data_type: str, config: RunnableConfig) -> str:
    """Retrieve financial data as a markdown table. data_type must be one of: PNL, OPEX, ROI."""
    cfg = Configuration.from_runnable_config(config)
    df, error = _get_filtered_df(data_type, cfg)
    if error:
        return error
    return dataframe_to_markdown(df)


@tool
def summarize_financial_data(data_type: str, config: RunnableConfig) -> str:
    """Retrieve a statistical summary (min, max, mean, total) of financial data. data_type: PNL, OPEX, or ROI."""
    cfg = Configuration.from_runnable_config(config)
    df, error = _get_filtered_df(data_type, cfg)
    if error:
        return error
    return summarize_dataframe(df)


@tool
def generate_excel_report(data_type: str, config: RunnableConfig) -> str:
    """Generate an Excel report for a given data type and return the file path. data_type: PNL, OPEX, or ROI."""
    cfg = Configuration.from_runnable_config(config)
    df, error = _get_filtered_df(data_type, cfg)
    if error:
        return error
    if df.empty:
        return "No data to export for your current permissions."

    filename = f"{data_type.lower()}_report_{cfg.role}_{cfg.user_bu.replace(' ', '_')}.xlsx"
    filepath = os.path.join(OUTPUTS_DIR, filename)
    df.to_excel(filepath, index=False)
    return f"Excel report generated: /outputs/{filename}"


@tool
async def search_knowledge_base(query: str) -> str:
    """Search the finance knowledge base for definitions, policies, and glossary terms."""
    return await search_knowledge(query)


QA_TOOLS = [retrieve_financial_data, summarize_financial_data, search_knowledge_base]
ANALYTICS_TOOLS = [retrieve_financial_data, summarize_financial_data]
REPORT_TOOLS = [retrieve_financial_data, generate_excel_report]
