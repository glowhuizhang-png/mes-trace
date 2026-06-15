# modules/uf.py
import streamlit as st
import pandas as pd
import plotly.express as px

UF_COLUMNS = [
    "CWRFVOA_kgf", "CWRFVOA1H_kgf", "CWLFVOA_kgf",
    "CCWRFVOA_kgf", "CCWRFVOA1H_kgf", "CCWLFVOA_kgf",
    "CON_kgf", "Upper_g", "Lower_g"
]

UF_HEADER_MAP = {
    "CWRFVOA_kgf": "RVF",
    "CWRFVOA1H_kgf": "R1H",
    "CWLFVOA_kgf": "LFV",
    "CCWRFVOA_kgf": "RFV(ccw)",
    "CCWRFVOA1H_kgf": "R1H(ccw)",
    "CCWLFVOA_kgf": "LFV(ccw)",
    "CON_kgf": "CON",
    "Upper_g": "UPP",
    "Lower_g": "LOW"
}

def render_uf_detail_table(df, uf_check_df, key_prefix, height=680):
    """完全自包含：绘制柱状图 + 明细表，点击柱状图自动筛选"""
    # 合并UF检查数据
    if uf_check_df is not None and not uf_check_df.empty:
        df["条码"] = df["条码"].astype(str).str.strip()
        uf_check_df["条码"] = uf_check_df["条码"].astype(str).str.strip()
        merged = df.merge(uf_check_df, on="条码", how="left")
    else:
        merged = df.copy()
        for c in UF_COLUMNS:
            merged[c] = None

    if merged.empty:
        st.info("无UF次品数据")
        return

    for col in ["成型机台", "规格", "花纹"]:
        if col in merged.columns:
            merged[col] = merged[col].fillna("").astype(str).str.strip()

    # 柱状图数据
    machine_counts = merged["成型机台"].value_counts().reset_index()
    machine_counts.columns = ["成型机", "数量"]

    st.markdown(
        """
        <style>
        .uf-header-card {
            background:white;
            border-radius:18px;
            padding:18px 20px;
            box-shadow:0 8px 20px rgba(15,23,42,.06);
            margin-top:18px;
            margin-bottom:10px;
        }
        .uf-header-label {
            font-size:14px;
            color:#334155;
            font-weight:600;
            margin-bottom:4px;
        }
        .uf-filter-row .stSelectbox, .uf-filter-row .stMultiselect {
            background:white !important;
            border-radius:14px !important;
            border:1px solid #e2e8f0 !important;
            padding:0 8px !important;
            box-shadow:none !important;
        }
        .uf-chart-card {
            background:white;
            border-radius:18px;
            padding:10px;
            box-shadow:0 8px 20px rgba(15,23,42,.06);
            margin-top:0;
            margin-bottom:0;
        }
        section[data-testid="stPlotlyChart"], div[data-testid="stPlotlyChart"] {
            background:white !important;
            border-radius:18px !important;
            padding:10px !important;
            box-shadow:none !important;
            margin-top:0 !important;
            margin-bottom:0 !important;
        }
        section[data-testid="stDataFrame"], div[data-testid="stDataFrame"] {
            background:white !important;
            border-radius:18px !important;
            padding:12px !important;
            box-shadow:0 8px 20px rgba(15,23,42,.06) !important;
            margin-top:0 !important;
            margin-bottom:18px !important;
        }
        /* 图表与表格占据页面最大宽度 */
        section[data-testid="stPlotlyChart"], div[data-testid="stPlotlyChart"],
        section[data-testid="stDataFrame"], div[data-testid="stDataFrame"] {
            max-width:100% !important;
            width:100% !important;
            margin-left:0 !important;
            margin-right:0 !important;
            padding-left:0 !important;
            padding-right:0 !important;
        }
        /* 保持表格内数值居中，保留 Streamlit 内置浮动工具 */
        section[data-testid="stDataFrame"] td,
        section[data-testid="stDataFrame"] th {
            text-align:center !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    # (已移除清除按钮) 点击柱形图即可筛选，下方不再显示额外按钮

    # 绘制柱状图（仅作为筛选触发器），不再显示下拉筛选
    fig = px.bar(machine_counts, x="成型机", y="数量", text="数量", text_auto=True)
    fig.update_traces(marker_color='steelblue', marker_line_color='white', marker_line_width=1, textfont=dict(size=18, color='black'))
    fig.update_layout(
        clickmode='event+select',
        height=260,
        margin=dict(t=10, b=10, l=10, r=10),
        yaxis=dict(title=""),
        xaxis=dict(title="")
    )

    plotly_event = st.plotly_chart(
        fig,
        use_container_width=True,
        key=f"uf_bar_{key_prefix}",
        on_select="rerun",
        selection_mode="points"
    )

    # 处理图表点击：将点击的机台写入 session_state
    selected_machine = None
    if plotly_event and plotly_event.selection:
        points = plotly_event.selection.points
        if points and len(points) > 0:
            if isinstance(points[0], dict):
                selected_machine = points[0].get('x')
            else:
                selected_machine = getattr(points[0], 'x', None)

    # 根据图表点击过滤；未选择时展示所有机台数据
    if selected_machine:
        filtered = merged[merged["成型机台"] == selected_machine].copy()
    else:
        filtered = merged.copy()

    if filtered.empty:
        st.warning("无符合条件的数据")
        return

    base_cols = ["条码", "成型机台", "硫化机台", "成型时间", "成型主手", "规格", "花纹"]
    base_cols = [c for c in base_cols if c in filtered.columns]
    show_cols = base_cols + UF_COLUMNS
    filtered_display = filtered[show_cols].rename(columns=UF_HEADER_MAP)
    st.dataframe(filtered_display, width='stretch', height=height, hide_index=True)