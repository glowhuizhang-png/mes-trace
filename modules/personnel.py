# -*- coding: utf-8 -*-
"""
MES质量追溯系统 —— 成型/硫化人员分析
在原有页面基础上，为「成型人员分析」「硫化人员分析」两张表增加一键导出功能。

导出特性：
1. 导出内容与当前页面的筛选开关完全一致（显示成型机台 / 显示硫化机台 / 不显示胎侧缺胶）。
2. Excel 内含 3 类工作表：
   - 「XX人员分析」：与页面完全一致的合并单元格版式（可直接打印/汇报）
   - 「XX明细数据」：扁平明细，带自动筛选，可直接做数据透视表
   - 「导出说明」：导出时间、数据口径、统计口径说明
3. 支持"按人员筛选导出"，只导出选中的主手；不选即导出全部（一键导出默认行为）。
4. 若运行环境缺少 openpyxl，自动降级为 CSV（UTF-8 BOM，Excel 可直接打开）。

用法：
- render_molding_analysis(df) / render_vulcanization_analysis(df) 自带导出按钮，无需改动调用处。
- 如需把两张表合并导出成一个文件，在页面顶部额外调用一次 render_combined_export_button(df)。
"""

from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

# openpyxl 为可选依赖：缺失时导出自动降级为 CSV
try:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    _HAS_OPENPYXL = True
except Exception:  # pragma: no cover
    _HAS_OPENPYXL = False


# ======================================================================
# 一键导出：Excel 构建
# ======================================================================

# 数据区在 Excel 中的起始行（1 基）：1=标题 2=口径说明 3=空行 4=表头 5=首行数据
_EXCEL_DATA_START = 5

_HEADER_FILL = PatternFill("solid", fgColor="F0F2F6") if _HAS_OPENPYXL else None
_THIN = Side(style="thin", color="D9D9D9") if _HAS_OPENPYXL else None
_BORDER = Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN) if _HAS_OPENPYXL else None

_CJK_FACTOR = 2  # 中文字符按 2 个字符宽度估算


def _cn_len(value) -> int:
    """按中文全角、半角混排估算显示宽度"""
    text = "" if value is None else str(value)
    return sum(_CJK_FACTOR if ord(ch) > 0x2E80 else 1 for ch in text)


def _autofit_widths(col_order, rows, min_width=9, max_width=34):
    """按内容估算列宽，返回每列的显示宽度"""
    widths = []
    for idx in range(len(col_order)):
        longest = _cn_len(col_order[idx])
        for row in rows:
            if idx < len(row):
                value = row[idx]
                if value not in ("", None):
                    longest = max(longest, _cn_len(value))
        widths.append(int(min(max(longest + 3, min_width), max_width)))
    return widths


def _write_banner(ws, ncols, title, note):
    """写入标题行与口径说明行"""
    last_col = get_column_letter(max(ncols, 1))

    ws.merge_cells(f"A1:{last_col}1")
    cell = ws["A1"]
    cell.value = title
    cell.font = Font(name="微软雅黑", size=14, bold=True, color="1F3864")
    cell.alignment = Alignment(horizontal="left", vertical="center")
    ws.row_dimensions[1].height = 26

    ws.merge_cells(f"A2:{last_col}2")
    cell = ws["A2"]
    cell.value = note
    cell.font = Font(name="微软雅黑", size=9, color="7F7F7F")
    cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=False)
    ws.row_dimensions[2].height = 16


def _write_merged_sheet(ws, title, note, col_order, rows, merges):
    """写出与页面版式一致的合并单元格表格"""
    ncols = len(col_order)
    _write_banner(ws, ncols, title, note)

    # 表头
    for idx, name in enumerate(col_order, start=1):
        cell = ws.cell(row=_EXCEL_DATA_START - 1, column=idx, value=name)
        cell.font = Font(name="微软雅黑", size=10, bold=True, color="1F3864")
        cell.fill = _HEADER_FILL
        cell.border = _BORDER
        cell.alignment = Alignment(horizontal="center", vertical="center")

    # 数据区
    for r_off, row in enumerate(rows):
        excel_row = _EXCEL_DATA_START + r_off
        for c_off in range(ncols):
            value = row[c_off] if c_off < len(row) else ""
            cell = ws.cell(row=excel_row, column=c_off + 1, value=value)
            cell.font = Font(name="微软雅黑", size=10)
            cell.border = _BORDER
            cell.alignment = Alignment(horizontal="center", vertical="center")

    # 合并区域（rows 为 0 基索引，Excel 为 1 基）
    for r1, r2, col_idx in merges:
        if r2 > r1:
            ws.merge_cells(
                start_row=_EXCEL_DATA_START + r1,
                end_row=_EXCEL_DATA_START + r2,
                start_column=col_idx + 1,
                end_column=col_idx + 1,
            )

    # 列宽
    for idx, width in enumerate(_autofit_widths(col_order, rows), start=1):
        ws.column_dimensions[get_column_letter(idx)].width = width

    # 冻结表头
    ws.freeze_panes = ws.cell(row=_EXCEL_DATA_START, column=1)


def _write_flat_sheet(ws, flat_df, title, note, person_col):
    """写出扁平明细表，带自动筛选，便于数据透视"""
    ncols = len(flat_df.columns)
    last_col = get_column_letter(max(ncols, 1))
    _write_banner(ws, ncols, title, note)

    for idx, name in enumerate(flat_df.columns, start=1):
        cell = ws.cell(row=_EXCEL_DATA_START - 1, column=idx, value=name)
        cell.font = Font(name="微软雅黑", size=10, bold=True, color="1F3864")
        cell.fill = _HEADER_FILL
        cell.border = _BORDER
        cell.alignment = Alignment(horizontal="center", vertical="center")

    values = flat_df.values.tolist()
    for r_off, row in enumerate(values):
        excel_row = _EXCEL_DATA_START + r_off
        for c_off, value in enumerate(row):
            cell = ws.cell(row=excel_row, column=c_off + 1, value=value)
            cell.font = Font(name="微软雅黑", size=10)
            cell.border = _BORDER
            cell.alignment = Alignment(horizontal="center", vertical="center")

    for idx, width in enumerate(_autofit_widths(list(flat_df.columns), values), start=1):
        ws.column_dimensions[get_column_letter(idx)].width = width

    if len(flat_df):
        ws.auto_filter.ref = (
            f"A{_EXCEL_DATA_START - 1}:{last_col}{_EXCEL_DATA_START + len(flat_df) - 1}"
        )
    ws.freeze_panes = ws.cell(row=_EXCEL_DATA_START, column=1)


def _write_readme_sheet(ws, title, meta_rows):
    """写出「导出说明」工作表"""
    ws["A1"] = title
    ws["A1"].font = Font(name="微软雅黑", size=14, bold=True, color="1F3864")

    ws["A2"] = "项目"
    ws["B2"] = "内容"
    for coord in ("A2", "B2"):
        ws[coord].font = Font(name="微软雅黑", size=10, bold=True, color="1F3864")
        ws[coord].fill = _HEADER_FILL
        ws[coord].border = _BORDER
        ws[coord].alignment = Alignment(horizontal="center", vertical="center")

    for offset, (key, value) in enumerate(meta_rows):
        excel_row = 3 + offset
        kc = ws.cell(row=excel_row, column=1, value=key)
        vc = ws.cell(row=excel_row, column=2, value=value)
        for cell in (kc, vc):
            cell.font = Font(name="微软雅黑", size=10)
            cell.border = _BORDER
            cell.alignment = Alignment(horizontal="left", vertical="center")
        kc.font = Font(name="微软雅黑", size=10, bold=True)

    ws.column_dimensions["A"].width = 20
    ws.column_dimensions["B"].width = 90


def build_personnel_workbook(specs):
    """
    构建 Excel 工作簿。

    specs: list of dict
        {
            "sheet": "成型人员分析",
            "title": "成型人员分析（不含返修）",
            "note":  "数据口径说明…",
            "person_col": "成型主手",
            "extra_col": "成型" or None,
            "df": person_detail,
        }
    返回 bytes；无 openpyxl 时返回 None。
    """
    if not _HAS_OPENPYXL:
        return None

    wb = Workbook()
    wb.remove(wb.active)
    meta_rows = [("导出时间", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))]

    for spec in specs:
        person_df = spec["df"]
        if person_df is None or person_df.empty:
            continue

        col_order, rows, merges = _expand_person_detail(
            person_df,
            person_col=spec["person_col"],
            extra_col=spec.get("extra_col"),
        )

        ws = wb.create_sheet(title=spec["sheet"][:31])
        _write_merged_sheet(ws, spec["title"], spec["note"], col_order, rows, merges)

        flat_cols = [c for c in col_order if c != "合计"] + ["合计"]
        ws2 = wb.create_sheet(title=f"{spec['sheet'][:28]}_明细数据")
        _write_flat_sheet(ws2, person_df[flat_cols], spec["title"], spec["note"], spec["person_col"])

        meta_rows.append(
            (
                spec["sheet"],
                f"{len(person_df)} 行明细 / {person_df[spec['person_col']].nunique()} 人 / "
                f"合计 {int(person_df['数量'].sum())} 条；口径：{spec['note']}",
            )
        )

    ws3 = wb.create_sheet(title="导出说明")
    _write_readme_sheet(ws3, "导出说明", meta_rows)

    import io

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def build_csv_bytes(specs):
    """降级方案：打包为 ZIP（内含每个表的 CSV，UTF-8 BOM，Excel 可直接打开）"""
    import io
    import zipfile

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for spec in specs:
            person_df = spec["df"]
            if person_df is None or person_df.empty:
                continue
            csv_text = person_df.to_csv(index=False)
            zf.writestr(f"{spec['sheet']}.csv", csv_text.encode("utf-8-sig"))
        zf.writestr(
            "导出说明.txt",
            f"导出时间：{datetime.now():%Y-%m-%d %H:%M:%S}\n"
            + "\n".join(f"{s['sheet']}：{s['note']}" for s in specs),
        )
    return buffer.getvalue()


# ======================================================================
# 合并单元格布局：HTML 与 Excel 共用同一份展开逻辑
# ======================================================================

def _expand_person_detail(
    person_df,
    person_col,
    extra_col=None,
    type_col="类型",
    cause_col="病象",
    count_col="数量",
    total_col="合计",
):
    """
    将分组明细展开为「二维表 + 合并区域」。

    返回 (col_order, rows, merges)
      col_order : 列顺序
      rows      : 展开后的二维列表，被合并覆盖的位置为空字符串
      merges    : [(起始行0基, 结束行0基, 列索引0基), ...]
    HTML 渲染与 Excel 导出共用此函数，保证两者版式完全一致。
    """
    if extra_col and extra_col in person_df.columns:
        col_order = [person_col, extra_col, type_col, cause_col, count_col, total_col]
    else:
        col_order = [person_col, type_col, cause_col, count_col, total_col]

    for c in col_order:
        if c not in person_df.columns:
            raise ValueError(f"缺少列: {c}")

    idx_person = col_order.index(person_col)
    idx_extra = col_order.index(extra_col) if extra_col and extra_col in person_df.columns else None
    idx_type = col_order.index(type_col)
    idx_total = col_order.index(total_col)

    rows: list[list] = []
    merges: list[tuple] = []

    n = len(person_df)
    i = 0
    while i < n:
        current_person = person_df.iloc[i][person_col]
        person_end = i
        while person_end < n and person_df.iloc[person_end][person_col] == current_person:
            person_end += 1
        person_start_row = len(rows)

        j = i
        while j < person_end:
            current_type = person_df.iloc[j][type_col]
            type_end = j
            while type_end < person_end and person_df.iloc[type_end][type_col] == current_type:
                type_end += 1
            type_start_row = len(rows)

            for k in range(j, type_end):
                row = [""] * len(col_order)
                if k == i:
                    row[idx_person] = current_person
                if idx_extra is not None:
                    row[idx_extra] = person_df.iloc[k][extra_col]
                if k == j:
                    row[idx_type] = current_type
                row[col_order.index(cause_col)] = person_df.iloc[k][cause_col]
                row[col_order.index(count_col)] = person_df.iloc[k][count_col]
                if k == i:
                    row[idx_total] = person_df.iloc[k][total_col]
                rows.append(row)

            if len(rows) - type_start_row > 1:
                merges.append((type_start_row, len(rows) - 1, idx_type))
            j = type_end

        if len(rows) - person_start_row > 1:
            merges.append((person_start_row, len(rows) - 1, idx_person))
            merges.append((person_start_row, len(rows) - 1, idx_total))
        i = person_end

    return col_order, rows, merges


def render_merged_person_table(
    person_df,
    person_col,
    type_col="类型",
    cause_col="病象",
    count_col="数量",
    total_col="合计",
    max_height="600px",
    extra_col=None,
):
    if person_df.empty:
        return ""

    col_order, rows, merges = _expand_person_detail(
        person_df,
        person_col=person_col,
        extra_col=extra_col,
        type_col=type_col,
        cause_col=cause_col,
        count_col=count_col,
        total_col=total_col,
    )

    rowspan_map = {(r1, c): r2 - r1 + 1 for r1, r2, c in merges}

    st.markdown(
        """
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
    """,
        unsafe_allow_html=True,
    )

    html = f'<div class="scrollable-table" style="max-height: {max_height};">'
    html += '<table class="merged-person-table">'
    header = "<tr>" + "".join([f"<th>{c}</th>" for c in col_order]) + "</tr>"
    html += f"<thead>{header}</thead><tbody>"

    for r_off, row in enumerate(rows):
        html += "<tr>"
        for c_off, value in enumerate(row):
            span = rowspan_map.get((r_off, c_off))
            if span:
                html += f'<td rowspan="{span}" style="vertical-align: middle;">{value}</td>'
            elif value != "" or not _is_covered(rows, merges, r_off, c_off):
                html += f"<td>{value}</td>"
        html += "</tr>"

    html += "</tbody></table></div>"
    return html


def _is_covered(rows, merges, r_off, c_off) -> bool:
    """判断某单元格是否落在某个合并区域内（用于 HTML 跳过被覆盖的空位）"""
    for r1, r2, c in merges:
        if c == c_off and r1 < r_off <= r2:
            return True
    return False


# ======================================================================
# 数据准备（页面与导出共用，保证口径一致）
# ======================================================================

def _molding_person_detail(df, show_machine=True):
    condition = ((df["车间"] == "成型") | (df["类型"] == "次品UF")) & (df["类型"] != "返修")
    molding_data = df[condition]

    if molding_data.empty:
        return pd.DataFrame(), None

    if show_machine:
        person_detail = (
            molding_data.groupby(["成型主手", "成型", "类型", "病象"]).size().reset_index(name="数量")
        )
        extra = "成型"
    else:
        person_detail = molding_data.groupby(["成型主手", "类型", "病象"]).size().reset_index(name="数量")
        extra = None

    person_detail["合计"] = person_detail.groupby("成型主手")["数量"].transform("sum")
    person_detail = person_detail.sort_values(
        ["合计", "成型主手", "类型", "病象"], ascending=[False, True, True, True]
    )
    return person_detail.reset_index(drop=True), extra


def _vulcanization_person_detail(df, show_machine=True, hide_side_glue=True):
    vul_data = df[(df["车间"] == "硫化") & (df["类型"].isin(["废品", "次品外观"]))]
    if hide_side_glue:
        vul_data = vul_data[vul_data["病象"] != "胎侧缺胶"]

    if vul_data.empty:
        return pd.DataFrame(), None

    if show_machine:
        person_detail = (
            vul_data.groupby(["硫化主手", "硫化", "类型", "病象"]).size().reset_index(name="数量")
        )
        extra = "硫化"
    else:
        person_detail = vul_data.groupby(["硫化主手", "类型", "病象"]).size().reset_index(name="数量")
        extra = None

    person_detail["合计"] = person_detail.groupby("硫化主手")["数量"].transform("sum")
    person_detail = person_detail.sort_values(
        ["合计", "硫化主手", "类型", "病象"], ascending=[False, True, True, True]
    )
    return person_detail.reset_index(drop=True), extra


# ======================================================================
# 导出工具栏（页面上的一键导出按钮）
# ======================================================================

def _render_export_toolbar(key_prefix, sheet_name, file_stem, person_detail, person_col, extra_col, note):
    """渲染「人员筛选 + 一键导出」工具栏"""
    persons = sorted(person_detail[person_col].astype(str).unique().tolist())

    left, right = st.columns([5, 1.35])

    with left:
        use_filter = st.checkbox(
            "按人员筛选导出",
            value=False,
            key=f"{key_prefix}_export_filter",
            help="勾选后可只导出指定主手；不勾选时为「一键导出全部」",
        )
        selected = []
        if use_filter:
            selected = st.multiselect(
                "选择要导出的主手（留空 = 全部）",
                options=persons,
                key=f"{key_prefix}_export_persons",
                placeholder=f"共 {len(persons)} 人，留空导出全部",
            )

    export_df = person_detail
    if selected:
        export_df = person_detail[person_detail[person_col].astype(str).isin(selected)]

    spec = {
        "sheet": sheet_name,
        "title": f"{sheet_name}（不含返修）",
        "note": note,
        "person_col": person_col,
        "extra_col": extra_col,
        "df": export_df,
    }

    with right:
        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        if export_df.empty:
            st.button("📥 一键导出", key=f"{key_prefix}_export_btn", disabled=True, use_container_width=True)
        elif _HAS_OPENPYXL:
            payload = build_personnel_workbook([spec])
            st.download_button(
                "📥 一键导出",
                data=payload,
                file_name=f"{file_stem}_{datetime.now():%Y%m%d_%H%M%S}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key=f"{key_prefix}_export_btn",
                use_container_width=True,
                help=f"导出当前筛选条件下的 {len(export_df)} 行明细",
            )
        else:
            payload = build_csv_bytes([spec])
            st.download_button(
                "📥 一键导出CSV",
                data=payload,
                file_name=f"{file_stem}_{datetime.now():%Y%m%d_%H%M%S}.zip",
                mime="application/zip",
                key=f"{key_prefix}_export_btn",
                use_container_width=True,
                help="未安装 openpyxl，已降级为 CSV",
            )

    return export_df


# ======================================================================
# 原有页面渲染函数（均已内置导出按钮）
# ======================================================================

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


def render_molding_analysis(df):
    st.markdown("**成型人员分析**")
    with st.container():
        show_molding_machine = st.checkbox("显示成型机台", value=True, key="molding_machine")

    person_detail, extra = _molding_person_detail(df, show_molding_machine)

    if not person_detail.empty:
        machine_text = "显示成型机台" if show_molding_machine else "不显示成型机台"
        note = f"车间=成型 或 类型=次品UF；已排除类型=返修；{machine_text}"
        _render_export_toolbar(
            key_prefix="molding",
            sheet_name="成型人员分析",
            file_stem="成型人员分析",
            person_detail=person_detail,
            person_col="成型主手",
            extra_col=extra,
            note=note,
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

    person_detail, extra = _vulcanization_person_detail(df, show_vul_machine, hide_side_glue)

    if not person_detail.empty:
        machine_text = "显示硫化机台" if show_vul_machine else "不显示硫化机台"
        glue_text = "已排除胎侧缺胶" if hide_side_glue else "包含胎侧缺胶"
        note = f"车间=硫化；类型∈(废品, 次品外观)；{machine_text}；{glue_text}"
        _render_export_toolbar(
            key_prefix="vul",
            sheet_name="硫化人员分析",
            file_stem="硫化人员分析",
            person_detail=person_detail,
            person_col="硫化主手",
            extra_col=extra,
            note=note,
        )
        html = render_merged_person_table(person_detail, "硫化主手", extra_col=extra, max_height="600px")
        if html:
            st.markdown(html, unsafe_allow_html=True)
    else:
        st.info("无硫化数据（废品/次品外观）")


def render_combined_export_button(df):
    """
    可选：把「成型人员分析」和「硫化人员分析」合并导出为一个 Excel 文件。
    在页面任意位置调用一次即可，例如标题下方：

        render_combined_export_button(df)
    """
    show_molding_machine = st.session_state.get("molding_machine", True)
    show_vul_machine = st.session_state.get("vul_machine", True)
    hide_side_glue = st.session_state.get("hide_side_glue", True)

    molding_df, molding_extra = _molding_person_detail(df, show_molding_machine)
    vul_df, vul_extra = _vulcanization_person_detail(df, show_vul_machine, hide_side_glue)

    specs = [
        {
            "sheet": "成型人员分析",
            "title": "成型人员分析（不含返修）",
            "note": (
                f"车间=成型 或 类型=次品UF；已排除类型=返修；"
                f"{'显示成型机台' if show_molding_machine else '不显示成型机台'}"
            ),
            "person_col": "成型主手",
            "extra_col": molding_extra,
            "df": molding_df,
        },
        {
            "sheet": "硫化人员分析",
            "title": "硫化人员分析（不含返修）",
            "note": (
                f"车间=硫化；类型∈(废品, 次品外观)；"
                f"{'显示硫化机台' if show_vul_machine else '不显示硫化机台'}；"
                f"{'已排除胎侧缺胶' if hide_side_glue else '包含胎侧缺胶'}"
            ),
            "person_col": "硫化主手",
            "extra_col": vul_extra,
            "df": vul_df,
        },
    ]

    left, right = st.columns([5, 1.6])
    with left:
        st.caption("💡 提示：每张表下方均有独立的一键导出按钮；此处可一次导出两张表。")
    with right:
        if _HAS_OPENPYXL:
            st.download_button(
                "📥 导出成型+硫化",
                data=build_personnel_workbook(specs),
                file_name=f"成型硫化人员分析_{datetime.now():%Y%m%d_%H%M%S}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="combined_export_btn",
                use_container_width=True,
            )
        else:
            st.download_button(
                "📥 导出CSV包",
                data=build_csv_bytes(specs),
                file_name=f"成型硫化人员分析_{datetime.now():%Y%m%d_%H%M%S}.zip",
                mime="application/zip",
                key="combined_export_btn",
                use_container_width=True,
            )