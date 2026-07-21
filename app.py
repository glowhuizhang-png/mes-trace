import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
from datetime import datetime, timedelta
from pathlib import Path

# 自动刷新
try:
    from streamlit_autorefresh import st_autorefresh
    AUTOREFRESH_AVAILABLE = True
except ImportError:
    AUTOREFRESH_AVAILABLE = False

# 导入自定义模块
from config import RULE_FILE, RAW_DIR, PHOTO_BASE_DIR, PRODUCTION_FILE, UF_DATA_DIR, APP_VERSION
from modules.loader import (load_rule, load_raw, load_production, load_uf_check_data, load_daily_production_dict)
from modules.derivations import derive_columns
from modules.photo import build_photo_index, trigger_image_popup
from modules.charts import style_bar_chart
from modules.personnel import (
    render_merged_person_table,
    render_molding_analysis,
    render_vulcanization_analysis,
    render_master_ranking
)
from modules.repair import render_repair_table
from modules.pareto import build_pareto_chart
from modules.uf import render_uf_detail_table
from modules.utils import find_col
from modules.detail import render_waste_appearance_analysis
from modules.correction import (
    load_corrections, apply_corrections_to_df,
    save_corrections, write_corrections_to_source
)

# ---------- CSS 样式 ----------
def inject_css():
    st.markdown("""
    <style>
    * { font-family: 'Microsoft YaHei', sans-serif !important; }
    html, body, [class*="css"], .stApp, .stMarkdown, .stText, .stDataFrame, .stTable, .stSelectbox, .stMultiSelect, .stRadio, .stCheckbox, .stButton, .stDownloadButton, .stTabs, .stTab, .stCaption, .stMetric, .stHeader, .stSubheader, .stTitle, .stPlotlyChart {
        font-family: 'Microsoft YaHei', sans-serif !important;
    }
    table, th, td, tr, thead, tbody, tfoot, caption {
        font-family: 'Microsoft YaHei', sans-serif !important;
    }
    h1 {
        margin-top: 0 !important;
        margin-bottom: 0.2rem !important;
        padding-top: 0 !important;
        padding-bottom: 0 !important;
        font-size: 32px !important;
        font-weight: 800 !important;
    }
    .block-container { padding-top: 0.5rem !important; }
    section.main > div { padding-top: 0rem !important; }
    .metric-card {
        background: #f8f9fa;
        border-radius: 16px;
        padding: 20px 16px;
        border-left: 6px solid #1976D2;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        margin-bottom: 10px;
    }
    .metric-title { font-size: 20px; font-weight: 600; }
    .metric-value { font-size: 50px; font-weight: 800; line-height: 1.2; margin: 5px 0; }
    .metric-rate { font-size: 20px; font-weight: 600; }

    [data-testid="stDataFrameGlideDataEditor"] { zoom: 1.5; }
    [data-testid="stDataEditor"] { zoom: 1.5; }
    [data-testid="stDataFrameGlideDataEditor"] td,
    [data-testid="stDataEditor"] td {
        white-space: normal !important;
        word-break: break-word;
        font-size: 20px !important;
        line-height: 1.2 !important;
    }
    table {
        text-align: center !important;
        border-collapse: collapse;
    }
    th {
        background-color: #f0f2f6 !important;
        font-weight: 700;
        padding: 14px 6px !important;
        font-size: 18px;
    }
    td {
        padding: 8px 6px !important;
        font-size: 18px !important;
        font-weight: 600;
        border-bottom: 1px solid #e0e0e0;
        line-height: 1.2;
    }
    .table-header {
        font-size: 22px;
        font-weight: 700;
        margin: 15px 0 5px 0;
        border-left: 5px solid #1976D2;
        padding-left: 12px;
    }
    /* 固定 Tabs */
    .stTabs [data-baseweb="tab-list"] {
        position: fixed !important;
        top: 3.5rem !important;
        z-index: 9999 !important;
        background: white !important;
        border-bottom: 2px solid #1976D2 !important;
        padding-top: 5px !important;
        padding-bottom: 5px !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08) !important;
        width: calc(100% - 2rem) !important;
        left: 1rem !important;
        right: 1rem !important;
    }
    .stTabs [data-baseweb="tab"] {
        font-size: 26px !important;
        font-weight: 800 !important;
        height: 65px !important;
    }
    .stTabs [aria-selected="true"] {
        color: #1976D2 !important;
        border-bottom: 4px solid #1976D2 !important;
    }
    .stTabs [role="tabpanel"] {
        padding-top: 80px !important;
    }
    .stTabs .stTabs [data-baseweb="tab-list"] {
        position: static !important;
        width: 100% !important;
        left: auto !important;
        right: auto !important;
        box-shadow: none !important;
        border-bottom: 2px solid #EEE !important;
        margin-top: 0 !important;
        padding-top: 0 !important;
        padding-bottom: 0 !important;
        z-index: auto !important;
        background: transparent !important;
    }
    .stTabs .stTabs [role="tabpanel"] {
        padding-top: 0 !important;
    }
    .stTabs .stTabs [data-baseweb="tab"] {
        font-size: 16px !important;
        height: 40px !important;
    }
    .merged-repair-table td, .merged-repair-table th {
        text-align: center !important;
        vertical-align: middle !important;
        padding: 6px 3px !important;
        border: 1px solid #ddd !important;
        font-size: 12px !important;
        font-weight: 500 !important;
    }
    .merged-repair-table th {
        background-color: #f0f2f6 !important;
        font-weight: 500 !important;
        position: sticky;
        top: 0;
        z-index: 10;
    }
    .product-name {
        text-align: left !important;
        padding-left: 12px !important;
        white-space: pre-line !important;
        word-break: break-word !important;
    }
    .machine {
        text-align: center !important;
    }
    .defect-name {
        text-align: center !important;
    }
    .scrollable-table {
        max-height: 500px;
        overflow-y: auto;
        border: 1px solid #ccc;
    }
    </style>
    """, unsafe_allow_html=True)

# ---------- 登录验证（左侧图片）----------
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if st.session_state.authenticated:
        return True

    # 登录图片路径（407x644 产品图）
    img_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "login.png")
    if not os.path.exists(img_path):
        img_path = "https://via.placeholder.com/407x644?text=轮胎产品"

    # 精简 CSS
    st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(135deg, #eef3fb, #dbe7f5);
    }
    header, footer, #MainMenu {
        visibility: hidden;
    }
    .block-container {
        max-width: 1000px;
        padding-top: 3vh;
        padding-bottom: 0;
    }
    .login-title {
        font-size: 40px;
        font-weight: 700;
        color: #1b2b5b;
        margin-bottom: 10px;
    }
    .login-sub {
        font-size: 18px;
        color: #999;
        margin-bottom: 40px;
    }
    div[data-testid="stTextInput"] {
        margin-bottom: 28px;
    }
    div[data-testid="stTextInput"] input {
        border: none;
        border-bottom: 2px solid #d8d8d8;
        border-radius: 0;
        background: transparent;
        font-size: 18px;
        padding: 12px;
        box-shadow: none;
    }
    div[data-testid="stTextInput"] input:focus {
        border-bottom: 2px solid #2459ff;
    }
    div[data-testid="stFormSubmitButton"] button {
        width: 100%;
        height: 52px;
        border-radius: 6px;
        border: none;
        background: #0d3cff;
        color: white;
        font-size: 20px;
        font-weight: bold;
    }
    div[data-testid="stFormSubmitButton"] button:hover {
        background: #002fc8;
    }
    </style>
    """, unsafe_allow_html=True)

    # 左右分栏
    left, right = st.columns([0.8, 1.2], gap="large")

    with left:
        st.image(img_path, width=407)   # 匹配原始图片尺寸

    with right:
        st.markdown('<div class="login-title">MES质量追溯系统</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-sub">Manufacturing Execution System</div>', unsafe_allow_html=True)

        with st.form("login_form"):
            username = st.text_input("用户名", placeholder="👤 请输入用户名", label_visibility="collapsed")
            password = st.text_input("密码", type="password", placeholder="🔒 请输入密码", label_visibility="collapsed")
            st.markdown('<div style="text-align:right; color:#888; font-size:15px;">忘记密码</div>', unsafe_allow_html=True)
            login = st.form_submit_button("登 录")

    if login:
        try:
            from config import LOGIN_USERNAME, LOGIN_PASSWORD
            valid = (username == LOGIN_USERNAME and password == LOGIN_PASSWORD)
        except ImportError:
            st.error("配置文件缺失，请联系管理员")
            return False
        if valid:
            st.session_state.authenticated = True
            st.session_state.username = username
            st.rerun()
        else:
            st.error("用户名或密码错误")

    return False

# ---------- 辅助函数 ----------
def get_available_dates(raw_dir):
    dates = []
    available_files = set()
    for ext in ["*.xlsx", "*.xls"]:
        for file in Path(raw_dir).glob(ext):
            name = file.stem.strip()
            try:
                d = datetime.strptime(name, "%Y%m%d").date()
                dates.append(d)
                available_files.add(name)
            except ValueError:
                continue
    dates.sort()
    return dates, available_files

def load_all_data(selected_dates):
    raw = load_raw(selected_dates, RAW_DIR)
    if raw.empty:
        return None, None, None, None, None, None

    code_to_cause, code_to_shop, cause_to_shop = load_rule(RULE_FILE)
    df = derive_columns(raw, code_to_cause, code_to_shop, cause_to_shop)

    corrections = load_corrections()
    if corrections:
        df = apply_corrections_to_df(df, corrections)

    waste_df = df[df["类型"] == "废品"]
    app_df = df[df["类型"] == "次品外观"]
    uf_df = df[df["类型"] == "次品UF"]
    repair_df = df[df["类型"] == "返修"]

    total_production = load_production(selected_dates, PRODUCTION_FILE) or 0
    daily_prod_dict = load_daily_production_dict(selected_dates, PRODUCTION_FILE)
    uf_check_data = load_uf_check_data(UF_DATA_DIR)

    return df, waste_df, app_df, uf_df, repair_df, total_production, daily_prod_dict, uf_check_data

# ---------- 综合看板 ----------
def render_dashboard(df, waste_df, app_df, uf_df, total_production, daily_prod_dict, selected_dates):
    waste_shop = waste_df["车间"].value_counts().reset_index()
    waste_shop.columns = ["车间", "数量"]
    app_shop = app_df["车间"].value_counts().reset_index()
    app_shop.columns = ["车间", "数量"]
    uf_mac = uf_df["成型"].value_counts().reset_index()
    uf_mac.columns = ["成型", "数量"]

    if total_production > 0:
        waste_rate = len(waste_df) / total_production
        app_rate = len(app_df) / total_production
        uf_rate = len(uf_df) / total_production
        bad_barcodes = set(waste_df["条码"].dropna()) | set(app_df["条码"].dropna()) | set(uf_df["条码"].dropna())
        qual_rate = 1 - len(bad_barcodes) / total_production
    else:
        waste_rate = app_rate = uf_rate = 0
        qual_rate = 1

    c1, c2, c3, c4 = st.columns(4)
    metrics = [
        ("废品数量", len(waste_df), waste_rate),
        ("次品外观", len(app_df), app_rate),
        ("UF次品", len(uf_df), uf_rate),
        ("综合合格率", f"{qual_rate:.2%}", f"产量：{total_production:,.0f}")
    ]
    for col, m in zip([c1, c2, c3, c4], metrics):
        with col:
            st.markdown(f"""<div class="metric-card"><div class="metric-title">{m[0]}</div><div class="metric-value">{m[1]}</div><div class="metric-rate">{'' if m[2] is None else f'{m[2]:.3%}' if isinstance(m[2], float) else m[2]}</div></div>""", unsafe_allow_html=True)

    st.divider()
    col_left, col_right = st.columns(2)

    fig1 = px.bar(waste_shop, x="车间", y="数量", text="数量", text_auto=True)
    col_left.plotly_chart(style_bar_chart(fig1, "废品车间分布"), use_container_width=True, key="tab1_waste_shop")

    fig2 = px.bar(app_shop, x="车间", y="数量", text="数量", text_auto=True)
    col_right.plotly_chart(style_bar_chart(fig2, "次品外观车间分布"), use_container_width=True, key="tab1_app_shop")

    fig3 = px.bar(uf_mac, x="成型", y="数量", text="数量", text_auto=True)
    st.plotly_chart(style_bar_chart(fig3, "UF次品成型机分布"), use_container_width=True, key="tab1_uf_mac")

    if len(selected_dates) > 1 and daily_prod_dict:
        daily_stats = []
        for d in sorted(selected_dates):
            day_data = df[df["文件日期"] == d]
            day_prod = daily_prod_dict.get(d, 0)
            if day_prod > 0:
                day_waste = len(day_data[day_data["类型"] == "废品"])
                day_app = len(day_data[day_data["类型"] == "次品外观"])
                day_uf = len(day_data[day_data["类型"] == "次品UF"])
                daily_stats.append({
                    "日期": pd.to_datetime(d, format='%Y%m%d').strftime('%m/%d'),
                    "废品率": day_waste / day_prod,
                    "外观次品率": day_app / day_prod,
                    "UF次品率": day_uf / day_prod,
                    "综合合格率": 1 - (day_waste + day_app + day_uf) / day_prod
                })
        if daily_stats:
            daily_stats_df = pd.DataFrame(daily_stats)
            st.subheader("废品率趋势")
            fig_waste = go.Figure()
            fig_waste.add_trace(go.Scatter(x=daily_stats_df["日期"], y=daily_stats_df["废品率"], mode='lines+markers+text', text=[f"{v:.4%}" for v in daily_stats_df["废品率"]], textposition='top center', line=dict(color='#1f77b4'), marker=dict(size=8)))
            fig_waste.add_hline(y=0.0006, line_dash="dot", line_color="red")
            fig_waste.update_layout(height=350, margin=dict(t=60, b=40), template="plotly_white")
            st.plotly_chart(fig_waste, use_container_width=True)

            st.subheader("综合合格率趋势")
            fig_qual = go.Figure()
            fig_qual.add_trace(go.Scatter(x=daily_stats_df["日期"], y=daily_stats_df["综合合格率"], mode='lines+markers+text', text=[f"{v:.2%}" for v in daily_stats_df["综合合格率"]], line=dict(color='green'), marker=dict(size=8)))
            fig_qual.add_hline(y=0.993, line_dash="dot", line_color="red")
            fig_qual.update_layout(height=350, margin=dict(t=60, b=40), template="plotly_white")
            st.plotly_chart(fig_qual, use_container_width=True)

            st.subheader("外观次品率及UF次品率趋势")
            fig_app_uf = go.Figure()
            fig_app_uf.add_trace(go.Scatter(x=daily_stats_df["日期"], y=daily_stats_df["外观次品率"], mode='lines+markers+text', name='外观次品率', line=dict(color='orange')))
            fig_app_uf.add_trace(go.Scatter(x=daily_stats_df["日期"], y=daily_stats_df["UF次品率"], mode='lines+markers+text', name='UF次品率', line=dict(color='purple')))
            fig_app_uf.update_layout(height=350, margin=dict(t=60, b=40), template="plotly_white")
            st.plotly_chart(fig_app_uf, use_container_width=True)

# ---------- 数据修正页 ----------
def render_correction_tab(df, selected_dates):
    st.subheader("🔧 数据修正（车间 / 病象）")
    st.caption("修改后点击「保存修正记录」持久化，点击「应用到源文件」会修改原始 Excel（请先备份）")

    corrections = load_corrections()
    df_corrected = apply_corrections_to_df(df, corrections)
    df_corrected = df_corrected[df_corrected["类型"].isin(["废品", "次品外观"])]

    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    with col_f1:
        shops = ["全部"] + sorted(df_corrected["车间"].dropna().unique().tolist())
        selected_shop = st.selectbox("车间", shops, key="corr_shop")
    with col_f2:
        causes = ["全部"] + sorted(df_corrected["病象"].dropna().unique().tolist())
        selected_cause = st.selectbox("病象", causes, key="corr_cause")
    with col_f3:
        machines = ["全部"] + sorted(df_corrected["成型"].dropna().unique().tolist())
        selected_machine = st.selectbox("成型机", machines, key="corr_machine")
    with col_f4:
        masters = ["全部"] + sorted(df_corrected["成型主手"].dropna().unique().tolist())
        selected_master = st.selectbox("成型主手", masters, key="corr_master")

    filtered = df_corrected.copy()
    if selected_shop != "全部":
        filtered = filtered[filtered["车间"] == selected_shop]
    if selected_cause != "全部":
        filtered = filtered[filtered["病象"] == selected_cause]
    if selected_machine != "全部":
        filtered = filtered[filtered["成型"] == selected_machine]
    if selected_master != "全部":
        filtered = filtered[filtered["成型主手"] == selected_master]

    display_cols = ["条码", "车间", "病象", "规格", "花纹", "成型", "成型主手", "硫化", "硫化主手", "硫化日期", "成型时间", "位置"]
    display_cols = [c for c in display_cols if c in filtered.columns]

    if filtered.empty:
        st.info("没有匹配的数据")
        return

    edited_df = st.data_editor(
        filtered[display_cols],
        column_config={
            "车间": st.column_config.SelectboxColumn("车间", options=["密炼", "部件", "部件成型", "成型", "硫化", "工程", "工艺"]),
            "病象": st.column_config.SelectboxColumn("病象", options=sorted(df_corrected["病象"].unique()))
        },
        hide_index=True,
        use_container_width=True,
        height=600,
        key="correction_editor"
    )

    original = filtered[display_cols].reset_index(drop=True)
    edited = edited_df.reset_index(drop=True)
    changed_mask = (original["车间"] != edited["车间"]) | (original["病象"] != edited["病象"])
    changed_rows = edited[changed_mask]

    if not changed_rows.empty:
        st.info(f"检测到 {len(changed_rows)} 行数据发生变化")
        if st.button("💾 保存修正记录"):
            new_corrections = {}
            for _, row in changed_rows.iterrows():
                barcode = str(row["条码"])
                new_corrections[barcode] = {"车间": row["车间"], "病象": row["病象"]}
            corrections.update(new_corrections)
            save_corrections(corrections)
            st.success("✅ 修正记录已保存！")
            st.rerun()
    else:
        st.success("✅ 当前数据与修正记录一致，无变更")

    if corrections:
        st.divider()
        st.subheader("📋 已保存的修正记录")
        corr_df = pd.DataFrame([{"条码": k, "修正车间": v.get("车间", ""), "修正病象": v.get("病象", "")} for k, v in corrections.items()])
        st.dataframe(corr_df, use_container_width=True, height=200)

        if st.button("⚠️ 应用到源文件（修改Excel）", type="primary"):
            if st.checkbox("我已备份数据，确认执行修改"):
                success = write_corrections_to_source(RAW_DIR, corrections, RULE_FILE)
                if success:
                    st.success("✅ 源文件已更新！")
                else:
                    st.error("应用失败，请检查日志")
    else:
        st.info("暂无修正记录")

# ---------- 主程序 ----------
def main():
    st.set_page_config(page_title="MES质量追溯系统", layout="wide", initial_sidebar_state="expanded")
    inject_css()

    if not check_password():
        st.stop()

    if AUTOREFRESH_AVAILABLE:
        st_autorefresh(interval=60000, key="auto_refresh")

    st.title("🏭 MES质量追溯系统")

    # 全局图片查看器
    if "selected_photo" in st.session_state:
        photo = st.session_state["selected_photo"]
        with st.expander(f"📸 条码：{photo['barcode']}", expanded=True):
            col1, col2 = st.columns([5, 1])
            with col1:
                st.image(photo["path"], use_container_width=True)
            with col2:
                if st.button("❌ 关闭", key="close_photo_btn"):
                    del st.session_state["selected_photo"]
                    st.rerun()

    # 侧边栏
    with st.sidebar:
        st.header("系统控制")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄刷新数据", use_container_width=True):
                st.cache_data.clear()
                st.cache_resource.clear()
                st.success("缓存已清除")
                st.rerun()
        with col2:
            st.caption(f"版本：{APP_VERSION}")
        st.divider()

        st.header("数据选择")
        available_dates, available_files = get_available_dates(RAW_DIR)
        if not available_dates:
            st.error("❌ raw_data 文件夹中没有找到有效的日期文件！")
            st.stop()

        default_start = available_dates[-1]
        default_end = available_dates[-1]

        date_range = st.date_input(
            "📅 选择日期区间",
            value=(default_start, default_end),
            min_value=available_dates[0],
            max_value=available_dates[-1],
            format="YYYY-MM-DD",
        )

        selected_dates = []
        if isinstance(date_range, tuple) and len(date_range) == 2:
            start_date, end_date = date_range
            d = start_date
            while d <= end_date:
                file_name = d.strftime("%Y%m%d")
                if file_name in available_files:
                    selected_dates.append(file_name)
                d += timedelta(days=1)
        else:
            file_name = date_range.strftime("%Y%m%d")
            if file_name in available_files:
                selected_dates.append(file_name)

        if not selected_dates:
            st.warning("所选区间内没有可用的数据文件")
            return

        st.write(f"📂 加载文件数：**{len(selected_dates)}** 天")
        st.write(f"📅 数据范围：**{min(selected_dates)} ～ {max(selected_dates)}**")
        prod_total = load_production(selected_dates, PRODUCTION_FILE)
        if prod_total is not None and prod_total > 0:
            st.metric("📦 总产量", f"{prod_total:,.0f}")
        else:
            st.caption("⚠️ 未找到产量数据")

        st.divider()
        st.write("规则文件")
        st.code(RULE_FILE)
        st.write("原始数据")
        st.code(RAW_DIR)
        st.write("照片库")
        st.code(PHOTO_BASE_DIR)

        st.divider()
        if "username" in st.session_state:
            st.caption(f"👤 当前用户：{st.session_state.username}")
        if st.button("🚪 退出登录", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.pop("username", None)
            st.rerun()

    # 加载数据
    with st.spinner("数据加载中..."):
        data = load_all_data(selected_dates)
        if data[0] is None or data[0].empty:
            st.error("无数据")
            return
        df, waste_df, app_df, uf_df, repair_df, total_production, daily_prod_dict, uf_check_data = data

    @st.cache_resource
    def get_photo_index():
        return build_photo_index(PHOTO_BASE_DIR)

    PHOTO_INDEX = get_photo_index()

    # 标签页
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "综合看板", "外观废次品分析", "UF次品",
        "成型/硫化人员分析", "返修分析", "Pareto分析", "数据修正"
    ])

    with tab1:
        render_dashboard(df, waste_df, app_df, uf_df, total_production, daily_prod_dict, selected_dates)

    with tab2:
        render_waste_appearance_analysis(
            combined_df=df[df["类型"].isin(["废品", "次品外观"])],
            photo_index=PHOTO_INDEX,
            waste_df=waste_df,
            app_df=app_df,
            df_full=df,
            selected_dates=selected_dates,
            shop_order_list=["密炼", "部件", "部件成型", "成型", "硫化", "工程", "工艺"]
        )

    with tab3:
        st.subheader("UF 次品分析")
        uf_mac_all = uf_df["成型"].value_counts().reset_index()
        uf_mac_all.columns = ["成型", "数量"]
        fig_uf = px.bar(uf_mac_all, x="成型", y="数量", text="数量", text_auto=True)
        st.plotly_chart(style_bar_chart(fig_uf, "UF次品成型机分布"), use_container_width=True, key="tab3_uf_mac")
        render_uf_detail_table(uf_df, uf_check_data, "uf_detail", height=680)

    with tab4:
        st.subheader("成型/硫化人员分析（不含返修）")
        df_waste_app = df[df["类型"].isin(["废品", "次品外观"])]
        render_master_ranking(df_waste_app)
        left_col, right_col = st.columns(2)
        with left_col:
            render_molding_analysis(df)
        with right_col:
            render_vulcanization_analysis(df)

    with tab5:
        st.subheader("返修分析")
        if not repair_df.empty:
            tire_code_col = find_col(repair_df, ["胎胚编码", "条码"])
            product_name_col = find_col(repair_df, ["成品名称", "规格"])
            repair_std = repair_df.rename(columns={
                tire_code_col: "胎胚编码",
                product_name_col: "成品名称",
                "成型": "成型机",
                "硫化": "硫化机",
                "病象": "返修缺陷"
            })
            if "文件日期" not in repair_std.columns:
                st.error("数据中缺少“文件日期”列")
            else:
                render_repair_table(repair_std, selected_dates=selected_dates if len(selected_dates)>1 else None, photo_index=None)
        else:
            st.info("无返修数据")

    with tab6:
        st.subheader("Pareto病象分析")
        fig, pareto_df = build_pareto_chart(df)
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(pareto_df, use_container_width=True, height=600)

    with tab7:
        render_correction_tab(df, selected_dates)

if __name__ == "__main__":
    main()