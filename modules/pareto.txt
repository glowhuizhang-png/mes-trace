import pandas as pd
import plotly.graph_objects as go

def build_pareto_chart(df, title_suffix=""):
    # 过滤出缺陷相关类型（废品、次品外观、次品UF）
    filtered_df = df[df["类型"].isin(["废品", "次品外观", "次品UF"])]
    pareto_df = (
        filtered_df.groupby("病象")
        .size()
        .reset_index(name="数量")
        .sort_values("数量", ascending=False)
    )
    pareto_df["累计数量"] = pareto_df["数量"].cumsum()
    total = pareto_df["数量"].sum()
    pareto_df["累计占比"] = pareto_df["累计数量"] / total

    fig = go.Figure()
    fig.add_trace(go.Bar(x=pareto_df["病象"], y=pareto_df["数量"], name="数量"))
    fig.add_trace(go.Scatter(
        x=pareto_df["病象"], y=pareto_df["累计占比"],
        yaxis="y2", name="累计占比"
    ))
    fig.update_layout(
        title=f"Pareto病象分析{title_suffix}",
        yaxis2=dict(overlaying="y", side="right", tickformat=".0%"),
        height=700
    )
    return fig, pareto_df