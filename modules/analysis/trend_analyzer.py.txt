import streamlit as st
import pandas as pd
import plotly.express as px

def _plot_top5(series, name, color_scale):
    """生成TOP5水平条形图，返回图表对象或None"""
    ser = series.astype(str).replace("nan", "").replace("None", "")
    ser = ser[ser != ""]
    if ser.empty:
        return None
    top = ser.value_counts().head(5).reset_index()
    top.columns = [name, "数量"]
    fig = px.bar(top, x="数量", y=name, orientation="h", title=f"{name} TOP5", text="数量", color="数量", color_continuous_scale=color_scale)
    fig.update_traces(textposition="outside", textfont=dict(size=16, color="black"), marker=dict(line=dict(color='black', width=0.5)))
    fig.update_layout(height=300, bargap=0.4, margin=dict(l=0, r=0, t=40, b=0), xaxis_title=None, yaxis_title=None, xaxis_showgrid=False, yaxis_showgrid=False, coloraxis_showscale=False, font=dict(color="black"))
    return fig

def render_concentration_chart_with_drilldown(combined_df, photo_index, shop_order_list, df_full, selected_dates):
    if combined_df.empty:
        st.info("无数据可分析")
        return
    dim_options = ["车间", "病象", "成型机", "硫化机", "规格-花纹", "成型主手", "硫化主手"]
    selected_dim = st.radio("选择分析维度", dim_options, horizontal=True, key="dim_selector")
    dim_col = {
        "车间": "车间", "病象": "病象", "成型机": "成型", "硫化机": "硫化",
        "规格-花纹": "规格-花纹", "成型主手": "成型主手", "硫化主手": "硫化主手"
    }[selected_dim]

    grouped = combined_df.groupby([dim_col, "类型"]).size().reset_index(name="数量")
    pivot = grouped.pivot(index=dim_col, columns="类型", values="数量").fillna(0).reset_index()
    for col in ["废品", "次品外观"]:
        if col not in pivot.columns:
            pivot[col] = 0
    pivot["总数"] = pivot["废品"] + pivot["次品外观"]
    pivot = pivot.sort_values("总数", ascending=False)

    top12_values = []
    if len(pivot) > 12:
        top12 = pivot.head(12)
        other = pivot.iloc[12:].sum(numeric_only=True)
        other[dim_col] = "其他"
        pivot = pd.concat([top12, pd.DataFrame([other])], ignore_index=True)
        top12_values = top12[dim_col].tolist()
    else:
        top12_values = pivot[pivot[dim_col] != "其他"][dim_col].tolist()

    fig = px.bar(pivot, x=dim_col, y=["废品", "次品外观"], title=f"{selected_dim} 分布（废品/次品堆积）", barmode="stack", text_auto=True, color_discrete_map={"废品": "#ff7f0e", "次品外观": "#1f77b4"})
    fig.update_layout(height=550, template="plotly_white", clickmode="event+select")
    event = st.plotly_chart(fig, use_container_width=True, key=f"chart_{selected_dim}", on_select="rerun")

    st.markdown("**点击柱形图查看深入归因分析**")
    if event and event.selection and event.selection.points:
        clicked_value = event.selection.points[0]["x"]
        if clicked_value == "其他":
            drill_df = combined_df[~combined_df[dim_col].isin(top12_values)]
        else:
            drill_df = combined_df[combined_df[dim_col] == clicked_value]

        if not drill_df.empty:
            total = len(drill_df)
            cols = st.columns(5)
            for i, (label, col_name) in enumerate(zip(["主要病象","主要规格","成型主手","硫化主手"], ["病象","规格","成型主手","硫化主手"])):
                ser = drill_df[col_name].astype(str).replace("nan","").replace("None","")
                ser = ser[ser!=""]
                if not ser.empty:
                    top = ser.value_counts().index[0]
                    ratio = ser.value_counts().iloc[0]/total
                else:
                    top = "-"; ratio=0
                cols[i+1].metric(label, top, f"{ratio:.0%}")
            cols[0].metric("废次品总数", total)

            # TOP5图表
            row1 = st.columns(2)
            row2 = st.columns(2)
            with row1[0]:
                fig = _plot_top5(drill_df["病象"], "病象", "Blues")
                if fig: st.plotly_chart(fig, use_container_width=True)
            with row1[1]:
                fig = _plot_top5(drill_df["规格"], "规格", "Greens")
                if fig: st.plotly_chart(fig, use_container_width=True)
            with row2[0]:
                fig = _plot_top5(drill_df["成型主手"], "成型主手", "Oranges")
                if fig: st.plotly_chart(fig, use_container_width=True)
            with row2[1]:
                fig = _plot_top5(drill_df["硫化主手"], "硫化主手", "Purples")
                if fig: st.plotly_chart(fig, use_container_width=True)

            # 风险组合
            if "规格" in drill_df.columns and "病象" in drill_df.columns:
                combo = drill_df.groupby(["规格","病象"]).size().reset_index(name="数量").sort_values("数量", ascending=False).head(10)
                if not combo.empty:
                    st.dataframe(combo, use_container_width=True, height=400, hide_index=True)
                    top_combo = combo.iloc[0]
                    st.warning(f"🔴 最高风险组合：**【{top_combo['规格']}】 + 【{top_combo['病象']}】** 共 {top_combo['数量']} 条，占 {top_combo['数量']/total:.0%}")
        else:
            st.info("该维度无明细数据")
    else:
        st.info("请点击柱状图中的柱子查看深入归因分析")