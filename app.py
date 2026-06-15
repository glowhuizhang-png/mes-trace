import streamlit as st
import pandas as pd
import os
from datetime import datetime

try:
    from streamlit_autorefresh import st_autorefresh
    AUTOREFRESH_AVAILABLE = True
except ImportError:
    AUTOREFRESH_AVAILABLE = False

from modules.config import (
    BASE_DIR, RULE_FILE, RAW_DIR, PHOTO_BASE_DIR,
    PRODUCTION_FILE, UF_DATA_DIR, APP_VERSION
)
from modules.loader import (
    load_rule, load_raw, load_production, load_uf_check_data,
    load_daily_production_dict, derive_columns
)
from modules.dashboard import render_dashboard
from modules.defect_analysis import render_defect_analysis
from modules.photo import build_photo_index, trigger_image_popup
from modules.personnel import render_merged_person_table
from modules.repair import render_repair_table
from modules.pareto import build_pareto_chart
from modules.uf import render_uf_detail_table
from modules.theme import apply_dark_theme

st.set_page_config(
    page_title="轮胎质量智能分析系统",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': None
    }
)

apply_dark_theme()
PHOTO_INDEX = build_photo_index(PHOTO_BASE_DIR)

def get_all_dates():
    files = []
    if not os.path.exists(RAW_DIR):
        return files
    for f in os.listdir(RAW_DIR):
        if f.endswith(".xls") or f.endswith(".xlsx"):
            name = f.split(".")[0]
            if len(name) == 8 and name.isdigit():
                files.append(name)
    return sorted(files, reverse=True)

def compute_daily_metrics(df, daily_prod_dict):
    if df.empty or not daily_prod_dict:
        return {}
    prod_series = pd.Series(daily_prod_dict, name='production')
    type_counts = df.groupby(['文件日期', '类型']).size().unstack(fill_value=0)
    metrics = prod_series.to_frame().join(type_counts, how='inner')
    for col in ['废品', '次品外观', '次品UF']:
        if col not in metrics.columns:
            metrics[col] = 0
    metrics = metrics.rename(columns={'废品': 'waste_cnt', '次品外观': 'app_cnt', '次品UF': 'uf_cnt'})
    metrics['waste_rate'] = metrics['waste_cnt'] / metrics['production']
    metrics['app_rate'] = metrics['app_cnt'] / metrics['production']
    metrics['uf_rate'] = metrics['uf_cnt'] / metrics['production']
    metrics['qual_rate'] = 1 - (metrics['waste_cnt'] + metrics['app_cnt'] + metrics['uf_cnt']) / metrics['production']
    return metrics.to_dict('index')

def render_detail_table(df, key_prefix, height=680, enable_click=True):
    if df.empty:
        st.info("无数据")
        return
    photo_col = None
    for col in df.columns:
        if "胎胚编码" in col or "条码" in col:
            photo_col = col
            break
    if enable_click and photo_col:
        st.dataframe(df, height=height, use_container_width=True)
        col1, col2 = st.columns([4, 1])
        with col1:
            barcode_input = st.text_input("输入胎胚编码查看图片", key=f"{key_prefix}_barcode_input")
        with col2:
            if st.button("查看图片", key=f"{key_prefix}_view_btn"):
                if barcode_input.strip():
                    trigger_image_popup(barcode_input.strip(), PHOTO_INDEX)
                else:
                    st.warning("请输入胎胚编码")
    else:
        st.dataframe(df, height=height, use_container_width=True)

def main():
    if AUTOREFRESH_AVAILABLE:
        st_autorefresh(interval=60000, key="auto_refresh")

    code_to_cause, code_to_shop, cause_to_shop = load_rule(RULE_FILE)
    all_dates = get_all_dates()

    # ========== 固定标题栏 ==========
    tire_base64 = "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjQiIGhlaWdodD0iNjQiIHZpZXdCb3g9IjAgMCA2NCA2NCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPGNpcmNsZSBjeD0iMzIiIGN5PSIzMiIgcj0iMjgiIHN0cm9rZT0iI0ZGRkZGRiIgc3Ryb2tlLXdpZHRoPSI0IiAvPgo8Y2lyY2xlIGN4PSIzMiIgY3k9IjMyIiByPSIxOCIgc3Ryb2tlPSIjRkZGRkZGIiBzdHJva2Utd2lkdGg9IjMiIC8+CjxjaXJjbGUgY3g9IjMyIiBjeT0iMzIiIHI9IjgiIGZpbGw9IiNGRkZGRkYiIC8+CjxwYXRoIGQ9Ik0zMiAyTDMyIDE0TTMyIDUwTDMyIDYyTTYgMzJMMTggMzJNNDYgMzJMNjIgMzIiIHN0cm9rZT0iI0ZGRkZGRiIgc3Ryb2tlLXdpZHRoPSIzIi8+CjxwYXRoIGQ9Ik0xMSAxMUwyMCAyME00NCAyMEw1MyAxMU00NCA0NEw1MyA1M00yMCA0NEwxMSA1MyIgc3Ryb2tlPSIjRkZGRkZGIiBzdHJva2Utd2lkdGg9IjMiLz4KPC9zdmc+"

    st.markdown(f"""
    <div class="fixed-header">
        <div class="header-left">
            <img src="{tire_base64}" alt="tire" />
            <div class="header-text">
                <div class="main-title">质量智能分析系统</div>
                <div class="sub-title">Quality Intelligent Analysis System</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ========== 右侧控件（日期、刷新、版本） ==========
    toolbar = st.container()
    with toolbar:
        c1, c2, c3 = st.columns([4, 1, 1], gap="small")
        with c1:
            selected_dates = st.multiselect(
                "日期",
                options=all_dates,
                default=all_dates[:1] if all_dates else [],
                label_visibility="collapsed",
                key="main_date_select"
            )
        with c2:
            refresh_clicked = st.button("🔄 刷新", use_container_width=True)
        with c3:
            st.markdown(f"<div style='color:white; text-align:center; padding-top:8px;'>v{APP_VERSION}</div>", unsafe_allow_html=True)

    # 右侧工具栏固定定位（稳定选择器）
    st.markdown("""
    <style>
    div.fixed-header + div {
        position: fixed;
        top: 18px;
        right: 24px;
        z-index: 100003;
        width: auto;
        background: transparent !important;
    }
    div.fixed-header + div > div {
        display: flex;
        align-items: center;
        gap: 12px;
    }
    </style>
    """, unsafe_allow_html=True)

    if refresh_clicked:
        st.cache_data.clear()
        st.cache_resource.clear()
        st.rerun()

    # ========== 固定导航 Tabs ==========
    tab_dashboard, tab_defect, tab_uf, tab_person, tab_repair, tab_pareto = st.tabs([
        "📊 综合看板",
        "🧩 缺陷分析",
        "⚡ UF分析",
        "👥 人员分析",
        "🔧 返修分析",
        "📈 Pareto"
    ])

    # ========== 智能扩展加载日期（单日时自动包含前一天） ==========
    if not selected_dates:
        st.warning("请选择日期")
        return

    load_dates = list(selected_dates)
    is_multi_day = len(selected_dates) > 1

    # 单日分析时，悄悄加入前一天（如果存在）
    if not is_multi_day and all_dates:
        selected_date = selected_dates[0]
        if selected_date in all_dates:
            idx = all_dates.index(selected_date)
            # all_dates 是倒序的，后一个索引是更早的日期
            if idx < len(all_dates) - 1:
                prev_day = all_dates[idx + 1]
                if prev_day not in load_dates:
                    load_dates.append(prev_day)

    # 用扩展后的日期加载原始数据
    raw = load_raw(load_dates, RAW_DIR)
    if raw.empty:
        st.error("无数据")
        return

    # 派生字段（完整数据，含前一天）
    df = derive_columns(raw, code_to_cause, code_to_shop, cause_to_shop)

    # 用于界面展示的数据框（仅用户选中日期）
    df_display = df[df["文件日期"].isin(selected_dates)]

    # 加载产量字典（基于 load_dates，确保前一天产量也在内）
    daily_prod_dict = load_daily_production_dict(load_dates, PRODUCTION_FILE)
    # 计算每日指标（基于完整 df，因此会包含前一天的指标）
    daily_metrics = compute_daily_metrics(df, daily_prod_dict)

    # ---------- 提取展示用的分类数据 ----------
    waste_df = df_display[df_display["类型"] == "废品"]
    app_df   = df_display[df_display["类型"] == "次品外观"]
    uf_df    = df_display[df_display["类型"] == "次品UF"]
    waste_shop = waste_df["车间"].value_counts().reset_index()
    waste_shop.columns = ["车间", "数量"]
    app_shop   = app_df["车间"].value_counts().reset_index()
    app_shop.columns = ["车间", "数量"]
    uf_mac     = uf_df["成型"].value_counts().reset_index()
    uf_mac.columns = ["成型", "数量"]

    # ---------- 确定“今日”和“昨日”日期 ----------
    all_valid_dates = sorted([d for d in daily_metrics.keys() if daily_prod_dict.get(d, 0) > 0])
    selected_sorted = sorted(selected_dates)
    latest_date = selected_sorted[-1] if selected_sorted else None
    if latest_date:
        prev_candidates = [d for d in all_valid_dates if d < latest_date]
        prev_date = prev_candidates[-1] if prev_candidates else None
    else:
        prev_date = None

    latest = daily_metrics.get(latest_date, {}) if latest_date else {}
    prev   = daily_metrics.get(prev_date, {}) if prev_date else {}

    def calc_change(curr, prev, key):
        if prev and prev.get(key, 0) != 0:
            return (curr.get(key, 0) - prev.get(key, 0)) / prev.get(key, 0)
        return None

    # ---------- 单日 / 多日的 KPI 计算 ----------
    if is_multi_day:
        # 多日：汇总用户选中的日期
        total_production = sum(daily_prod_dict.get(d, 0) for d in selected_dates)
        waste_cnt = len(waste_df)
        app_cnt   = len(app_df)
        uf_cnt    = len(uf_df)
        total_defects = waste_cnt + app_cnt + uf_cnt
        qual_rate = 1 - total_defects / total_production if total_production > 0 else 1
        waste_rate = waste_cnt / total_production if total_production > 0 else 0
        app_rate   = app_cnt / total_production if total_production > 0 else 0
        uf_rate    = uf_cnt / total_production if total_production > 0 else 0

        # 多日不显示变化量
        prod_change = None
        prod_abs_change = None
        waste_rate_change = None
        waste_cnt_change = None
        waste_cnt_abs_change = None
        app_rate_change = None
        app_cnt_change = None
        app_cnt_abs_change = None
        uf_rate_change = None
        uf_cnt_change = None
        uf_cnt_abs_change = None
        qual_rate_change = None
    else:
        # 单日：使用当天（selected_date）的统计值，产量从 daily_prod_dict 取
        selected_date = selected_dates[0]
        total_production = daily_prod_dict.get(selected_date, 0)
        waste_cnt = len(waste_df)
        app_cnt   = len(app_df)
        uf_cnt    = len(uf_df)
        total_defects = waste_cnt + app_cnt + uf_cnt
        qual_rate = 1 - total_defects / total_production if total_production > 0 else 1
        waste_rate = waste_cnt / total_production if total_production > 0 else 0
        app_rate   = app_cnt / total_production if total_production > 0 else 0
        uf_rate    = uf_cnt / total_production if total_production > 0 else 0

        # 变化量基于 latest（今日）与 prev（昨日）字典
        prod_change = calc_change(latest, prev, "production")
        waste_rate_change = calc_change(latest, prev, "waste_rate")
        app_rate_change   = calc_change(latest, prev, "app_rate")
        uf_rate_change    = calc_change(latest, prev, "uf_rate")
        qual_rate_change  = calc_change(latest, prev, "qual_rate")
        waste_cnt_change  = calc_change(latest, prev, "waste_cnt")
        app_cnt_change    = calc_change(latest, prev, "app_cnt")
        uf_cnt_change     = calc_change(latest, prev, "uf_cnt")

        waste_cnt_abs_change = (latest.get("waste_cnt", 0) - prev.get("waste_cnt", 0)) if prev else None
        app_cnt_abs_change   = (latest.get("app_cnt", 0) - prev.get("app_cnt", 0)) if prev else None
        uf_cnt_abs_change    = (latest.get("uf_cnt", 0) - prev.get("uf_cnt", 0)) if prev else None
        prod_abs_change      = (latest.get("production", 0) - prev.get("production", 0)) if prev else None

    # ---------- 日趋势数据（仅多天时显示） ----------
    daily_stats = None
    if is_multi_day and daily_prod_dict:
        daily_list = []
        for d in sorted(selected_dates):
            if d in daily_metrics:
                m = daily_metrics[d]
                daily_list.append({
                    "日期": pd.to_datetime(d, format='%Y%m%d').strftime('%m/%d'),
                    "废品率": m["waste_rate"],
                    "外观次品率": m["app_rate"],
                    "UF次品率": m["uf_rate"],
                    "综合合格率": m["qual_rate"]
                })
        if daily_list:
            daily_stats = pd.DataFrame(daily_list)

    # ========== 调用综合看板 ==========
    with tab_dashboard:
        render_dashboard(
            waste_df=waste_df, app_df=app_df, uf_df=uf_df,
            waste_shop=waste_shop, app_shop=app_shop, uf_mac=uf_mac,
            daily_stats=daily_stats,
            total_production=total_production, qual_rate=qual_rate,
            waste_rate=waste_rate, app_rate=app_rate, uf_rate=uf_rate,
            prod_change=prod_change,
            waste_rate_change=waste_rate_change,
            app_rate_change=app_rate_change,
            uf_rate_change=uf_rate_change,
            qual_rate_change=qual_rate_change,
            waste_cnt=waste_cnt, app_cnt=app_cnt, uf_cnt=uf_cnt,
            waste_cnt_change=waste_cnt_change,
            app_cnt_change=app_cnt_change,
            uf_cnt_change=uf_cnt_change,
            waste_cnt_abs_change=waste_cnt_abs_change,
            app_cnt_abs_change=app_cnt_abs_change,
            uf_cnt_abs_change=uf_cnt_abs_change,
            prod_abs_change=prod_abs_change,
            is_multi_day=is_multi_day,
        )

    with tab_defect:
        render_defect_analysis(
            df=df, waste_df=waste_df, app_df=app_df,
            selected_dates=selected_dates,
            photo_index=PHOTO_INDEX,
            detail_table_callback=render_detail_table
        )

    with tab_uf:
        uf_check_data = load_uf_check_data(UF_DATA_DIR)
        render_uf_detail_table(uf_df, uf_check_data, "uf_detail", height=680)

    with tab_person:
        st.subheader("成型/硫化人员分析（不含返修）")
        st.markdown("""
        <style>
        .stCheckbox > label { background-color: white !important; border-radius: 8px; padding: 6px 12px; border: 1px solid #e2e8f0; }
        .scrollable-table { border: 1px solid #ddd; border-radius: 8px; background-color: white !important; overflow-y: auto; overflow-x: hidden; }
        .merged-table { border-collapse: collapse; font-size: 13px; text-align: center; width: 100%; background-color: white !important; }
        .merged-table thead { position: sticky; top: 0; z-index: 10; }
        .merged-table th { background-color: #f0f2f6 !important; font-weight: 600; padding: 8px 4px; border: 1px solid #ddd; }
        .merged-table td { padding: 6px 3px; border: 1px solid #ddd; background-color: white !important; color: #333 !important; }
        .merged-table tbody tr { background-color: white !important; }
        </style>
        """, unsafe_allow_html=True)
        left_col, right_col = st.columns(2)
        with left_col:
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
                person_detail = person_detail.sort_values(["合计", "成型主手", "类型", "病象"], ascending=[False, True, True, True])
                html_output = render_merged_person_table(person_detail, "成型主手", extra_col=extra, max_height="400px")
                st.markdown(html_output, unsafe_allow_html=True)
            else:
                st.info("无成型及UF数据")
        with right_col:
            show_vul_machine = st.checkbox("显示硫化机台", value=True, key="vul_machine")
            vul_data = df[(df["车间"] == "硫化") & (df["类型"].isin(["废品", "次品外观"]))]
            if not vul_data.empty:
                if show_vul_machine:
                    person_detail = vul_data.groupby(["硫化主手", "硫化", "类型", "病象"]).size().reset_index(name="数量")
                    extra = "硫化"
                else:
                    person_detail = vul_data.groupby(["硫化主手", "类型", "病象"]).size().reset_index(name="数量")
                    extra = None
                person_detail["合计"] = person_detail.groupby("硫化主手")["数量"].transform("sum")
                person_detail = person_detail.sort_values(["合计", "硫化主手", "类型", "病象"], ascending=[False, True, True, True])
                html_output = render_merged_person_table(person_detail, "硫化主手", extra_col=extra, max_height="400px")
                st.markdown(html_output, unsafe_allow_html=True)
            else:
                st.info("无硫化数据（废品/次品外观）")

    with tab_repair:
        st.subheader("返修分析")
        repair_df = df[df["类型"] == "返修"]
        if not repair_df.empty:
            tire_code_col = None
            for col in repair_df.columns:
                if "胎胚编码" in col:
                    tire_code_col = col
                    break
            if not tire_code_col:
                tire_code_col = "条码"
            product_name_col = None
            for col in repair_df.columns:
                if "成品名称" in col:
                    product_name_col = col
                    break
            if not product_name_col:
                product_name_col = "规格"
            repair_std = repair_df.rename(columns={
                tire_code_col: "胎胚编码",
                product_name_col: "成品名称",
                "成型": "成型机",
                "硫化": "硫化机",
                "病象": "返修缺陷"
            })
            if "文件日期" not in repair_std.columns:
                st.error("数据中缺少“文件日期”列，无法进行日趋势分析")
            else:
                defect_counts = repair_std.groupby("返修缺陷").size().sort_values(ascending=False)
                defect_options = ["全部"] + defect_counts.index.tolist()
                selected_defect = st.selectbox("选择返修缺陷", defect_options, key="repair_defect_select")
                col_input, col_btn = st.columns([4, 1])
                with col_input:
                    repair_barcode = st.text_input("输入胎胚编码查看图片", key="repair_barcode_input")
                with col_btn:
                    if st.button("查看图片", key="repair_view_btn"):
                        if repair_barcode.strip():
                            trigger_image_popup(repair_barcode.strip(), PHOTO_INDEX)
                        else:
                            st.warning("请输入胎胚编码")
                render_repair_table(repair_std, selected_defect, selected_dates if len(selected_dates) > 1 else None)
        else:
            st.info("无返修数据")

    with tab_pareto:
        st.subheader("Pareto病象分析")
        filter_opt = st.radio(
            "分析范围", ["全部", "UC次品", "废次品"], horizontal=True, key="pareto_filter"
        )
        if filter_opt == "全部":
            df_sub = df[df["类型"].isin(["废品", "次品外观", "次品UF"])]
            title_suffix = "（全部缺陷）"
        elif filter_opt == "UC次品":
            df_sub = df[df["类型"] == "次品UF"]
            title_suffix = "（仅UF次品）"
        else:
            df_sub = df[df["类型"].isin(["废品", "次品外观"])]
            title_suffix = "（废品+外观次品）"
        fig, pareto_df = build_pareto_chart(df_sub, title_suffix)
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(pareto_df, use_container_width=True, height=600)

if __name__ == "__main__":
    main()