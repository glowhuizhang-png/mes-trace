import streamlit as st
import pandas as pd
import plotly.express as px
import io
import datetime

# ========== 成型部门主手综合排行（废品+外观次品总数降序 TOP10） ==========
def render_master_ranking(df, key_prefix="master_rank"):
    if df.empty or "成型主手" not in df.columns:
        st.info("无成型主手数据")
        return

    df = df.dropna(subset=["成型主手"])
    df = df[df["成型主手"].astype(str).str.strip() != ""]

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

    if event and event.selection and event.selection.points:
        clicked = event.selection.points[0]["x"]
        last = st.session_state.get(f"{key_prefix}_last")
        if clicked != last:
            st.session_state[f"{key_prefix}_last"] = clicked
            st.session_state[f"{key_prefix}_selected"] = clicked
            st.session_state[f"{key_prefix}_pending"] = True
            st.rerun()

    pending_key = f"{key_prefix}_pending"
    if st.session_state.get(pending_key):
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
                for k in [f"{key_prefix}_selected", f"{key_prefix}_last", pending_key]:
                    if k in st.session_state:
                        del st.session_state[k]
                st.rerun()
        show_dialog()


# ========== 核心功能：导出并美化 Excel ==========
def export_to_excel(df, person_col, type_col="类型", cause_col="病象", count_col="数量", total_col="合计", extra_col=None):
    """
    将 DataFrame 导出为美化后的 Excel 文件（支持合并单元格、边框、居中、自适应列宽等）
    """
    output = io.BytesIO()
    
    # 确定列顺序
    col_order = [person_col]
    if extra_col and extra_col in df.columns:
        col_order.append(extra_col)
    col_order.extend([type_col, cause_col, count_col, total_col])
    col_order = [c for c in col_order if c in df.columns] # 过滤不存在的列
    
    df_export = df[col_order].copy()
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_export.to_excel(writer, sheet_name='人员分析', index=False, startrow=0)
        workbook = writer.book
        worksheet = writer.sheets['人员分析']
        
        # 定义格式样式
        header_format = workbook.add_format({
            'bold': True, 'bg_color': '#f0f2f6', 'border': 1,
            'align': 'center', 'valign': 'vcenter',
            'font_name': 'Microsoft YaHei', 'font_size': 11
        })
        cell_format = workbook.add_format({
            'border': 1, 'align': 'center', 'valign': 'vcenter',
            'font_name': 'Microsoft YaHei', 'font_size': 11
        })
        merged_cell_format = workbook.add_format({
            'border': 1, 'align': 'center', 'valign': 'vcenter',
            'font_name': 'Microsoft YaHei', 'font_size': 11,
            'bg_color': '#ffffff'
        })
        
        # 设置列宽
        worksheet.set_column(0, len(col_order)-1, 15)
        for idx, col in enumerate(col_order):
            if col == cause_col: 
                worksheet.set_column(idx, idx, 30) # 病象列宽一些
            elif col in [person_col, extra_col, type_col]: 
                worksheet.set_column(idx, idx, 12)
            else: 
                worksheet.set_column(idx, idx, 10)
                
        # 写入表头（带样式）
        for col_num, value in enumerate(df_export.columns.values):
            worksheet.write(0, col_num, value, header_format)
            
        # 冻结首行
        worksheet.freeze_panes(1, 0)
        
        # 合并单元格逻辑
        n = len(df_export)
        i = 0
        row_idx = 1 # Excel 数据从第 1 行开始（0 是表头）
        
        while i < n:
            current_person = df_export.iloc[i][person_col]
            person_end = i
            while person_end < n and df_export.iloc[person_end][person_col] == current_person:
                person_end += 1
            person_span = person_end - i
            
            # 合并人员列
            if person_span > 1:
                worksheet.merge_range(row_idx, 0, row_idx + person_span - 1, 0, current_person, merged_cell_format)
            else:
                worksheet.write(row_idx, 0, current_person, cell_format)
                
            # 合并合计列
            total_col_idx = len(col_order) - 1
            total_val = df_export.iloc[i][total_col]
            if person_span > 1:
                worksheet.merge_range(row_idx, total_col_idx, row_idx + person_span - 1, total_col_idx, total_val, merged_cell_format)
            else:
                worksheet.write(row_idx, total_col_idx, total_val, cell_format)
            
            j = i
            while j < person_end:
                current_type = df_export.iloc[j][type_col]
                type_end = j
                while type_end < person_end and df_export.iloc[type_end][type_col] == current_type:
                    type_end += 1
                type_span = type_end - j
                
                type_col_idx = col_order.index(type_col)
                
                # 合并类型列
                if type_span > 1:
                    worksheet.merge_range(row_idx + (j - i), type_col_idx, row_idx + (j - i) + type_span - 1, type_col_idx, current_type, merged_cell_format)
                
                for k in range(j, type_end):
                    current_row_idx = row_idx + (k - i)
                    for col_idx, col_name in enumerate(col_order):
                        # 跳过已经合并的列
                        if col_name in [person_col, total_col]:
                            continue
                        if col_name == type_col and type_span > 1:
                            continue
                        
                        val = df_export.iloc[k][col_name]
                        worksheet.write(current_row_idx, col_idx, val, cell_format)
                        
                j = type_end
            i = person_end
            
        # 添加自动筛选
        worksheet.autofilter(0, 0, n, len(col_order)-1)
        
    output.seek(0)
    return output.getvalue()


# ========== 表格渲染函数（已取消滑动查看） ==========
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
        border: 1px solid #ccc;
        border-radius: 8px;
    }
    .person-checkbox-row {
        margin-top: -10px !important;
        margin-bottom: 6px !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # 取消高度限制，直接全部显示
    html = f'<div class="scrollable-table" style="max-height: none; overflow-y: visible;">'
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
        
        # 渲染 HTML 表格（取消滑动查看）
        html = render_merged_person_table(person_detail, "成型主手", extra_col=extra, max_height="none")
        if html:
            st.markdown(html, unsafe_allow_html=True)
            
        # 一键导出功能
        st.markdown("---")
        excel_data = export_to_excel(person_detail, "成型主手", extra_col=extra)
        st.download_button(
            label="📥 导出成型人员分析（Excel）",
            data=excel_data,
            file_name=f"成型人员分析_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="export_molding_btn"
        )
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
        
        # 渲染 HTML 表格（取消滑动查看）
        html = render_merged_person_table(person_detail, "硫化主手", extra_col=extra, max_height="none")
        if html:
            st.markdown(html, unsafe_allow_html=True)
            
        # 一键导出功能
        st.markdown("---")
        excel_data = export_to_excel(person_detail, "硫化主手", extra_col=extra)
        st.download_button(
            label="📥 导出硫化人员分析（Excel）",
            data=excel_data,
            file_name=f"硫化人员分析_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="export_vulcanization_btn"
        )
    else:
        st.info("无硫化数据（废品/次品外观）")