import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import re
from datetime import timedelta
from PIL import Image

# 尝试导入自动刷新，若未安装则跳过
try:
    from streamlit_autorefresh import st_autorefresh
    AUTOREFRESH_AVAILABLE = True
except ImportError:
    AUTOREFRESH_AVAILABLE = False

# =====================================================
# 自定义模块导入
# =====================================================
from modules.loader import (
    load_rule,
    load_raw,
    load_production,
    load_uf_check_data,
    extract_single_daily_production,
    load_daily_production_dict
)

from modules.photo import (
    build_photo_index,
    trigger_image_popup
)

from modules.charts import style_bar_chart

from modules.personnel import render_merged_person_table

from modules.repair import render_repair_table

from modules.pareto import build_pareto_chart

from modules.uf import render_uf_detail_table

# =====================================================
# 页面配置
# =====================================================
st.set_page_config(
    page_title="MES质量追溯系统",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =====================================================
# 全局字体微软雅黑 + 表格缩放放大 (1.3倍)
# =====================================================
st.markdown("""
<style>
/* 全局强制微软雅黑 */
* {
    font-family: 'Microsoft YaHei', sans-serif !important;
}
html, body, [class*="css"], .stApp, .stMarkdown, .stText, .stDataFrame, .stTable, .stSelectbox, .stMultiSelect, .stRadio, .stCheckbox, .stButton, .stDownloadButton, .stTabs, .stTab, .stCaption, .stMetric, .stHeader, .stSubheader, .stTitle, .stPlotlyChart {
    font-family: 'Microsoft YaHei', sans-serif !important;
}
/* 表格内部文字强制 */
table, th, td, tr, thead, tbody, tfoot, caption {
    font-family: 'Microsoft YaHei', sans-serif !important;
}
/* 标题 */
h1 {
    margin-top: 0 !important;
    margin-bottom: 0.2rem !important;
    padding-top: 0 !important;
    padding-bottom: 0 !important;
    font-size: 32px !important;
    font-weight: 800 !important;
}
.block-container {
    padding-top: 0.5rem !important;
}
section.main > div {
    padding-top: 0rem !important;
}

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

/* 表格缩放：放大1.3倍 */
[data-testid="stDataFrameGlideDataEditor"] {
    zoom: 1.5;
}
[data-testid="stDataEditor"] {
    zoom: 1.5;
}

/* 普通表格样式 */
table {
    text-align: center !important;
    border-collapse: collapse;
}
th {
    background-color: #f0f2f6 !important;
    font-weight: 700;
    padding: 14px 6px !important;
    font-size: 24px;
}
td {
    padding: 14px 6px !important;
    font-size: 36px !important;
    font-weight: 700;
    border-bottom: 1px solid #e0e0e0;
    line-height: 1.6;
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
    padding-top: 130px !important;
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

/* 返修分析专用合并表格（动态列宽） */
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

/* 人员分析合并表格样式 */
.merged-table td, .merged-table th {
    text-align: center !important;
    vertical-align: middle !important;
    padding: 10px 6px !important;
    border: 1px solid #ddd !important;
    font-size: 16px !important;   /* 缩小字体 */
    font-weight: 600 !important;
}
.merged-table th {
    background-color: #f0f2f6 !important;
    font-weight: 700 !important;
    position: -webkit-sticky;
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

# =====================================================
# 路径常量
# =====================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RULE_FILE = os.path.join(BASE_DIR, "data", "0.rule.xlsx")
RAW_DIR = os.path.join(BASE_DIR, "data", "raw_data")
PHOTO_BASE_DIR = os.path.join(BASE_DIR, "data", "photos")
PRODUCTION_FILE = os.path.join(BASE_DIR, "data", "production", "production.xls")
UF_DATA_DIR = os.path.join(BASE_DIR, "data", "uf_check")

# =====================================================
# 工具函数（可保留在 app.py 或移至 utils.py）
# =====================================================
def full_to_half(text):
    if pd.isna(text): return ""
    s = str(text).strip()
    full = '０１２３４５６７８９'
    half = '0123456789'
    trans = str.maketrans(full, half)
    s = s.translate(trans)
    s = s.replace('\u3000', '').strip()
    return s

def clean_str(x):
    if pd.isna(x): return ""
    s = str(x).strip()
    s = s.replace("　", " ")
    s = re.sub(r"[\n\r\t]", "", s)
    return s

def find_col(df, candidates):
    cols = [clean_str(c) for c in df.columns]
    for cand in candidates:
        cand = clean_str(cand)
        for i, real in enumerate(cols):
            if cand == real:
                return df.columns[i]
    return None

def extract_chinese(text):
    if pd.isna(text): return ""
    chinese = re.findall(r'[\u4e00-\u9fff]+', str(text))
    return ' '.join(chinese) if chinese else str(text)

def short_name(text):
    if pd.isna(text): return ""
    s = str(text).strip()
    return s[-3:] if len(s) >= 3 else s

# =====================================================
# 派生字段（数据处理，可保留在此或独立模块）
# =====================================================
def derive_columns(df, code_to_cause, code_to_shop, cause_to_shop):
    df = df.copy()
    col_detect = find_col(df, ["检测分类", "分类"])
    col_reason = find_col(df, ["溯源原因简码", "原因简码", "简码", "原因代码"])
    col_r = find_col(df, ["检测原因"])
    col_u = find_col(df, ["缺陷原因"])
    col_build = find_col(df, ["成型机台", "成型设备", "机台"])
    col_vul = find_col(df, ["硫化日期", "日期"])

    df["成型"] = df[col_build] if col_build else "未知"
    df["类型"] = "其他"
    if col_detect:
        df.loc[df[col_detect].astype(str).str.strip() == "废品", "类型"] = "废品"
        df.loc[df[col_detect].astype(str).str.strip() == "返修", "类型"] = "返修"
    if col_reason:
        df.loc[df[col_reason].astype(str).str.strip() == "MBA", "类型"] = "次品外观"
        df.loc[df[col_reason].astype(str).str.strip() == "MBB", "类型"] = "次品UF"

    causes, shops = [], []
    for _, row in df.iterrows():
        code = clean_str(row[col_u]) if col_u else ""
        r = clean_str(row[col_r]) if col_r else ""
        if code in code_to_cause:
            causes.append(code_to_cause[code])
            shops.append(code_to_shop.get(code, "未知"))
        else:
            causes.append(r)
            shops.append(cause_to_shop.get(r, "未知"))
    df["病象"] = causes
    df["车间"] = shops

    if col_vul:
        df["硫化日期"] = pd.to_datetime(df[col_vul], errors="coerce")
        df["统计日期"] = df["硫化日期"].apply(
            lambda x: (x - timedelta(days=1)).date() if pd.notna(x) and x.hour < 8 else x.date() if pd.notna(x) else None
        )

    rename_map = {
        "模具位置":"位置", "上下模":"位置", "硫化机台":"硫化",
        "成型主手":"成型主手", "花纹":"花纹", "规格":"规格",
        "成型时间":"成型时间", "硫化人":"硫化主手", "条码":"条码"
    }
    for old, new in rename_map.items():
        if old in df.columns:
            df.rename(columns={old: new}, inplace=True)

    if "条码" in df.columns:
        df["条码"] = df["条码"].apply(full_to_half)

    if "位置" in df.columns:
        df["位置"] = df["位置"].apply(extract_chinese)

    if "成型" in df.columns:
        df["成型"] = df["成型"].apply(short_name)
    if "硫化" in df.columns:
        df["硫化"] = df["硫化"].apply(short_name)

    return df

# =====================================================
# 图片索引（全局初始化）
# =====================================================
PHOTO_INDEX = build_photo_index(PHOTO_BASE_DIR)

# =====================================================
# 版本号
# =====================================================
APP_VERSION = "20260609_001"

# =====================================================
# 主程序
# =====================================================
def main():
    # 自动刷新（若可用）
    if AUTOREFRESH_AVAILABLE:
        st_autorefresh(interval=60000, key="auto_refresh")

    st.title("🏭 MES质量追溯系统")

    # 加载规则
    code_to_cause, code_to_shop, cause_to_shop = load_rule(RULE_FILE)
    all_dates = get_all_dates()

    with st.sidebar:
        # 系统控制与刷新按钮
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

    if not selected_dates:
        st.warning("请选择日期")
        return

    # 加载原始数据
    raw = load_raw(selected_dates, RAW_DIR)
    if raw.empty:
        st.error("无数据")
        return

    # 派生字段
    df = derive_columns(raw, code_to_cause, code_to_shop, cause_to_shop)

    # 分类
    waste_df = df[df["类型"] == "废品"]
    app_df = df[df["类型"] == "次品外观"]
    uf_df = df[df["类型"] == "次品UF"]
    repair_df = df[df["类型"] == "返修"]

    # 预聚合
    waste_shop = waste_df["车间"].value_counts().reset_index()
    waste_shop.columns = ["车间", "数量"]
    app_shop = app_df["车间"].value_counts().reset_index()
    app_shop.columns = ["车间", "数量"]
    uf_mac = uf_df["成型"].value_counts().reset_index()
    uf_mac.columns = ["成型", "数量"]

    # UF检查数据
    uf_check_data = load_uf_check_data(UF_DATA_DIR)

    # 合格率计算（去重条码）
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

    # ========== 标签页定义 ==========
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "综合看板", "外观废次品分析", "UF次品", "成型/硫化人员分析", "返修分析", "Pareto分析"
    ])

    # ========== 综合看板 ==========
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
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">{m[0]}</div>
                    <div class="metric-value">{m[1]}</div>
                    <div class="metric-rate">{'' if m[2] is None else f'{m[2]:.3%}' if isinstance(m[2], float) else m[2]}</div>
                </div>""", unsafe_allow_html=True)

        st.divider()
        col_left, col_right = st.columns(2)

        fig1 = px.bar(waste_shop, x="车间", y="数量", text="数量", text_auto=True)
        col_left.plotly_chart(style_bar_chart(fig1, "废品车间分布"), width='stretch', key="tab1_waste_shop")

        fig2 = px.bar(app_shop, x="车间", y="数量", text="数量", text_auto=True)
        col_right.plotly_chart(style_bar_chart(fig2, "次品外观车间分布"), width='stretch', key="tab1_app_shop")

        fig3 = px.bar(uf_mac, x="成型", y="数量", text="数量", text_auto=True)
        st.plotly_chart(style_bar_chart(fig3, "UF次品成型机分布"), width='stretch', key="tab1_uf_mac")

        if daily_stats is not None and not daily_stats.empty:
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

    # ========== 外观废次品分析 ==========
    with tab2:
        st.subheader("外观废次品分析")
        combined = df[df["类型"].isin(["废品", "次品外观"])]

        type_order = {"废品": 0, "次品外观": 1}
        combined["类型排序"] = combined["类型"].map(type_order)
        shop_order_list = ["密炼", "部件", "部件成型", "成型", "硫化", "工程", "工艺"]
        combined["车间排序"] = combined["车间"].apply(lambda x: shop_order_list.index(x) if x in shop_order_list else 99)
        combined = combined.sort_values(["类型排序", "车间排序", "病象", "成型", "规格"])
        combined.drop(columns=["类型排序", "车间排序"], inplace=True)

        summary = combined.groupby(["病象", "车间"]).agg(
            总数=("类型", "count"),
            废品=("类型", lambda x: (x == "废品").sum()),
            次品=("类型", lambda x: (x == "次品外观").sum())
        ).reset_index()
        summary = summary[["病象", "总数", "废品", "次品", "车间"]].sort_values("总数", ascending=False)

        col_left, col_right = st.columns([1, 1.3])
        with col_left:
            st.caption("单击行查看该病象/车间的条码明细")
            event_summary = st.dataframe(
                summary,
                width='stretch',
                height=680,
                hide_index=True,
                selection_mode="single-row",
                on_select="rerun",
                key="summary_table"
            )
        with col_right:
            if event_summary.selection.rows:
                selected_row = event_summary.selection.rows[0]
                selected_data = summary.iloc[selected_row]
                selected_cause = selected_data["病象"]
                selected_shop = selected_data["车间"]
                detail = combined[(combined["病象"] == selected_cause) & (combined["车间"] == selected_shop)]
                if not detail.empty:
                    detail_cols = ["条码", "类型", "成型", "硫化", "规格", "花纹", "成型主手", "硫化主手"]
                    detail_cols = [c for c in detail_cols if c in detail.columns]
                    st.markdown(f"**{selected_cause}（{selected_shop}）的明细**")
                    event_detail = st.dataframe(
                        detail[detail_cols],
                        width='stretch',
                        height=680,
                        hide_index=True,
                        selection_mode="single-row",
                        on_select="rerun",
                        key=f"detail_summary_{selected_row}"
                    )
                    if event_detail.selection.rows:
                        detail_row = event_detail.selection.rows[0]
                        barcode = str(detail.iloc[detail_row]["条码"])
                        file_date = str(detail.iloc[detail_row]["文件日期"])
                        trigger_image_popup(barcode, PHOTO_INDEX)
                else:
                    st.info("无明细数据")
            else:
                st.info("请单击左侧表格的行查看明细")

        st.divider()
        waste_type = st.radio("选择明细类型", ["全选", "废品", "外观次品"], horizontal=True)
        if waste_type == "全选":
            render_detail_table(combined, "all_detail", height=680, enable_click=False)
        elif waste_type == "废品":
            render_detail_table(waste_df, "waste_detail", height=680, enable_click=True)
        else:
            render_detail_table(app_df, "app_detail", height=680, enable_click=True)

        # 机台统计
        st.divider()
        st.subheader("机台统计")

        stat_type = st.radio("统计类型", ["日期统计", "病象统计"], horizontal=True, key="stat_type")
        dimension = st.radio("统计维度", ["全部", "成型", "硫化"], horizontal=True, key="machine_dimension")

        if dimension == "硫化":
            base_data = df[(df["车间"] == "硫化") & (df["类型"].isin(["废品", "次品外观"]))]
            group_col = "硫化"
        else:
            if dimension == "成型":
                base_data = df[((df["车间"] == "成型") | (df["类型"] == "次品UF")) & (df["类型"].isin(["废品", "次品外观", "次品UF"]))]
            else:
                base_data = df[df["类型"].isin(["废品", "次品外观", "次品UF"])]
            group_col = "成型"

        col1, col2, col3 = st.columns(3)
        with col1:
            type_filter = st.selectbox("类型", ["全部", "废品", "次品", "UF次品"], key="machine_date_type")
        with col2:
            available_shops = base_data["车间"].dropna().unique().tolist()
            sorted_shop_options = ["全部"] + [s for s in shop_order_list if s in available_shops] + [s for s in available_shops if s not in shop_order_list]
            selected_shop_machine = st.selectbox("🏭 车间", sorted_shop_options, key="machine_date_shop")
        with col3:
            filtered_temp = base_data.copy()
            if type_filter == "废品":
                filtered_temp = filtered_temp[filtered_temp["类型"] == "废品"]
            elif type_filter == "次品":
                filtered_temp = filtered_temp[filtered_temp["类型"] == "次品外观"]
            elif type_filter == "UF次品":
                filtered_temp = filtered_temp[filtered_temp["类型"] == "次品UF"]
            if selected_shop_machine != "全部":
                filtered_temp = filtered_temp[filtered_temp["车间"] == selected_shop_machine]
            defect_options = ["全部"] + sorted(filtered_temp["病象"].dropna().unique().tolist())
            selected_defect = st.selectbox("🔍 缺陷", defect_options, key="machine_date_defect")

        if type_filter == "废品":
            base_data = base_data[base_data["类型"] == "废品"]
        elif type_filter == "次品":
            base_data = base_data[base_data["类型"] == "次品外观"]
        elif type_filter == "UF次品":
            base_data = base_data[base_data["类型"] == "次品UF"]
        if selected_shop_machine != "全部":
            base_data = base_data[base_data["车间"] == selected_shop_machine]
        if selected_defect != "全部":
            base_data = base_data[base_data["病象"] == selected_defect]

        if not base_data.empty:
            if stat_type == "日期统计":
                if selected_dates:
                    pivot = base_data.groupby([group_col, "文件日期"]).size().unstack(fill_value=0)
                    sorted_dates = sorted(selected_dates)
                    date_columns = [d for d in sorted_dates if d in pivot.columns]
                    if not date_columns:
                        date_columns = sorted(pivot.columns.tolist())
                    pivot = pivot[date_columns]
                    pivot.insert(0, "合计", pivot.sum(axis=1))
                    rename_dates = {d: pd.to_datetime(d, format='%Y%m%d').strftime('%m/%d') for d in date_columns}
                    pivot.rename(columns=rename_dates, inplace=True)
                    pivot = pivot.reset_index()
                    pivot = pivot.sort_values("合计", ascending=False)
                    st.data_editor(
                        pivot, disabled=True, use_container_width=True, height=680, hide_index=True, key="machine_date_editor"
                    )
                else:
                    st.info("请至少选择一个日期")
            else:
                pivot = base_data.groupby([group_col, "病象"]).size().unstack(fill_value=0)
                pivot["合计"] = pivot.sum(axis=1)
                pivot = pivot.sort_values("合计", ascending=False)
                cols = ["合计"] + [c for c in pivot.columns if c != "合计"]
                pivot = pivot[cols]
                pivot = pivot.reset_index()
                st.data_editor(
                    pivot, disabled=True, use_container_width=True, height=680, hide_index=True, key="machine_cause_editor"
                )
        else:
            st.info("无数据")

    # ========== UF次品 ==========
    with tab3:
        st.subheader("UF 次品分析")
        uf_mac_all = uf_df["成型"].value_counts().reset_index()
        uf_mac_all.columns = ["成型", "数量"]
        fig_uf = px.bar(uf_mac_all, x="成型", y="数量", text="数量", text_auto=True)
        st.plotly_chart(style_bar_chart(fig_uf, "UF次品成型机分布"), width='stretch', key="tab3_uf_mac")

        render_uf_detail_table(uf_df, uf_check_data, "uf_detail", height=680)

    # ========== 成型/硫化人员分析 ==========
    with tab4:
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
                person_detail = person_detail.sort_values(["合计", "成型主手", "类型", "病象"],
                                                          ascending=[False, True, True, True])
                html = render_merged_person_table(person_detail, "成型主手", extra_col=extra)
                if html:
                    st.markdown(html, unsafe_allow_html=True)
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
                person_detail = person_detail.sort_values(["合计", "硫化主手", "类型", "病象"],
                                                          ascending=[False, True, True, True])
                html = render_merged_person_table(person_detail, "硫化主手", extra_col=extra)
                if html:
                    st.markdown(html, unsafe_allow_html=True)
            else:
                st.info("无硫化数据（废品/次品外观）")

    # ========== 返修分析 ==========
    with tab5:
        st.subheader("返修分析")
        if not repair_df.empty:
            # 统一列名
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
                return

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

    # ========== Pareto分析 ==========
    with tab6:
        st.subheader("Pareto病象分析")
        fig, pareto_df = build_pareto_chart(df)
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(pareto_df, use_container_width=True, height=600)

# =====================================================
# 通用明细表函数（保留在主程序中，因为它与多个Tab交互）
# =====================================================
def render_detail_table(df, key_prefix, height=680, enable_click=True):
    if df.empty:
        st.info("无数据")
        return

    shop_order = ["密炼", "部件", "部件成型", "成型", "硫化", "工程", "工艺"]
    all_shops = df["车间"].dropna().astype(str).unique().tolist()
    sorted_shops = [s for s in shop_order if s in all_shops] + sorted([s for s in all_shops if s not in shop_order])
    shops = ["全部"] + sorted_shops

    causes = ["全部"] + sorted(df["病象"].dropna().astype(str).unique().tolist())
    machines = ["全部"] + sorted(df["成型"].dropna().astype(str).unique().tolist())
    masters = ["全部"] + sorted(df["成型主手"].dropna().astype(str).unique().tolist())
    vul_machines = ["全部"] + sorted(df["硫化"].dropna().astype(str).unique().tolist())
    vul_workers = ["全部"] + sorted(df["硫化主手"].dropna().astype(str).unique().tolist())

    cols = st.columns(6)
    with cols[0]:
        selected_shop = st.selectbox("🏭 车间", shops, key=f"shop_{key_prefix}")
    with cols[1]:
        selected_cause = st.selectbox("🔍 病象", causes, key=f"cause_{key_prefix}")
    with cols[2]:
        selected_machine = st.selectbox("⚙️ 成型", machines, key=f"machine_{key_prefix}")
    with cols[3]:
        selected_master = st.selectbox("👤 成型主手", masters, key=f"master_{key_prefix}")
    with cols[4]:
        selected_vul_machine = st.selectbox("🔥 硫化", vul_machines, key=f"vul_machine_{key_prefix}")
    with cols[5]:
        selected_vul_worker = st.selectbox("👨‍🏭 硫化主手", vul_workers, key=f"vul_worker_{key_prefix}")

    filtered_df = df.copy()
    if selected_shop != "全部":
        filtered_df = filtered_df[filtered_df["车间"] == selected_shop]
    if selected_cause != "全部":
        filtered_df = filtered_df[filtered_df["病象"] == selected_cause]
    if selected_machine != "全部":
        filtered_df = filtered_df[filtered_df["成型"] == selected_machine]
    if selected_master != "全部":
        filtered_df = filtered_df[filtered_df["成型主手"] == selected_master]
    if selected_vul_machine != "全部":
        filtered_df = filtered_df[filtered_df["硫化"] == selected_vul_machine]
    if selected_vul_worker != "全部":
        filtered_df = filtered_df[filtered_df["硫化主手"] == selected_vul_worker]

    if filtered_df.empty:
        st.warning("无符合条件的数据")
        return

    show_cols = ["病象", "条码", "硫化", "硫化主手", "硫化日期",
                 "成型", "成型时间", "成型主手", "规格", "花纹", "位置", "车间"]
    show_cols = [c for c in show_cols if c in filtered_df.columns]

    st.markdown("<div class='table-header'>📋 明细数据</div>", unsafe_allow_html=True)

    if enable_click:
        event = st.dataframe(
            filtered_df[show_cols],
            width='stretch',
            height=height,
            hide_index=True,
            selection_mode="single-row",
            on_select="rerun",
            key=f"detail_table_{key_prefix}"
        )
        if event.selection.rows:
            selected_row = event.selection.rows[0]
            barcode = str(filtered_df.iloc[selected_row]["条码"])
            file_date = str(filtered_df.iloc[selected_row]["文件日期"])
            trigger_image_popup(barcode, PHOTO_INDEX)
    else:
        st.dataframe(
            filtered_df[show_cols],
            width='stretch',
            height=height,
            hide_index=True,
            key=f"detail_table_{key_prefix}"
        )

# 获取日期列表函数（保留在主程序中）
def get_all_dates():
    files = []
    if not os.path.exists(RAW_DIR): return files
    for f in os.listdir(RAW_DIR):
        if f.endswith(".xls") or f.endswith(".xlsx"):
            name = f.split(".")[0]
            if len(name) == 8 and name.isdigit():
                files.append(name)
    return sorted(files, reverse=True)

# =====================================================
# 启动
# =====================================================
if __name__ == "__main__":
    main()