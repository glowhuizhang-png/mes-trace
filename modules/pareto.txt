import streamlit as st
import pandas as pd
import plotly.graph_objects as go

def build_pareto_chart(df, scope="全部"):
    if scope == "外观废次品":
        filtered_df = df[df["类型"].isin(["废品", "次品外观"])]
    else:
        filtered_df = df[df["类型"].isin(["废品", "次品外观", "次品UF"])]
    if filtered_df.empty:
        return go.Figure(), pd.DataFrame()
    pareto_df = filtered_df.groupby("病象").size().reset_index(name="数量").sort_values("数量", ascending=False)
    pareto_df["累计数量"] = pareto_df["数量"].cumsum()
    pareto_df["累计占比"] = pareto_df["累计数量"] / pareto_df["数量"].sum()
    fig = go.Figure()
    fig.add_bar(x=pareto_df["病象"], y=pareto_df["数量"], text=pareto_df["数量"], textposition="outside", name="数量")
    fig.add_scatter(x=pareto_df["病象"], y=pareto_df["累计占比"], mode="lines+markers", yaxis="y2", name="累计占比")
    fig.update_layout(
        template="plotly_white", height=430, margin=dict(l=20, r=20, t=50, b=20),
        title=f"Pareto分析（{scope}）", yaxis2=dict(overlaying="y", side="right", tickformat=".0%", range=[0, 1.05])
    )
    return fig, pareto_df

def render_pareto_panel(df):
    scope = st.radio("选择分析范围", ["全部", "外观废次品"], horizontal=True, key="pareto_scope")
    fig, pareto_df = build_pareto_chart(df, scope)
    event = st.plotly_chart(fig, use_container_width=True, on_select="rerun", key="dashboard_pareto")
    if event and event.selection and event.selection.points:
        cause = event.selection.points[0]["x"]
        detail = df[df["病象"] == cause]
        st.session_state["dashboard_detail"] = detail
        if "硫化日期" in detail.columns:
            st.session_state["dashboard_trend"] = detail.groupby("硫化日期").size().sort_index()
        st.rerun()
    return pareto_df