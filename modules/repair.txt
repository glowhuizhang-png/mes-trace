import streamlit as st
import pandas as pd

def render_repair_table(raw_repair_df, defect_filter="全部", selected_dates=None):
    if raw_repair_df.empty:
        st.info("无返修数据")
        return

    df = raw_repair_df.copy()
    if defect_filter != "全部":
        df = df[df["返修缺陷"] == defect_filter]
        if df.empty:
            st.info(f"无缺陷为“{defect_filter}”的数据")
            return

    multi_date = selected_dates is not None and len(selected_dates) > 1

    if multi_date:
        # 日期递增排序
        sorted_dates = sorted(selected_dates, key=lambda x: pd.to_datetime(x, format='%Y%m%d'))
        pivot = df.groupby(["胎胚编码", "成品名称", "成型机", "硫化机", "返修缺陷", "文件日期"]).size().unstack(fill_value=0)
        date_cols = [d for d in sorted_dates if d in pivot.columns]
        pivot = pivot[date_cols]
        pivot.insert(0, "合计", pivot.sum(axis=1))
        rename_map = {d: pd.to_datetime(d, format='%Y%m%d').strftime('%m/%d') for d in date_cols}
        pivot.rename(columns=rename_map, inplace=True)
        flat = pivot.reset_index()

        # 按胎胚总合计降序排序
        total_per_code = flat.groupby("胎胚编码")["合计"].sum().reset_index(name="总合计")
        flat = flat.merge(total_per_code, on="胎胚编码", how="left")
        flat = flat.sort_values(["总合计", "胎胚编码", "成品名称", "成型机"], ascending=[False, True, True, True])
        flat = flat.drop(columns=["总合计"])

        # 强制日期列递增
        date_columns = [col for col in flat.columns if col not in ["胎胚编码", "成品名称", "成型机", "硫化机", "返修缺陷", "合计"]]
        sorted_date_cols = sorted(date_columns, key=lambda x: pd.to_datetime(x, format='%m/%d'))
        ordered_columns = ["胎胚编码", "成品名称", "成型机", "硫化机", "返修缺陷", "合计"] + sorted_date_cols
        flat = flat[ordered_columns]

        headers = ordered_columns
        fixed_widths = [10, 46, 9, 9, 16]
        num_date = len(sorted_date_cols) + 1
        total_fixed = sum(fixed_widths)
        remaining = 100 - total_fixed
        date_width = remaining / num_date if num_date > 0 else remaining
        col_widths = fixed_widths + [date_width] * num_date
        render_df = flat
    else:
        grouped = df.groupby(["胎胚编码", "成品名称", "成型机", "硫化机", "返修缺陷"]).size().reset_index(name="数量")
        total_per_code = grouped.groupby("胎胚编码")["数量"].sum().reset_index(name="总数量")
        grouped = grouped.merge(total_per_code, on="胎胚编码", how="left")
        grouped = grouped.sort_values(["总数量", "胎胚编码", "成品名称", "成型机"], ascending=[False, True, True, True])
        grouped = grouped.drop(columns=["总数量"])
        headers = ["胎胚编码", "成品名称", "成型机", "硫化机", "返修缺陷", "数量"]
        col_widths = [10, 46, 9, 9, 16, 10]
        render_df = grouped

    # 生成 HTML 表格（表头固定）
    html = '<div style="max-height: 600px; overflow-y: auto; border: 1px solid #ddd; border-radius: 8px;">'
    html += '<style>table, th, td { background-color: white !important; color: black !important; }</style>'  # 新增
    html += '<table style="width:100%; border-collapse: collapse; text-align: center;">'
    # 表头：添加 sticky 样式
    html += '<thead>'
    html += '<tr style="background-color: #f0f2f6;">'
    for i, h in enumerate(headers):
        html += f'<th style="width:{col_widths[i]}%; font-size: 13px; padding: 8px 4px; border: 1px solid #ddd; position: sticky; top: 0; background-color: #f0f2f6; z-index: 10;">{h}</th>'
    html += '</tr></thead><tbody>'

    n = len(render_df)
    i = 0
    while i < n:
        code = render_df.iloc[i]["胎胚编码"]
        j_code = i
        while j_code < n and render_df.iloc[j_code]["胎胚编码"] == code:
            j_code += 1
        code_span = j_code - i

        row_idx = i
        while row_idx < j_code:
            prod = render_df.iloc[row_idx]["成品名称"]
            j_prod = row_idx
            while j_prod < j_code and render_df.iloc[j_prod]["成品名称"] == prod:
                j_prod += 1
            prod_span = j_prod - row_idx

            row_idx2 = row_idx
            while row_idx2 < j_prod:
                machine = render_df.iloc[row_idx2]["成型机"]
                j_machine = row_idx2
                while j_machine < j_prod and render_df.iloc[j_machine]["成型机"] == machine:
                    j_machine += 1
                machine_span = j_machine - row_idx2

                for m in range(row_idx2, j_machine):
                    row = '<tr>'
                    if m == i:
                        row += f'<td rowspan="{code_span}" style="font-size: 13px; padding: 6px 3px; border: 1px solid #ddd; vertical-align: middle;">{code}</td>'
                    if m == row_idx:
                        row += f'<td rowspan="{prod_span}" style="font-size: 13px; padding: 6px 3px; border: 1px solid #ddd; vertical-align: middle;">{prod}</td>'
                    if m == row_idx2:
                        row += f'<td rowspan="{machine_span}" style="font-size: 13px; padding: 6px 3px; border: 1px solid #ddd; vertical-align: middle;">{machine}</td>'
                    row += f'<td style="font-size: 13px; padding: 6px 3px; border: 1px solid #ddd;">{render_df.iloc[m]["硫化机"]}</td>'
                    row += f'<td style="font-size: 13px; padding: 6px 3px; border: 1px solid #ddd;">{render_df.iloc[m]["返修缺陷"]}</td>'
                    for col_idx in range(5, len(headers)):
                        col_name = headers[col_idx]
                        val = render_df.iloc[m][col_name]
                        if pd.isna(val):
                            val = 0
                        if isinstance(val, (int, float)):
                            val = int(val) if val == int(val) else val
                        row += f'<td style="font-size: 13px; padding: 6px 3px; border: 1px solid #ddd;">{val}</td>'
                    row += '</tr>'
                    html += row
                row_idx2 = j_machine
            row_idx = j_prod
        i = j_code

    html += '</tbody></table></div>'
    st.markdown(html, unsafe_allow_html=True)