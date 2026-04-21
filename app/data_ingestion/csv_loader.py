import os
import pandas as pd
from typing import Optional

DATA_DIR = os.path.join(os.path.dirname(__file__), "../../data")

_cache: dict[str, pd.DataFrame] = {}


def _load_csv(filename: str) -> pd.DataFrame:
    if filename not in _cache:
        path = os.path.join(DATA_DIR, filename)
        _cache[filename] = pd.read_csv(path)
    return _cache[filename].copy()


def load_pl_report() -> pd.DataFrame:
    return _load_csv("pl_report.csv")


def load_opex_detail() -> pd.DataFrame:
    return _load_csv("opex_detail.csv")


def load_project_roi() -> pd.DataFrame:
    return _load_csv("project_roi.csv")


def filter_dataframe(
    df: pd.DataFrame,
    allowed_bus: list[str],
    allowed_regions: list[str],
) -> pd.DataFrame:
    if "*" not in allowed_bus and "business_unit" in df.columns:
        df = df[df["business_unit"].isin(allowed_bus)]
    if "*" not in allowed_regions and "region" in df.columns:
        df = df[df["region"].isin(allowed_regions)]
    return df


def dataframe_to_markdown(df: pd.DataFrame) -> str:
    if df.empty:
        return "No data available for your current permissions."
    return df.to_markdown(index=False)
