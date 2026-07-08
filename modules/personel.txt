import streamlit as st
import pandas as pd
import plotly.express as px

# ========== 成型部门主手综合排行（废品+外观次品总数降序 TOP10） ==========
def render_master_ranking(df, key_prefix="master_rank"):
    if df.empty or "成型主手" not in df.columns:
        st.info("无成型主手数据")
        return

    df = df.dropna(subset=["成型主手"])
    df = df[df["成型主手"].astype(str).str.strip() != ""]

    # 降序排列，取前10
    counts = df["成型主手"].value_counts().head(10).reset_index()
    counts.columns = ["成型主手", "数量"]

    fig = px.bar(counts, x="成型主手", y="数量", text="数量",
                 title="成型部门主手综合排行（降序）",
                 color="数量", color_continuous_scale="Blues")
    fig.update_traces(
        textposition="outside",
        textfont=dict(size=16, color="black", family="Microsoft YaHei"),
        cliponaxis=False
    )
    fig.update_layout(
        clickmode="event+select",
        height=300,
        template="plotly_white",
        margin=dict(l=10, r=10, t=40, b=10),
        xaxis=dict(title=None, tickfont=dict(size=14, color="black")),
        yaxis=dict(title=None, tickfont=dict(size=14, color="black")),
        coloraxis_showscale=False
    )

    chart_key = f"{key_prefix}_chart"
    event = st.plotly_chart(fig, use_container_width=True,
                            on_select="rerun", key=chart_key)

    # 处理点击：设置一次性标记
    if event and event.selection and event.selection.points:
        clicked = event.selection.points[0]["x"]
        last = st.session_state.get(f"{key_prefix}_last")
        if clicked != last:
            st.session_state[f"{key_prefix}_last"] = clicked
            st.session_state[f"{key_prefix}_selected"] = clicked
            st.session_state[f"{key_prefix}_pending"] = True   # 一次性标记
            st.rerun()

    # 弹窗逻辑：仅当本次有点击触发时才显示
    pending_key = f"{key_prefix}_pending"
    if st.session_state.get(pending_key):
        # 立即清除标记，防止后续渲染再次触发
        st.session_state[pending_key] = False
        selected = st.session_state[f"{key_prefix}_selected"]
        detail_df = df[df["成型主手"] == selected]

        @st.dialog(f"📋 {selected} 的明细", width="large")
        def show_dialog():
            st.subheader(f"成型主手：{selected}")
            display_cols = [
                "病象", "条码", "硫化", "硫化主手", "硫化日期",
                "成型", "成型时间", "成型主手", "规格", "花纹", "位置", "车间"
            ]
            available = [c for c in display_cols if c in detail_df.columns]
            st.dataframe(detail_df[available], use_container_width=True, height=500)
            if st.button("关闭", key=f"{key_prefix}_close"):
                # 清理所有相关状态
                for k in [f"{key_prefix}_selected", f"{key_prefix}_last", pending_key]:
                    if k in st.session_state:
                        del st.session_state[k]
                st.rerun()
        show_dialog()


# ========== 以下原有函数保持不变 ==========
def render_merged_person_table(person_df, person_col, type_col="类型", cause_col="病象", count_col="数量", total_col="合计", max_height="600px", extra_col=None):
    if person_df.empty:
        return ""

    if extra_col and extra_col in person_df.columns:
        col_order = [person_col, extra_col, type_col, cause_col, count_col, total_col]
    else:
        col_order = [person_col, type_col, cause_col, count_col, total_col]

    for c in col_order:
        if c not in person_df.columns:
            raise ValueError(f"缺少列: {c}")

    st.markdown("""
    <style>
    .merged-person-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 16px !important;
    }
    .merged-person-table th, .merged-person-table td {
        border: 1px solid #ddd !important;
        padding: 10px 8px !important;
        text-align: center !important;
        vertical-align: middle !important;
        font-size: 16px !important;
        font-weight: 500 !important;
    }
    .merged-person-table th {
        background-color: #f0f2f6 !important;
        font-weight: 600 !important;
        position: sticky;
        top: 0;
        z-index: 10;
    }
    .scrollable-table {
        max-height: 600px;
        overflow-y: auto;
        border: 1px solid #ccc;
        border-radius: 8px;
    }
    .person-checkbox-row {
        margin-top: -10px !important;
        margin-bottom: 6px !important;
    }
    </style>
    """, unsafe_allow_html=True)

    html = f'<div class="scrollable-table" style="max-height: {max_height};">'
    html += '<table class="merged-person-table">'
    header = '<tr>' + ''.join([f'<th>{c}</th>' for c in col_order]) + '</tr>'
    html += f'<thead>{header}</thead><tbody>'

    n = len(person_df)
    i = 0
    while i < n:
        current_person = person_df.iloc[i][person_col]
        person_end = i
        while person_end < n and person_df.iloc[person_end][person_col] == current_person:
            person_end += 1
        person_span = person_end - i

        j = i
        while j < person_end:
            current_type = person_df.iloc[j][type_col]
            type_end = j
            while type_end < person_end and person_df.iloc[type_end][type_col] == current_type:
                type_end += 1
            type_span = type_end - j

            for k in range(j, type_end):
                row = "<tr>"
                if k == i:
                    row += f'<td rowspan="{person_span}" style="vertical-align: middle;">{current_person}</td>'
                if extra_col and extra_col in person_df.columns:
                    row += f'<td>{person_df.iloc[k][extra_col]}</td>'
                if k == j:
                    row += f'<td rowspan="{type_span}" style="vertical-align: middle;">{current_type}</td>'
                row += f'<td>{person_df.iloc[k][cause_col]}</td>'
                row += f'<td>{person_df.iloc[k][count_col]}</td>'
                if k == i:
                    row += f'<td rowspan="{person_span}" style="vertical-align: middle;">{person_df.iloc[k][total_col]}</td>'
                row += '</tr>'
                html += row
            j = type_end
        i = person_end

    html += '</tbody></table></div>'
    return html


def render_molding_analysis(df):
    st.markdown("**成型人员分析**")
    with st.container():
        show_molding_machine = st.checkbox("显示成型机台", value=True, key="molding_machine")

    condition = ((df["车间"] == "成型") | (df["类型"] == "次品UF")) & (df["类型"] != "返修")
    molding_data = df[condition]

    if not molding_data.empty:
        if show_molding_machine:
            person_detail = molding_data.groupby(["成型主手", "成型", "类型", "病象"]).size().reset_index(name="数量")
            extra = "成型"
        else:
            person_detail = molding_data.groupby(["成型主手", "类型", "病象"]).size().reset_index(name="数量")
            extra = None
        person_detail["合计"] = person_detail.groupby("成型主手")["数量"].transform("sum")
        person_detail = person_detail.sort_values(
            ["合计", "成型主手", "类型", "病象"],
            ascending=[False, True, True, True]
        )
        html = render_merged_person_table(person_detail, "成型主手", extra_col=extra, max_height="600px")
        if html:
            st.markdown(html, unsafe_allow_html=True)
    else:
        st.info("无成型及UF数据")


def render_vulcanization_analysis(df):
    st.markdown("**硫化人员分析**")

    col1, col2 = st.columns(2)
    with col1:
        show_vul_machine = st.checkbox("显示硫化机台", value=True, key="vul_machine")
    with col2:
        hide_side_glue = st.checkbox("不显示胎侧缺胶", value=True, key="hide_side_glue")

    vul_data = df[(df["车间"] == "硫化") & (df["类型"].isin(["废品", "次品外观"]))]
    if hide_side_glue:
        vul_data = vul_data[vul_data["病象"] != "胎侧缺胶"]

    if not vul_data.empty:
        if show_vul_machine:
            person_detail = vul_data.groupby(["硫化主手", "硫化", "类型", "病象"]).size().reset_index(name="数量")
            extra = "硫化"
        else:
            person_detail = vul_data.groupby(["硫化主手", "类型", "病象"]).size().reset_index(name="数量")
            extra = None

        person_detail["合计"] = person_detail.groupby("硫化主手")["数量"].transform("sum")
        person_detail = person_detail.sort_values(
            ["合计", "硫化主手", "类型", "病象"],
            ascending=[False, True, True, True]
        )
        html = render_merged_person_table(person_detail, "硫化主手", extra_col=extra, max_height="600px")
        if html:
            st.markdown(html, unsafe_allow_html=True)
    else:
        st.info("无硫化数据（废品/次品外观）")