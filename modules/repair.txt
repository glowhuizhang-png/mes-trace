import streamlit as st
import pandas as pd
import plotly.express as px
from modules.charts import style_bar_chart
from modules.photo import trigger_image_popup

def render_repair_table(raw_repair_df, selected_dates=None, photo_index=None):
    """
    完全自包含的返修分析模块：
    - 显示返修总数、柱状图
    - 下拉框选择缺陷
    - 输入框+按钮查看图片
    - 合并表格（按日期或单日）
    """
    if raw_repair_df.empty:
        st.info("无返修数据")
        return

    # ---------- 1. 统计与柱状图（放在最前） ----------
    total_repair = len(raw_repair_df)
    defect_dist = raw_repair_df["返修缺陷"].value_counts().reset_index()
    defect_dist.columns = ["返修缺陷", "数量"]

    st.metric("📦 返修总数量", f"{total_repair} 条")

    fig_repair = px.bar(
        defect_dist,
        x="返修缺陷",
        y="数量",
        text="数量",
        title="返修缺陷分布"
    )
    fig_repair = style_bar_chart(fig_repair, "返修缺陷分布")
    fig_repair.update_traces(textposition='outside')
    st.plotly_chart(fig_repair, use_container_width=True, key="repair_dist_chart")

    st.divider()

    # ---------- 2. 缺陷筛选下拉框（放在柱状图下方） ----------
    defect_options = ["全部"] + defect_dist["返修缺陷"].tolist()
    selected_defect = st.selectbox("选择返修缺陷", defect_options, key="repair_defect_select")

    # 根据筛选过滤数据
    df = raw_repair_df.copy()
    if selected_defect != "全部":
        df = df[df["返修缺陷"] == selected_defect]
        if df.empty:
            st.info(f"无缺陷为“{selected_defect}”的数据")
            return

    # ---------- 3. 多日期合并表格 ----------
    multi_date = selected_dates is not None and len(selected_dates) > 1

    if multi_date:
        pivot = df.groupby(["胎胚编码", "成品名称", "成型机", "硫化机", "返修缺陷", "文件日期"]).size().unstack(fill_value=0)
        sorted_dates = sorted(selected_dates)
        date_cols = [d for d in sorted_dates if d in pivot.columns]
        if not date_cols:
            date_cols = sorted(pivot.columns.tolist())
        pivot = pivot[date_cols]
        pivot.insert(0, "合计", pivot.sum(axis=1))
        rename_map = {d: pd.to_datetime(d, format='%Y%m%d').strftime('%m/%d') for d in date_cols}
        pivot.rename(columns=rename_map, inplace=True)
        flat = pivot.reset_index()
        flat = flat.sort_values("合计", ascending=False)
        data_columns = ["合计"] + list(rename_map.values())
        headers = ["胎胚编码", "成品名称", "成型机", "硫化机", "返修缺陷"] + data_columns
        fixed_widths = [10, 46, 9, 9, 16]
        fixed_total = sum(fixed_widths)
        remaining = 100 - fixed_total
        num_date_cols = len(data_columns)
        date_width = remaining / num_date_cols if num_date_cols > 0 else remaining
        col_widths = fixed_widths + [date_width] * num_date_cols
        render_df = flat
    else:
        grouped = df.groupby(["胎胚编码", "成品名称", "成型机", "硫化机", "返修缺陷"]).size().reset_index(name="数量")
        grouped = grouped.sort_values("数量", ascending=False)
        headers = ["胎胚编码", "成品名称", "成型机", "硫化机", "返修缺陷", "数量"]
        col_widths = [10, 46, 9, 9, 16, 10]
        render_df = grouped

    # ---------- 4. 渲染合并表格 ----------
    html = '<div class="scrollable-table" style="max-height: 600px;">'
    html += '<table class="merged-repair-table" style="width:100%">'
    html += '<thead><tr>'
    for i, h in enumerate(headers):
        html += f'<th style="width:{col_widths[i]}%">{h}</th>'
    html += '</tr></thead><tbody>'

    n = len(render_df)
    i = 0
    while i < n:
        current_code = render_df.iloc[i]["胎胚编码"]
        code_end = i
        while code_end < n and render_df.iloc[code_end]["胎胚编码"] == current_code:
            code_end += 1
        code_span = code_end - i

        j = i
        while j < code_end:
            current_name = render_df.iloc[j]["成品名称"]
            name_end = j
            while name_end < code_end and render_df.iloc[name_end]["成品名称"] == current_name:
                name_end += 1
            name_span = name_end - j

            k = j
            while k < name_end:
                current_machine = render_df.iloc[k]["成型机"]
                machine_end = k
                while machine_end < name_end and render_df.iloc[machine_end]["成型机"] == current_machine:
                    machine_end += 1
                machine_span = machine_end - k

                for m in range(k, machine_end):
                    row = "<tr>"
                    if m == i:
                        row += f'<td rowspan="{code_span}" style="vertical-align: middle; width:{col_widths[0]}%">{current_code}</td>'
                    if m == j:
                        row += f'<td rowspan="{name_span}" style="vertical-align: middle; width:{col_widths[1]}%">{current_name}</td>'
                    if m == k:
                        row += f'<td rowspan="{machine_span}" style="vertical-align: middle; width:{col_widths[2]}%">{current_machine}</td>'
                    row += f'<td style="width:{col_widths[3]}%">{render_df.iloc[m]["硫化机"]}</td>'
                    row += f'<td style="width:{col_widths[4]}%">{render_df.iloc[m]["返修缺陷"]}</td>'
                    for col_idx in range(5, len(headers)):
                        col_name = headers[col_idx]
                        val = render_df.iloc[m][col_name]
                        row += f'<td style="width:{col_widths[col_idx]}%">{int(val) if not pd.isna(val) else 0}</td>'
                    row += '</tr>'
                    html += row
                k = machine_end
            j = name_end
        i = code_end

    html += '</tbody></table></div>'
    st.markdown(html, unsafe_allow_html=True)

    # ---------- 5. 图片查询放在最后 ----------
    st.divider()
    col_input, col_btn = st.columns([4, 1])
    with col_input:
        repair_barcode = st.text_input("输入胎胚编码查看图片", key="repair_barcode_input")
    with col_btn:
        if st.button("查看图片", key="repair_view_btn"):
            if repair_barcode.strip() and photo_index is not None:
                trigger_image_popup(repair_barcode.strip(), photo_index)
            elif repair_barcode.strip() and photo_index is None:
                st.warning("图片索引未初始化，无法查看图片")
            else:
                st.warning("请输入胎胚编码")