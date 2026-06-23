# modules/personnel.py
import streamlit as st

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

    # 注入针对该表格的 CSS（只影响此表格）
    st.markdown("""
    <style>
    .merged-person-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 16px !important;   /* 控制字体大小 */
    }
    .merged-person-table th, .merged-person-table td {
        border: 1px solid #ddd !important;
        padding: 6px 4px !important;
        text-align: center !important;
        vertical-align: middle !important;
        font-size: 16px !important;   /* 确保单元格字体也生效 */
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
    }
    </style>
    """, unsafe_allow_html=True)

    html = f'<div class="scrollable-table" style="max-height: {max_height};">'
    html += '<table class="merged-person-table">'   # 使用新类
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