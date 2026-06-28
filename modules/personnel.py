import streamlit as st
import pandas as pd

def render_merged_person_table(person_df, person_col, type_col="类型", cause_col="病象", count_col="数量", total_col="合计", max_height="600px", extra_col=None):
    """
    渲染合并的人员统计表，自动合并人员、类型行，并添加针对该表格的样式。
    """
    if person_df.empty:
        return ""

    if extra_col and extra_col in person_df.columns:
        col_order = [person_col, extra_col, type_col, cause_col, count_col, total_col]
    else:
        col_order = [person_col, type_col, cause_col, count_col, total_col]

    for c in col_order:
        if c not in person_df.columns:
            raise ValueError(f"缺少列: {c}")

    # 注入针对该表格的 CSS（行高增大，但标题复选框间距缩小在外部控制）
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
    /* 缩小复选框与标题之间的间距 */
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


# ========== 成型人员分析 ==========
def render_molding_analysis(df):
    """
    渲染成型人员分析（含显示成型机台复选框）
    """
    st.markdown("**成型人员分析**")
    # 使用容器减小复选框上方间距
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


# ========== 硫化人员分析 ==========
def render_vulcanization_analysis(df):
    """
    渲染硫化人员分析
    - 显示硫化机台（复选框）
    - 不显示胎侧缺胶（默认勾选）
    """
    st.markdown("**硫化人员分析**")

    # 两个复选框并排
    col1, col2 = st.columns(2)
    with col1:
        show_vul_machine = st.checkbox("显示硫化机台", value=True, key="vul_machine")
    with col2:
        # 改为“不显示胎侧缺胶”，默认勾选
        hide_side_glue = st.checkbox("不显示胎侧缺胶", value=True, key="hide_side_glue")

    # 基础数据：硫化车间的废品和外观次品
    vul_data = df[(df["车间"] == "硫化") & (df["类型"].isin(["废品", "次品外观"]))]

    # 如果勾选了“不显示胎侧缺胶”，则排除该病象
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