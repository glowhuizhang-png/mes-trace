import streamlit as st
import pandas as pd
import plotly.graph_objects as go

def build_pareto_chart(df):
    """
    绘制 Pareto 病象分析图。
    在函数内部添加选择器，用户可选择“全部”或“外观废次品”。
    """
    # ---------- 增加选择器 ----------
    option = st.radio(
        "选择分析范围",
        ["全部", "外观废次品"],
        horizontal=True,
        key="pareto_scope"
    )

    # 根据选择过滤数据
    if option == "外观废次品":
        filtered_df = df[df["类型"].isin(["废品", "次品外观"])]
    else:
        filtered_df = df[df["类型"].isin(["废品", "次品外观", "次品UF"])]

    # 如果过滤后为空，给出提示并返回空图表
    if filtered_df.empty:
        st.warning("当前选择范围内无数据")
        empty_fig = go.Figure()
        empty_fig.update_layout(title="无数据")
        return empty_fig, pd.DataFrame(columns=["病象", "数量"])

    # ---------- 原有 Pareto 计算 ----------
    pareto_df = (
        filtered_df
        .groupby("病象")
        .size()
        .reset_index(name="数量")
        .sort_values("数量", ascending=False)
    )
    pareto_df["累计数量"] = pareto_df["数量"].cumsum()
    total = pareto_df["数量"].sum()
    pareto_df["累计占比"] = pareto_df["累计数量"] / total

    # ---------- 绘图 ----------
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=pareto_df["病象"],
        y=pareto_df["数量"],
        name="数量",
        text=pareto_df["数量"],
        textposition='outside'
    ))
    fig.add_trace(go.Scatter(
        x=pareto_df["病象"],
        y=pareto_df["累计占比"],
        yaxis="y2",
        name="累计占比",
        mode='lines+markers',
        line=dict(color='red', width=2),
        marker=dict(size=8)
    ))

    fig.update_layout(
        yaxis2=dict(
            overlaying="y",
            side="right",
            tickformat=".0%",
            range=[0, 1.05]
        ),
        height=700,
        template="plotly_white",
        title=dict(
            text=f"Pareto 病象分析（{option}）",
            font=dict(size=26, family="Microsoft YaHei")
        ),
        xaxis=dict(
            title=None,
            tickfont=dict(size=16, family="Microsoft YaHei")
        ),
        yaxis=dict(
            title="数量",
            tickfont=dict(size=16, family="Microsoft YaHei")
        ),
        legend=dict(
            font=dict(size=16, family="Microsoft YaHei")
        )
    )

    return fig, pareto_df