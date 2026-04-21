import pandas as pd


def summarize_dataframe(df: pd.DataFrame) -> str:
    if df.empty:
        return "No data available for your current permissions."

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    if not numeric_cols:
        return df.to_markdown(index=False)

    summary_rows = []
    for col in numeric_cols:
        summary_rows.append({
            "metric": col,
            "min": f"${df[col].min():,.0f}",
            "max": f"${df[col].max():,.0f}",
            "mean": f"${df[col].mean():,.0f}",
            "total": f"${df[col].sum():,.0f}",
        })

    summary_df = pd.DataFrame(summary_rows)
    return summary_df.to_markdown(index=False)
