import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
from datetime import timedelta

# 自动刷新
try:
    from streamlit_autorefresh import st_autorefresh
    AUTOREFRESH_AVAILABLE = True
except ImportError:
    AUTOREFRESH_AVAILABLE = False

# 导入自定义模块
from config import RULE_FILE, RAW_DIR, PHOTO_BASE_DIR, PRODUCTION_FILE, UF_DATA_DIR, APP_VERSION
from modules.loader import (
    load_rule, load_raw, load_production, load_uf_check_data,
    load_daily_production_dict, derive_columns, get_all_dates
)
from modules.photo import build_photo_index, trigger_image_popup
from modules.charts import style_bar_chart
from modules.personnel import render_merged_person_table
from modules.repair import render_repair_table
from modules.pareto import build_pareto_chart
from modules.uf import render_uf_detail_table
from modules.detail import render_detail_table
from modules.detail import render_detail_table, render_summary_table, render_waste_appearance_analysis
from modules.statistics import render_machine_statistics

# ========== 登录验证函数 ==========
def check_password():
    """返回 True 如果用户已登录，否则显示登录表单并返回 False"""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if st.session_state.authenticated:
        return True

    # 登录表单样式
    st.markdown("""
    <style>
    .login-container {
        max-width: 420px;
        margin: 80px auto 0 auto;
        padding: 40px 32px 32px 32px;
        background: white;
        border-radius: 20px;
        box-shadow: 0 12px 40px rgba(0,0,0,0.12);
        border: 1px solid #e8ecf0;
    }
    .login-title {
        text-align: center;
        font-size: 28px;
        font-weight: 700;
        color: #0a2d6e;
        margin-bottom: 4px;
    }
    .login-sub {
        text-align: center;
        color: #64748b;
        font-size: 14px;
        margin-bottom: 28px;
    }
    .login-icon {
        text-align: center;
        font-size: 56px;
        margin-bottom: 8px;
    }
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div class="login-container">
            <div class="login-icon">🛞</div>
            <div class="login-title">MES质量追溯系统</div>
            <div class="login-sub">请输入账号和密码登录</div>
        """, unsafe_allow_html=True)

        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("👤 用户名", placeholder="请输入用户名", key="login_username")
            password = st.text_input("🔒 密码", type="password", placeholder="请输入密码", key="login_password")
            submitted = st.form_submit_button("🔐 登 录", use_container_width=True)

            if submitted:
                # 验证逻辑（从 config 读取或硬编码）
                try:
                    from config import LOGIN_USERNAME, LOGIN_PASSWORD
                    valid = (username == LOGIN_USERNAME and password == LOGIN_PASSWORD)
                except ImportError:
                    # 如果 config 中没有定义，使用硬编码
                    valid = (username == "QA" and password == "123123")

                if valid:
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.rerun()
                else:
                    st.error("❌ 用户名或密码错误，请重试")

        st.markdown("</div>", unsafe_allow_html=True)

    return False

# ========== 页面配置 ==========
st.set_page_config(
    page_title="MES质量追溯系统",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========== 全局样式（保持不变） ==========
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
.stTabs [data-baseweb="tab-list"] {
    position: fixed !important;
    top: 3.5rem;
    z-index: 9999;
    background: white;
    border-bottom: 2px solid #1976D2;
    padding-top: 5px; padding-bottom: 5px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    width: calc(100% - 2rem);
    left: 1rem; right: 1rem;
}
.stTabs [data-baseweb="tab"] {
    font-size: 26px !important; font-weight: 800 !important;
    height: 65px;
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
    left: auto !important; right: auto !important;
    box-shadow: none !important;
    border-bottom: 2px solid #EEE !important;
    margin-top: 0 !important;
    padding-top: 0 !important; padding-bottom: 0 !important;
    z-index: auto !important;
    background: transparent;
}
.stTabs .stTabs [role="tabpanel"] {
    padding-top: 0 !important;
}
.stTabs .stTabs [data-baseweb="tab"] {
    font-size: 20px !important;
    height: 50px !important;
}
.merged-repair-table td, .merged-repair-table th {
    text-align: center !important;
    vertical-align: middle !important;
    padding: 6px 3px !important;
    border: 1px solid #ddd !important;
    font-size: 14px !important;
    font-weight: 500 !important;
}
.merged-repair-table th {
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

# ========== 图片索引 ==========
PHOTO_INDEX = build_photo_index(PHOTO_BASE_DIR)

# ========== 主程序 ==========
def main():
    # ===== 新增：登录验证（必须放在最前面） =====
    if not check_password():
        st.stop()   # 阻止后续代码执行

    if AUTOREFRESH_AVAILABLE:
        st_autorefresh(interval=60000, key="auto_refresh")

    st.title("🏭 MES质量追溯系统")
    code_to_cause, code_to_shop, cause_to_shop = load_rule(RULE_FILE)
    all_dates = get_all_dates(RAW_DIR)

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
        selected_dates = st.multiselect("选择分析日期", all_dates, default=all_dates[:1] if all_dates else [])

        total_production = 0
        daily_prod_dict = {}
        if selected_dates:
            auto_prod = load_production(selected_dates, PRODUCTION_FILE)
            if auto_prod is not None:
                total_production = auto_prod
                daily_prod_dict = load_daily_production_dict(selected_dates, PRODUCTION_FILE)
                st.metric("硫化产量（自动提取）", f"{total_production:,.0f}")
            else:
                st.warning("自动提取失败，请手动上传产量文件")
        else:
            st.warning("请选择日期")

        st.divider()
        st.write("规则文件")
        st.code(RULE_FILE)
        st.write("原始数据")
        st.code(RAW_DIR)
        st.write("照片库")
        st.code(PHOTO_BASE_DIR)

        # ===== 新增：退出登录按钮（放在侧边栏底部） =====
        st.divider()
        if "username" in st.session_state:
            st.caption(f"👤 当前用户：{st.session_state.username}")
        if st.button("🚪 退出登录", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.pop("username", None)
            st.rerun()

    if not selected_dates:
        st.warning("请选择日期")
        return

    raw = load_raw(selected_dates, RAW_DIR)
    if raw.empty:
        st.error("无数据")
        return

    df = derive_columns(raw, code_to_cause, code_to_shop, cause_to_shop)

    waste_df = df[df["类型"] == "废品"]
    app_df = df[df["类型"] == "次品外观"]
    uf_df = df[df["类型"] == "次品UF"]
    repair_df = df[df["类型"] == "返修"]

    waste_shop = waste_df["车间"].value_counts().reset_index()
    waste_shop.columns = ["车间", "数量"]
    app_shop = app_df["车间"].value_counts().reset_index()
    app_shop.columns = ["车间", "数量"]
    uf_mac = uf_df["成型"].value_counts().reset_index()
    uf_mac.columns = ["成型", "数量"]

    uf_check_data = load_uf_check_data(UF_DATA_DIR)

    if total_production > 0:
        waste_rate = len(waste_df) / total_production
        app_rate = len(app_df) / total_production
        uf_rate = len(uf_df) / total_production
        bad_barcodes = set()
        for temp_df in [waste_df, app_df, uf_df]:
            if "条码" in temp_df.columns:
                bad_barcodes.update(temp_df["条码"].dropna().astype(str).tolist())
        bad_count = len(bad_barcodes)
        qual_rate = 1 - bad_count / total_production
    else:
        waste_rate = app_rate = uf_rate = 0
        qual_rate = 1

    # 趋势数据
    daily_stats = None
    if len(selected_dates) > 1 and daily_prod_dict:
        daily_list = []
        for d in sorted(selected_dates):
            day_data = df[df["文件日期"] == d]
            day_prod = daily_prod_dict.get(d, 0)
            if day_prod > 0:
                day_waste = len(day_data[day_data["类型"] == "废品"])
                day_app = len(day_data[day_data["类型"] == "次品外观"])
                day_uf = len(day_data[day_data["类型"] == "次品UF"])
                daily_list.append({
                    "日期": pd.to_datetime(d, format='%Y%m%d').strftime('%m/%d'),
                    "废品率": day_waste / day_prod,
                    "外观次品率": day_app / day_prod,
                    "UF次品率": day_uf / day_prod,
                    "综合合格率": 1 - (day_waste + day_app + day_uf) / day_prod
                })
        if daily_list:
            daily_stats = pd.DataFrame(daily_list)

    # ========== 标签页 ==========
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "综合看板", "外观废次品分析", "UF次品", "成型/硫化人员分析", "返修分析", "Pareto分析"
    ])

    # ---------- 综合看板 ----------
    with tab1:
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
        col_left.plotly_chart(style_bar_chart(fig1, "废品车间分布"), width='stretch', key="tab1_waste_shop")

        fig2 = px.bar(app_shop, x="车间", y="数量", text="数量", text_auto=True)
        col_right.plotly_chart(style_bar_chart(fig2, "次品外观车间分布"), width='stretch', key="tab1_app_shop")

        fig3 = px.bar(uf_mac, x="成型", y="数量", text="数量", text_auto=True)
        st.plotly_chart(style_bar_chart(fig3, "UF次品成型机分布"), width='stretch', key="tab1_uf_mac")

        if daily_stats is not None and not daily_stats.empty:
            # 废品率趋势
            st.subheader("废品率趋势")
            target_waste = 0.0006
            fig_waste = go.Figure()
            colors = ['red' if v > target_waste else '#1f77b4' for v in daily_stats["废品率"]]
            fig_waste.add_trace(go.Scatter(
                x=daily_stats["日期"], y=daily_stats["废品率"],
                mode='lines+markers+text',
                text=[f"{v:.4%}" for v in daily_stats["废品率"]],
                textposition='top center',
                textfont=dict(size=15, color='black', family='Microsoft YaHei'),
                line=dict(color='#1f77b4', width=2),
                marker=dict(size=8, color=colors, line=dict(width=0.75, color='white')),
            ))
            fig_waste.add_hline(y=target_waste, line_dash="dot", line_color="red",
                                annotation_text="目标0.06%", annotation_position="bottom right")
            fig_waste.update_layout(
                template="plotly_white", title="废品率趋势",
                xaxis=dict(title=None, showline=True, linecolor='gray', tickfont=dict(family='Microsoft YaHei')),
                yaxis=dict(title="废品率", tickformat='.2%', range=[0, 0.0015], showline=True, linecolor='gray', tickfont=dict(family='Microsoft YaHei')),
                showlegend=False, height=350, margin=dict(t=60, b=40, l=40, r=20)
            )
            st.plotly_chart(fig_waste, width='stretch', key="waste_trend")

            # 综合合格率趋势
            st.subheader("综合合格率趋势")
            target_qual = 0.993
            fig_qual = go.Figure()
            fig_qual.add_trace(go.Scatter(
                x=daily_stats["日期"], y=daily_stats["综合合格率"],
                mode='lines+markers+text',
                text=[f"{v:.2%}" for v in daily_stats["综合合格率"]],
                textposition='top center',
                textfont=dict(size=15, color='black', family='Microsoft YaHei'),
                line=dict(color='green', width=2),
                marker=dict(size=8, color='green', line=dict(width=0.75, color='white')),
            ))
            fig_qual.add_hline(y=target_qual, line_dash="dot", line_color="red",
                               annotation_text="目标99.3%", annotation_position="bottom right")
            fig_qual.update_layout(
                template="plotly_white", title="综合合格率趋势",
                xaxis=dict(title=None, showline=True, linecolor='gray', tickfont=dict(family='Microsoft YaHei')),
                yaxis=dict(title="合格率", tickformat='.2%', range=[0.99, 1.0], showline=True, linecolor='gray', tickfont=dict(family='Microsoft YaHei')),
                showlegend=False, height=350, margin=dict(t=60, b=40, l=40, r=20)
            )
            st.plotly_chart(fig_qual, width='stretch', key="qual_trend")

            # 外观次品率及UF次品率趋势
            st.subheader("外观次品率及UF次品率趋势")
            fig_app_uf = go.Figure()
            fig_app_uf.add_trace(go.Scatter(
                x=daily_stats["日期"], y=daily_stats["外观次品率"],
                mode='lines+markers+text', name='外观次品率',
                text=[f"{v:.4%}" for v in daily_stats["外观次品率"]],
                textposition='top center',
                textfont=dict(size=15, color='black', family='Microsoft YaHei'),
                line=dict(color='orange', width=2),
                marker=dict(size=8, line=dict(width=0.75, color='white')),
            ))
            fig_app_uf.add_trace(go.Scatter(
                x=daily_stats["日期"], y=daily_stats["UF次品率"],
                mode='lines+markers+text', name='UF次品率',
                text=[f"{v:.4%}" for v in daily_stats["UF次品率"]],
                textposition='top center',
                textfont=dict(size=15, color='black', family='Microsoft YaHei'),
                line=dict(color='purple', width=2),
                marker=dict(size=8, line=dict(width=0.75, color='white')),
            ))
            fig_app_uf.update_layout(
                template="plotly_white", title="外观次品率及UF次品率趋势",
                xaxis=dict(title=None, showline=True, linecolor='gray', tickfont=dict(family='Microsoft YaHei')),
                yaxis=dict(title="比率", tickformat='.2%', range=[0.0002, 0.006], showline=True, linecolor='gray', tickfont=dict(family='Microsoft YaHei')),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, font=dict(family='Microsoft YaHei')),
                height=350, margin=dict(t=60, b=40, l=40, r=20)
            )
            st.plotly_chart(fig_app_uf, width='stretch', key="app_uf_trend")

    # ---------- 外观废次品分析 ----------
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

    # ---------- UF次品 ----------
    with tab3:
        st.subheader("UF 次品分析")
        uf_mac_all = uf_df["成型"].value_counts().reset_index()
        uf_mac_all.columns = ["成型", "数量"]
        fig_uf = px.bar(uf_mac_all, x="成型", y="数量", text="数量", text_auto=True)
        st.plotly_chart(style_bar_chart(fig_uf, "UF次品成型机分布"), width='stretch', key="tab3_uf_mac")
        render_uf_detail_table(uf_df, uf_check_data, "uf_detail", height=680)

    # ---------- 成型/硫化人员分析 ----------
    with tab4:
        st.subheader("成型/硫化人员分析（不含返修）")
        left_col, right_col = st.columns(2)

        with left_col:
            # 直接调用封装好的成型分析函数
            from modules.personnel import render_molding_analysis
            render_molding_analysis(df)

        with right_col:
            # 直接调用封装好的硫化分析函数
            from modules.personnel import render_vulcanization_analysis
            render_vulcanization_analysis(df)

    # ==================== 返修分析 ====================
    with tab5:
        st.subheader("返修分析")
        if not repair_df.empty:
            # 准备数据（列名映射）
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
                st.error("数据中缺少“文件日期”列")
            else:
                # 所有 UI 由子模块内部绘制
                render_repair_table(
                    repair_std,
                    selected_dates=selected_dates if len(selected_dates) > 1 else None,
                    photo_index=PHOTO_INDEX
                )
        else:
            st.info("无返修数据")

    # ---------- Pareto分析 ----------
    with tab6:
        st.subheader("Pareto病象分析")
        fig, pareto_df = build_pareto_chart(df)
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(pareto_df, use_container_width=True, height=600)

if __name__ == "__main__":
    main()