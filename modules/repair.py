import streamlit as st
import pandas as pd
import plotly.express as px
import io
from modules.charts import style_bar_chart
from modules.photo import trigger_image_popup

def _build_row(records, row_idx, code_span, name_span, mold_span, cure_span,
               current_code, current_name, current_mold, current_cure,
               i, j, k, m, show_molding, show_curing, show_defect_col,
               group_cols, headers, is_first_code, is_first_name, is_first_mold, is_first_cure):
    row = "<tr>"
    if is_first_code:
        row += f'<td rowspan="{code_span}" style="vertical-align:middle;text-align:center;">{current_code}</td>'
    if is_first_name:
        row += (
            f'<td rowspan="{name_span}" class="product-name" '
            f'style="vertical-align:middle;text-align:left;padding-left:12px;white-space:pre-line;">'
            f'{current_name}'
            f'</td>'
        )
    if show_molding and is_first_mold:
        row += f'<td rowspan="{mold_span}" class="machine" style="vertical-align:middle;text-align:center;">{current_mold}</td>'
    if show_curing and is_first_cure:
        row += f'<td rowspan="{cure_span}" class="machine" style="vertical-align:middle;text-align:center;">{current_cure}</td>'
    if show_defect_col:
        row += f'<td class="defect-name" style="text-align:center;">{records[row_idx]["返修缺陷"]}</td>'
    for col_idx in range(len(group_cols), len(headers)):
        col_name = headers[col_idx]
        val = records[row_idx][col_name]
        row += f'<td style="text-align:center;">{int(val) if not pd.isna(val) else 0}</td>'
    row += '</tr>'
    return row

def render_repair_table(raw_repair_df, selected_dates=None, photo_index=None):
    if raw_repair_df.empty:
        st.info("无返修数据")
        return

    # ---------- 1. 统计与柱状图 ----------
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

    # ---------- 2. 缺陷筛选 ----------
    defect_options = ["全部"] + defect_dist["返修缺陷"].tolist()
    selected_defect = st.selectbox("选择返修缺陷", defect_options, key="repair_defect_select")

    # ---------- 3. 列控制 ----------
    col_ctrl1, col_ctrl2 = st.columns(2)
    with col_ctrl1:
        show_molding = st.checkbox("显示成型机", value=False, key="repair_show_molding")
    with col_ctrl2:
        show_curing = st.checkbox("显示硫化机", value=False, key="repair_show_curing")

    df = raw_repair_df.copy()
    if selected_defect != "全部":
        df = df[df["返修缺陷"] == selected_defect]
        if df.empty:
            st.info(f"无缺陷为“{selected_defect}”的数据")
            return

    # ---------- 4. 动态 groupby ----------
    group_cols = ["胎胚编码", "成品名称"]
    if show_molding:
        group_cols.append("成型机")
    if show_curing:
        group_cols.append("硫化机")
    show_defect_col = (selected_defect == "全部")
    if show_defect_col:
        group_cols.append("返修缺陷")

    multi_date = selected_dates is not None and len(selected_dates) > 1

    if multi_date:
        pivot = df.groupby(group_cols + ["文件日期"]).size().unstack(fill_value=0)
        sorted_dates = sorted(selected_dates, key=lambda d: pd.to_datetime(d, format='%Y%m%d'))
        date_cols = [d for d in sorted_dates if d in pivot.columns]
        if not date_cols:
            date_cols = sorted(pivot.columns.tolist(), key=lambda d: pd.to_datetime(d, format='%Y%m%d'))
        pivot = pivot[date_cols]
        pivot.insert(0, "合计", pivot.sum(axis=1))
        rename_map = {d: pd.to_datetime(d, format='%Y%m%d').strftime('%m/%d') for d in date_cols}
        pivot.rename(columns=rename_map, inplace=True)
        flat = pivot.reset_index()
        data_columns = ["合计"] + list(rename_map.values())
        headers = group_cols + data_columns
        render_df = flat[headers].copy()
        sort_total_col = "合计"
    else:
        grouped = df.groupby(group_cols).size().reset_index(name="数量")
        headers = group_cols + ["数量"]
        render_df = grouped[headers].copy()
        sort_total_col = "数量"

    # ---------- 5. 排序 ----------
    code_total = render_df.groupby("胎胚编码")[sort_total_col].transform("sum")
    name_total = render_df.groupby(["胎胚编码", "成品名称"])[sort_total_col].transform("sum")

    if show_defect_col and "返修缺陷" in render_df.columns:
        defect_total = render_df.groupby(["胎胚编码", "成品名称", "返修缺陷"])[sort_total_col].transform("sum")
    else:
        defect_total = render_df[sort_total_col]

    render_df["code_total"] = code_total
    render_df["name_total"] = name_total
    render_df["defect_total"] = defect_total

    sort_cols = ["code_total", "name_total"]
    ascendings = [False, False]
    sort_cols += ["胎胚编码", "成品名称"]
    ascendings += [True, True]

    if show_defect_col:
        sort_cols += ["defect_total", "返修缺陷"]
        ascendings += [False, True]

    if show_molding:
        sort_cols.append("成型机")
        ascendings.append(True)
    if show_curing:
        sort_cols.append("硫化机")
        ascendings.append(True)

    render_df = render_df.sort_values(sort_cols, ascending=ascendings).reset_index(drop=True)
    render_df.drop(columns=["code_total", "name_total", "defect_total"], inplace=True)

    # ---------- 6. 计算列求和（合计行） ----------
    # 确定哪些列是数值列（需要求和）
    numeric_cols = []
    for col in render_df.columns:
        if col not in group_cols:
            # 检查该列是否为数值类型
            if pd.api.types.is_numeric_dtype(render_df[col]):
                numeric_cols.append(col)
    # 生成合计行
    total_row = {}
    for col in render_df.columns:
        if col in numeric_cols:
            total_row[col] = render_df[col].sum()
        else:
            total_row[col] = "合计"
    # 将合计行添加到 render_df 的末尾（仅用于导出，不在表格中重复渲染）
    render_df_with_total = pd.concat([render_df, pd.DataFrame([total_row])], ignore_index=True)

    # ---------- 7. 准备渲染 ----------
    records = render_df.to_dict("records")

    # ---------- 8. 生成 HTML（固定列宽） ----------
    html = '<div class="scrollable-table" style="max-height:600px;">'
    html += '<table class="merged-repair-table" style="width:100%;table-layout:fixed;">'
    html += '<thead><tr>'
    for h in headers:
        if h == "成品名称":
            html += f'<th style="width:300px;text-align:left;padding-left:12px;">{h}</th>'
        elif h == "胎胚编码":
            html += f'<th style="width:80px;text-align:center;">{h}</th>'
        else:
            html += f'<th style="text-align:center;">{h}</th>'
    html += '</tr></thead><tbody>'

    n = len(records)
    i = 0
    while i < n:
        current_code = records[i]["胎胚编码"]
        code_end = i
        while code_end < n and records[code_end]["胎胚编码"] == current_code:
            code_end += 1
        code_span = code_end - i

        j = i
        while j < code_end:
            current_name = records[j]["成品名称"]
            name_end = j
            while name_end < code_end and records[name_end]["成品名称"] == current_name:
                name_end += 1
            name_span = name_end - j

            if show_molding:
                k = j
                while k < name_end:
                    current_mold = records[k]["成型机"]
                    mold_end = k
                    while mold_end < name_end and records[mold_end]["成型机"] == current_mold:
                        mold_end += 1
                    mold_span = mold_end - k

                    if show_curing:
                        m = k
                        while m < mold_end:
                            current_cure = records[m]["硫化机"]
                            cure_end = m
                            while (cure_end < mold_end and
                                   records[cure_end]["硫化机"] == current_cure and
                                   (not show_defect_col or records[cure_end]["返修缺陷"] == records[m]["返修缺陷"])):
                                cure_end += 1
                            cure_span = cure_end - m

                            for row_idx in range(m, cure_end):
                                is_first_code = (row_idx == i)
                                is_first_name = (row_idx == j)
                                is_first_mold = (row_idx == k)
                                is_first_cure = (row_idx == m)
                                html += _build_row(records, row_idx, code_span, name_span, mold_span, cure_span,
                                                   current_code, current_name, current_mold, current_cure,
                                                   i, j, k, m, show_molding, show_curing, show_defect_col,
                                                   group_cols, headers, is_first_code, is_first_name, is_first_mold, is_first_cure)
                            m = cure_end
                    else:
                        for row_idx in range(k, mold_end):
                            is_first_code = (row_idx == i)
                            is_first_name = (row_idx == j)
                            is_first_mold = (row_idx == k)
                            html += _build_row(records, row_idx, code_span, name_span, mold_span, 1,
                                               current_code, current_name, current_mold, None,
                                               i, j, k, row_idx, show_molding, show_curing, show_defect_col,
                                               group_cols, headers, is_first_code, is_first_name, is_first_mold, True)
                    k = mold_end
            else:
                if show_curing:
                    j2 = j
                    while j2 < name_end:
                        current_cure = records[j2]["硫化机"]
                        cure_end2 = j2
                        while (cure_end2 < name_end and
                               records[cure_end2]["硫化机"] == current_cure and
                               (not show_defect_col or records[cure_end2]["返修缺陷"] == records[j2]["返修缺陷"])):
                            cure_end2 += 1
                        cure_span2 = cure_end2 - j2

                        for row_idx in range(j2, cure_end2):
                            is_first_code = (row_idx == i)
                            is_first_name = (row_idx == j)
                            is_first_cure = (row_idx == j2)
                            html += _build_row(records, row_idx, code_span, name_span, 1, cure_span2,
                                               current_code, current_name, None, current_cure,
                                               i, j, 0, j2, show_molding, show_curing, show_defect_col,
                                               group_cols, headers, is_first_code, is_first_name, True, is_first_cure)
                        j2 = cure_end2
                else:
                    for row_idx in range(j, name_end):
                        is_first_code = (row_idx == i)
                        is_first_name = (row_idx == j)
                        html += _build_row(records, row_idx, code_span, name_span, 1, 1,
                                           current_code, current_name, None, None,
                                           i, j, 0, 0, show_molding, show_curing, show_defect_col,
                                           group_cols, headers, is_first_code, is_first_name, True, True)
            j = name_end
        i = code_end

    # ---------- 9. 添加合计行（tfoot） ----------
    # 计算每一列的合计（仅数值列）
    total_row_dict = {}
    for col in headers:
        if col in numeric_cols:
            total_row_dict[col] = render_df[col].sum()
        else:
            total_row_dict[col] = "合计"
    # 构造合计行 HTML
    total_cells = []
    for col in headers:
        val = total_row_dict[col]
        if col == "成品名称":
            total_cells.append(f'<td style="text-align:left;padding-left:12px;font-weight:bold;">{val}</td>')
        else:
            total_cells.append(f'<td style="text-align:center;font-weight:bold;">{val if isinstance(val, str) else int(val)}</td>')
    html += '<tfoot><tr>' + ''.join(total_cells) + '</tr></tfoot>'

    html += '</tbody></table></div>'
    st.markdown(html, unsafe_allow_html=True)

    # ---------- 10. 下载按钮 ----------
    # 导出当前显示的数据（含合计行）
    def to_csv_with_total(df, total_row):
        # 复制数据，追加合计行
        export_df = df.copy()
        # 将合计行转为 DataFrame 并追加
        total_df = pd.DataFrame([total_row])
        export_df = pd.concat([export_df, total_df], ignore_index=True)
        # 转换为 CSV
        csv = export_df.to_csv(index=False, encoding='utf-8-sig')
        return csv

    csv_data = to_csv_with_total(render_df, total_row_dict)
    st.download_button(
        label="📥 下载表格 (CSV)",
        data=csv_data,
        file_name="返修数据.csv",
        mime="text/csv",
        use_container_width=True,
        key="repair_download_csv"
    )

    # ---------- 11. 图片查询 ----------
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