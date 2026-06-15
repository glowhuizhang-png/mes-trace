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

    # ========== 右侧控件 ==========
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

    # 确保 toolbar 容器固定在右侧
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

# ========== 固定导航栏 (按钮) ==========
    if "page" not in st.session_state:
        st.session_state.page = "dashboard"

    st.markdown(
        '<div class="fixed-nav">',
        unsafe_allow_html=True
    )

    # 六个按钮横排
    nav1, nav2, nav3, nav4, nav5, nav6 = st.columns(6)

    with nav1:
        if st.button("📊 综合看板", key="nav_dashboard", use_container_width=True):
            st.session_state.page = "dashboard"

    with nav2:
        if st.button("🧩 缺陷分析", key="nav_defect", use_container_width=True):
            st.session_state.page = "defect"

    with nav3:
        if st.button("⚡ UF分析", key="nav_uf", use_container_width=True):
            st.session_state.page = "uf"

    with nav4:
        if st.button("👥 人员分析", key="nav_person", use_container_width=True):
            st.session_state.page = "person"

    with nav5:
        if st.button("🔧 返修分析", key="nav_repair", use_container_width=True):
            st.session_state.page = "repair"

    with nav6:
        if st.button("📈 Pareto", key="nav_pareto", use_container_width=True):
            st.session_state.page = "pareto"

    st.markdown(
        '</div>',
        unsafe_allow_html=True
    )

    # ========== 内容区 ==========
    st.markdown('<div class="content-wrapper">', unsafe_allow_html=True)

    if not selected_dates:
        st.warning("请选择日期")
        st.markdown('</div>', unsafe_allow_html=True)
        return

    raw = load_raw(selected_dates, RAW_DIR)
    if raw.empty:
        st.error("无数据")
        st.markdown('</div>', unsafe_allow_html=True)
        return

    df = derive_columns(raw, code_to_cause, code_to_shop, cause_to_shop)
    daily_prod_dict = load_daily_production_dict(selected_dates, PRODUCTION_FILE)
    daily_metrics = compute_daily_metrics(df, daily_prod_dict)

    sorted_dates = sorted([d for d in daily_metrics.keys() if d in daily_prod_dict and daily_prod_dict[d] > 0])
    latest_date = sorted_dates[-1] if sorted_dates else None
    prev_date = sorted_dates[-2] if len(sorted_dates) >= 2 else None

    latest = daily_metrics.get(latest_date, {}) if latest_date else {}
    prev = daily_metrics.get(prev_date, {}) if prev_date else {}

    def calc_change(curr, prev, key):
        if prev and prev.get(key, 0) != 0:
            return (curr.get(key, 0) - prev.get(key, 0)) / prev.get(key, 0)
        return None

    prod_change = calc_change(latest, prev, "production")
    waste_rate_change = calc_change(latest, prev, "waste_rate")
    app_rate_change = calc_change(latest, prev, "app_rate")
    uf_rate_change = calc_change(latest, prev, "uf_rate")
    qual_rate_change = calc_change(latest, prev, "qual_rate")
    waste_cnt_change = calc_change(latest, prev, "waste_cnt")
    app_cnt_change = calc_change(latest, prev, "app_cnt")
    uf_cnt_change = calc_change(latest, prev, "uf_cnt")

    waste_cnt_abs_change = latest.get("waste_cnt", 0) - prev.get("waste_cnt", 0) if prev else None
    app_cnt_abs_change = latest.get("app_cnt", 0) - prev.get("app_cnt", 0) if prev else None
    uf_cnt_abs_change = latest.get("uf_cnt", 0) - prev.get("uf_cnt", 0) if prev else None
    prod_abs_change = latest.get("production", 0) - prev.get("production", 0) if prev else None

    total_production = latest.get("production", 0)
    qual_rate = latest.get("qual_rate", 1)
    waste_rate = latest.get("waste_rate", 0)
    app_rate = latest.get("app_rate", 0)
    uf_rate = latest.get("uf_rate", 0)
    waste_cnt = latest.get("waste_cnt", 0)
    app_cnt = latest.get("app_cnt", 0)
    uf_cnt = latest.get("uf_cnt", 0)

    waste_df = df[df["类型"] == "废品"]
    app_df = df[df["类型"] == "次品外观"]
    uf_df = df[df["类型"] == "次品UF"]
    waste_shop = waste_df["车间"].value_counts().reset_index()
    waste_shop.columns = ["车间", "数量"]
    app_shop = app_df["车间"].value_counts().reset_index()
    app_shop.columns = ["车间", "数量"]
    uf_mac = uf_df["成型"].value_counts().reset_index()
    uf_mac.columns = ["成型", "数量"]

    daily_stats = None
    if len(selected_dates) > 1 and daily_prod_dict:
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

    # ========== 页面路由 ==========
    if selected_page == "dashboard":
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
        )
    elif selected_page == "defect":
        render_defect_analysis(
            df=df, waste_df=waste_df, app_df=app_df,
            selected_dates=selected_dates,
            photo_index=PHOTO_INDEX,
            detail_table_callback=render_detail_table
        )
    elif selected_page == "uf":
        st.subheader("UF 次品分析")
        uf_check_data = load_uf_check_data(UF_DATA_DIR)
        render_uf_detail_table(uf_df, uf_check_data, "uf_detail", height=680)
    elif selected_page == "person":
        st.subheader("成型/硫化人员分析（不含返修）")
        left_col, right_col = st.columns(2)
        with left_col:
            st.markdown("**成型人员分析**")
            show_molding_machine = st.checkbox("显示成型机台", value=True)
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
                render_merged_person_table(person_detail, "成型主手", extra_col=extra)
            else:
                st.info("无成型及UF数据")
        with right_col:
            st.markdown("**硫化人员分析**")
            show_vul_machine = st.checkbox("显示硫化机台", value=True)
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
                render_merged_person_table(person_detail, "硫化主手", extra_col=extra)
            else:
                st.info("无硫化数据（废品/次品外观）")
    elif selected_page == "repair":
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
    elif selected_page == "pareto":
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

    st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()