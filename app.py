import streamlit as st
import pandas as pd
import plotly.express as px
import os
import re
from datetime import timedelta
from PIL import Image

# =====================================================
# 页面配置
# =====================================================
st.set_page_config(
    page_title="MES质量追溯系统",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =====================================================
# 华青+朱柿 主题样式（最终调整版）
# =====================================================
st.markdown("""
<style>
/* 全局背景与字体 */
html, body, [class*="css"] {
    font-size: 18px;
    font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
    color: #FFFFFF !important;          /* 默认文字改为白色 */
    background-color: #013475;
}
section.main > div {
    background-color: #013475;
    padding-top: 0rem !important;
}
.block-container {
    background-color: #013475;
    padding-top: 0.5rem !important;
}

/* 标题 */
h1 {
    margin-top: 0 !important;
    margin-bottom: 0.2rem !important;
    padding-top: 0 !important;
    padding-bottom: 0 !important;
    font-size: 32px !important;
    font-weight: 800 !important;
    color: #EE6F44 !important;
}
h2, h3, h4 {
    color: #EE6F44 !important;
}

/* 指标卡片 */
.metric-card {
    background: rgba(1, 52, 117, 0.95);
    backdrop-filter: blur(10px);
    border-radius: 16px;
    padding: 20px 16px;
    border-left: 6px solid #EE6F44;
    box-shadow: 0 8px 20px rgba(0,0,0,0.5);
    margin-bottom: 10px;
}
.metric-title { font-size: 20px; color: #EE6F44; font-weight: 600; }
.metric-value { font-size: 50px; font-weight: 800; color: #EE6F44; line-height: 1.2; margin: 5px 0; }
.metric-rate { font-size: 20px; color: #EE6F44; font-weight: 600; }

/* 表格全局 */
table {
    text-align: center !important;
    border-collapse: collapse;
    color: #FFFFFF;
    background-color: #013475;
}
th {
    background-color: #012A5E !important;
    color: #EE6F44 !important;
    font-weight: 700;
    padding: 12px 8px !important;
    font-size: 20px;
    border-bottom: 2px solid #FFFFFF;
}
td {
    padding: 12px 8px !important;
    font-size: 26px;
    font-weight: 600;
    border-bottom: 1px solid #FFFFFF;
    color: #EE6F44;
    line-height: 1.8;
    background-color: #013475;
}
.table-header {
    font-size: 22px;
    font-weight: 700;
    color: #EE6F44;
    margin: 15px 0 5px 0;
    border-left: 5px solid #EE6F44;
    padding-left: 12px;
}

/* 下拉框间距 */
.stSelectbox, .stMultiSelect {
    margin-bottom: 0.5rem !important;
}

/* 下拉框标签文字颜色 */
.stSelectbox label, .stMultiSelect label, .stTextInput label {
    color: #EE6F44 !important;
    font-weight: 600 !important;
}

/* ========== 固定主Tab (朱柿) ========== */
.stTabs [data-baseweb="tab-list"] {
    position: fixed !important;
    top: 3.5rem;
    z-index: 9999;
    background: #012A5E;
    border-bottom: 3px solid #EE6F44;
    padding-top: 5px; padding-bottom: 5px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.5);
    width: calc(100% - 2rem);
    left: 1rem; right: 1rem;
}
.stTabs [data-baseweb="tab"] {
    font-size: 26px !important; font-weight: 800 !important;
    height: 65px; color: #EE6F44 !important;
}
.stTabs [aria-selected="true"] {
    color: #EE6F44 !important;
    border-bottom: 4px solid #EE6F44 !important;
}
.stTabs [role="tabpanel"] {
    padding-top: 130px !important;
}

/* 子Tab恢复正常流 */
.stTabs .stTabs [data-baseweb="tab-list"] {
    position: static !important;
    width: 100% !important;
    left: auto !important; right: auto !important;
    box-shadow: none !important;
    border-bottom: 2px solid #EE6F44 !important;
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
    color: #EE6F44 !important;
}
.stTabs .stTabs [aria-selected="true"] {
    color: #EE6F44 !important;
    border-bottom: 3px solid #EE6F44 !important;
}

/* 侧边栏 */
section[data-testid="stSidebar"] {
    background-color: #012A5E;
    border-right: 1px solid #EE6F44;
}
section[data-testid="stSidebar"] .stMarkdown, 
section[data-testid="stSidebar"] label {
    color: #EE6F44 !important;
}

/* 合并单元格表格 */
.merged-table td, .merged-table th {
    text-align: center !important;
    vertical-align: middle !important;
    padding: 10px 6px !important;
    border: 1px solid #FFFFFF !important;
    font-size: 22px !important;
    font-weight: 600 !important;
    color: #EE6F44 !important;
    background-color: #013475;
}
.merged-table th {
    background-color: #012A5E !important;
    color: #EE6F44 !important;
    font-weight: 700 !important;
    position: -webkit-sticky;
    position: sticky;
    top: 0;
    z-index: 10;
}
.scrollable-table {
    max-height: 600px;
    overflow-y: auto;
    border: 1px solid #FFFFFF;
    background-color: #013475;
}

/* 按钮与输入框 */
.stButton button, .stDownloadButton button {
    background-color: #EE6F44;
    color: #013475;
    font-weight: 700;
    border: none;
}
.stTextInput input, .stNumberInput input {
    background-color: #012A5E;
    color: #EE6F44;
    border: 1px solid #EE6F44;
}

/* 滚动条 */
::-webkit-scrollbar { width: 8px; }
::-webkit-scrollbar-track { background: #012A5E; }
::-webkit-scrollbar-thumb { background-color: #EE6F44; border-radius: 4px; }

/* 提示文字（caption）设为白色 */
.stCaption {
    color: #FFFFFF !important;
}
</style>
""", unsafe_allow_html=True)

# =====================================================
# 默认路径
# =====================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RULE_FILE = os.path.join(BASE_DIR, "data", "0.rule.xlsx")
RAW_DIR = os.path.join(BASE_DIR, "data", "raw_data")
PHOTO_DIR = os.path.join(BASE_DIR, "data", "photos")
PRODUCTION_FILE = os.path.join(BASE_DIR, "data", "production", "production.xls")
UF_DATA_DIR = os.path.join(BASE_DIR, "data", "uf_check")

# =====================================================
# 图表美化（华青背景+朱柿柱体）
# =====================================================
def style_bar_chart(fig, title):
    max_y = 0
    for trace in fig.data:
        if hasattr(trace, 'y') and len(trace.y) > 0:
            max_y = max(max_y, max(trace.y))
    fig.update_traces(
        textfont=dict(size=20, color="#EE6F44", family="Arial Black"),
        textposition="outside",
        marker=dict(
            color='#EE6F44',
            line=dict(width=1, color='#FFFFFF')
        )
    )
    y_max = max_y * 1.15 if max_y > 0 else 1
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor='rgba(1,52,117,1)',
        plot_bgcolor='rgba(1,52,117,0.8)',
        title=dict(text=title, font=dict(size=26, color="#EE6F44")),
        xaxis=dict(
            title=None,
            tickfont=dict(size=18, color="#EE6F44"),
            gridcolor='rgba(255,255,255,0.15)'
        ),
        yaxis=dict(
            title=None,
            tickfont=dict(size=18, color="#EE6F44"),
            range=[0, y_max],
            gridcolor='rgba(255,255,255,0.15)'
        ),
        hoverlabel=dict(font_size=16),
        margin=dict(t=80, b=40, l=60, r=20)
    )
    return fig

# =====================================================
# 工具函数
# =====================================================
def clean_str(x):
    if pd.isna(x): return ""
    return re.sub(r"[\n\r\t]", "", str(x).strip().replace("　", " "))

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
# 读取规则 (缓存优化)
# =====================================================
@st.cache_data(ttl=300)
def load_rule():
    if not os.path.exists(RULE_FILE):
        st.error(f"规则文件不存在：{RULE_FILE}")
        st.stop()
    df_rule = pd.read_excel(RULE_FILE, sheet_name=0, header=1)
    df_rule = df_rule.iloc[:, 1:5]
    df_rule.columns = ["MES代码", "病象", "分类", "车间"]
    df_rule["MES代码"] = df_rule["MES代码"].astype(str)
    code_to_cause = dict(zip(df_rule["MES代码"], df_rule["病象"]))
    code_to_shop = dict(zip(df_rule["MES代码"], df_rule["车间"]))
    cause_to_shop = dict(zip(df_rule["病象"], df_rule["车间"]))
    return code_to_cause, code_to_shop, cause_to_shop

# =====================================================
# 日期文件 & 数据加载 (缓存优化)
# =====================================================
def get_all_dates():
    files = []
    if not os.path.exists(RAW_DIR): return files
    for f in os.listdir(RAW_DIR):
        if f.endswith(".xls") or f.endswith(".xlsx"):
            name = f.split(".")[0]
            if len(name) == 8 and name.isdigit():
                files.append(name)
    return sorted(files, reverse=True)

@st.cache_data(ttl=300)
def load_raw(selected_dates):
    all_df = []
    for d in selected_dates:
        fp1 = os.path.join(RAW_DIR, f"{d}.xls")
        fp2 = os.path.join(RAW_DIR, f"{d}.xlsx")
        fp = fp1 if os.path.exists(fp1) else (fp2 if os.path.exists(fp2) else None)
        if fp:
            try:
                df = pd.read_excel(fp)
                df.columns = [clean_str(c) for c in df.columns]
                df["文件日期"] = d
                all_df.append(df)
            except Exception as e:
                st.warning(f"读取失败：{fp} - {e}")
    return pd.concat(all_df, ignore_index=True) if all_df else pd.DataFrame()

# =====================================================
# 派生字段
# =====================================================
def derive_columns(df, code_to_cause, code_to_shop, cause_to_shop):
    df = df.copy()
    col_detect = find_col(df, ["检测分类", "分类"])
    col_reason = find_col(df, ["溯源原因简码", "原因简码", "简码", "原因代码"])
    col_r = find_col(df, ["检测原因"])
    col_u = find_col(df, ["缺陷原因"])
    col_build = find_col(df, ["成型机台", "成型设备", "机台"])
    col_vul = find_col(df, ["硫化日期", "日期"])

    df["成型设备"] = df[col_build] if col_build else "未知"
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
        "模具位置":"位置", "上下模":"位置", "硫化机台":"硫化机台",
        "成型主手":"成型主手", "花纹":"花纹", "规格":"规格",
        "成型时间":"成型时间", "硫化人":"硫化人", "条码":"条码"
    }
    for old, new in rename_map.items():
        if old in df.columns:
            df.rename(columns={old: new}, inplace=True)

    if "位置" in df.columns:
        df["位置"] = df["位置"].apply(extract_chinese)

    for col in ["成型设备", "硫化机台"]:
        if col in df.columns:
            df[col] = df[col].apply(short_name)

    return df

# =====================================================
# 产量提取 (缓存优化)
# =====================================================
def extract_production(file_path, selected_dates):
    try:
        df_prod = pd.read_excel(file_path, header=None, dtype=str)
        header_row = (
            df_prod.iloc[0]
            .fillna("")
            .astype(str)
            .apply(lambda x: re.sub(r"[\s　\n\r\t]+", "", x))
            .tolist()
        )
        total = 0
        unique_dates = list(set(selected_dates))
        for date_str in unique_dates:
            try:
                dt = pd.to_datetime(date_str, format='%Y%m%d')
                patterns = [
                    f"{dt.month:02d}-{dt.day:02d}",
                    f"{dt.month}-{dt.day}",
                    f"{dt.month:02d}.{dt.day:02d}",
                    f"{dt.month}.{dt.day}",
                    f"{dt.month:02d}/{dt.day:02d}",
                    f"{dt.month}/{dt.day}",
                    f"{dt.month}月{dt.day}日",
                    f"{dt.year}-{dt.month:02d}-{dt.day:02d}",
                    f"{dt.year}/{dt.month:02d}/{dt.day:02d}",
                ]
            except:
                continue
            col_idx = None
            for i, cell in enumerate(header_row):
                if cell in patterns:
                    col_idx = i
                    break
            if col_idx is not None:
                col_data = df_prod.iloc[1:, col_idx]
                daily_sum = pd.to_numeric(col_data, errors='coerce').sum()
                total += daily_sum
        return total
    except Exception as e:
        st.warning(f"产量文件解析失败：{e}")
        return None

@st.cache_data(ttl=300)
def load_production(selected_dates):
    if not os.path.exists(PRODUCTION_FILE):
        return None
    return extract_production(PRODUCTION_FILE, selected_dates)

# =====================================================
# UF检查数据加载 (缓存优化)
# =====================================================
UF_COLUMNS = [
    "CWRFVOA_kgf", "CWRFVOA1H_kgf", "CWLFVOA_kgf",
    "CCWRFVOA_kgf", "CCWRFVOA1H_kgf", "CCWLFVOA_kgf",
    "CON_kgf", "Upper_g", "Lower_g"
]

@st.cache_data(ttl=300)
def load_uf_check_data():
    all_uf = []
    if not os.path.exists(UF_DATA_DIR):
        return pd.DataFrame(columns=["条码"] + UF_COLUMNS)
    for fname in os.listdir(UF_DATA_DIR):
        if fname.startswith("UFDATA_") and (fname.endswith(".xls") or fname.endswith(".xlsx")):
            file_path = os.path.join(UF_DATA_DIR, fname)
            try:
                df_uf = pd.read_excel(file_path)
                barcode_col = None
                for col in df_uf.columns:
                    if "条码" in str(col):
                        barcode_col = col
                        break
                if barcode_col is None:
                    df_uf.rename(columns={df_uf.columns[0]: "条码"}, inplace=True)
                    barcode_col = "条码"
                else:
                    df_uf.rename(columns={barcode_col: "条码"}, inplace=True)
                df_uf["条码"] = df_uf["条码"].astype(str).str.strip()
                available = [c for c in UF_COLUMNS if c in df_uf.columns]
                df_uf = df_uf[["条码"] + available].copy()
                all_uf.append(df_uf)
            except Exception as e:
                st.warning(f"读取UF文件失败：{file_path} - {e}")
    if all_uf:
        return pd.concat(all_uf, ignore_index=True)
    return pd.DataFrame(columns=["条码"] + UF_COLUMNS)

# =====================================================
# 图片弹窗
# =====================================================
@st.dialog("轮胎照片", width="large")
def show_big_image(img_path):
    if os.path.exists(img_path):
        img = Image.open(img_path)
        st.image(img, width='stretch')
    else:
        st.warning("图片文件不存在")

def trigger_image_popup(barcode):
    barcode = str(barcode).strip()
    for ext in [".jpg", ".jpeg", ".png", ".JPG", ".JPEG", ".PNG"]:
        fp = os.path.join(PHOTO_DIR, barcode + ext)
        if os.path.exists(fp):
            show_big_image(fp)
            return
    st.warning(f"未找到图片：{barcode}")

# =====================================================
# 通用明细表（筛选顺序：车间、病象、成型机、成型主手、硫化机、硫化人）
# =====================================================
def render_detail_table(df, key_prefix):
    if df.empty:
        st.info("无数据")
        return

    shop_order = ["密炼", "部件", "部件成型", "成型", "硫化", "工程", "工艺"]
    all_shops = df["车间"].dropna().astype(str).unique().tolist()
    sorted_shops = [s for s in shop_order if s in all_shops] + sorted([s for s in all_shops if s not in shop_order])
    shops = ["全部"] + sorted_shops

    causes = ["全部"] + sorted(df["病象"].dropna().astype(str).unique().tolist())
    machines = ["全部"] + sorted(df["成型设备"].dropna().astype(str).unique().tolist())
    masters = ["全部"] + sorted(df["成型主手"].dropna().astype(str).unique().tolist())
    vul_machines = ["全部"] + sorted(df["硫化机台"].dropna().astype(str).unique().tolist())
    vul_workers = ["全部"] + sorted(df["硫化人"].dropna().astype(str).unique().tolist())

    cols = st.columns(6)
    with cols[0]:
        selected_shop = st.selectbox("🏭 车间", shops, key=f"shop_{key_prefix}")
    with cols[1]:
        selected_cause = st.selectbox("🔍 病象", causes, key=f"cause_{key_prefix}")
    with cols[2]:
        selected_machine = st.selectbox("⚙️ 成型机", machines, key=f"machine_{key_prefix}")
    with cols[3]:
        selected_master = st.selectbox("👤 成型主手", masters, key=f"master_{key_prefix}")
    with cols[4]:
        selected_vul_machine = st.selectbox("🔥 硫化机", vul_machines, key=f"vul_machine_{key_prefix}")
    with cols[5]:
        selected_vul_worker = st.selectbox("👨‍🏭 硫化人", vul_workers, key=f"vul_worker_{key_prefix}")

    filtered_df = df.copy()
    if selected_shop != "全部":
        filtered_df = filtered_df[filtered_df["车间"] == selected_shop]
    if selected_cause != "全部":
        filtered_df = filtered_df[filtered_df["病象"] == selected_cause]
    if selected_machine != "全部":
        filtered_df = filtered_df[filtered_df["成型设备"] == selected_machine]
    if selected_master != "全部":
        filtered_df = filtered_df[filtered_df["成型主手"] == selected_master]
    if selected_vul_machine != "全部":
        filtered_df = filtered_df[filtered_df["硫化机台"] == selected_vul_machine]
    if selected_vul_worker != "全部":
        filtered_df = filtered_df[filtered_df["硫化人"] == selected_vul_worker]

    if filtered_df.empty:
        st.warning("无符合条件的数据")
        return

    show_cols = ["病象", "条码", "硫化机台", "硫化人", "硫化日期",
                 "成型设备", "成型时间", "成型主手", "规格", "花纹", "位置", "车间"]
    show_cols = [c for c in show_cols if c in filtered_df.columns]

    st.markdown("<div class='table-header'>📋 明细数据</div>", unsafe_allow_html=True)

    event = st.dataframe(
        filtered_df[show_cols],
        width='stretch',
        height=500,
        hide_index=True,
        selection_mode="single-row",
        on_select="rerun",
        key=f"detail_table_{key_prefix}"
    )

    if event.selection.rows:
        selected_row = event.selection.rows[0]
        barcode = str(filtered_df.iloc[selected_row]["条码"])
        trigger_image_popup(barcode)

# =====================================================
# UF专用明细表
# =====================================================
def render_uf_detail_table(df, uf_check_df, key_prefix):
    if not uf_check_df.empty:
        df["条码"] = df["条码"].astype(str).str.strip()
        uf_check_df["条码"] = uf_check_df["条码"].astype(str).str.strip()
        merged = df.merge(uf_check_df, on="条码", how="left")
    else:
        merged = df.copy()
        for c in UF_COLUMNS:
            merged[c] = None

    if merged.empty:
        st.info("无数据")
        return

    col1, col2, col3 = st.columns(3)
    with col1:
        machines = ["全部"] + sorted(merged["成型设备"].dropna().astype(str).unique().tolist())
        selected_machine = st.selectbox("⚙️ 成型机", machines, key=f"uf_machine_{key_prefix}")
    with col2:
        specs = ["全部"] + sorted(merged["规格"].dropna().astype(str).unique().tolist())
        selected_spec = st.selectbox("📏 规格", specs, key=f"uf_spec_{key_prefix}")
    with col3:
        patterns = ["全部"] + sorted(merged["花纹"].dropna().astype(str).unique().tolist())
        selected_pattern = st.selectbox("🎨 花纹", patterns, key=f"uf_pattern_{key_prefix}")

    filtered = merged.copy()
    if selected_machine != "全部":
        filtered = filtered[filtered["成型设备"] == selected_machine]
    if selected_spec != "全部":
        filtered = filtered[filtered["规格"] == selected_spec]
    if selected_pattern != "全部":
        filtered = filtered[filtered["花纹"] == selected_pattern]

    if filtered.empty:
        st.warning("无符合条件的数据")
        return

    base_cols = ["条码", "硫化机台", "成型设备", "成型时间", "成型主手", "规格", "花纹"]
    base_cols = [c for c in base_cols if c in filtered.columns]
    show_cols = base_cols + UF_COLUMNS

    st.markdown("<div class='table-header'>📋 UF 明细数据（含检查指标）</div>", unsafe_allow_html=True)
    st.dataframe(
        filtered[show_cols],
        width='stretch',
        height=500,
        hide_index=True
    )

# =====================================================
# 合并单元格渲染函数（滚动+冻结表头）
# =====================================================
def render_merged_person_table(person_df, person_col, type_col="类型", cause_col="病象", count_col="数量", total_col="合计", max_height="600px"):
    if person_df.empty:
        st.info("无数据")
        return

    cols = [person_col, type_col, cause_col, count_col, total_col]
    for c in cols:
        if c not in person_df.columns:
            st.error(f"缺少列: {c}")
            return

    html = f'<div class="scrollable-table" style="max-height: {max_height};">'
    html += '<table class="merged-table" style="width:100%">'
    html += f'<thead><tr><th>{person_col}</th><th>{type_col}</th><th>{cause_col}</th><th>{count_col}</th><th>{total_col}</th></tr></thead>'
    html += '<tbody>'

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
    st.markdown(html, unsafe_allow_html=True)

# =====================================================
# 主程序
# =====================================================
def main():
    st.title("🏭 MES质量追溯系统")
    (code_to_cause, code_to_shop, cause_to_shop) = load_rule()
    all_dates = get_all_dates()

    with st.sidebar:
        st.header("数据选择")
        selected_dates = st.multiselect("选择分析日期", all_dates, default=all_dates[:1] if all_dates else [])

        total_production = 0
        if selected_dates:
            auto_prod = load_production(selected_dates)
            if auto_prod is not None:
                total_production = auto_prod
                st.metric("硫化产量（自动提取）", f"{total_production:,.0f}")
            else:
                st.warning("自动提取失败，请手动上传产量文件")
                uploaded_file = st.file_uploader("上传硫化产量Excel", type=["xls", "xlsx"], key="prod_upload")
                if uploaded_file is not None:
                    with st.spinner("正在解析产量..."):
                        with open("temp_production.xlsx", "wb") as f:
                            f.write(uploaded_file.getbuffer())
                        total_production = extract_production("temp_production.xlsx", selected_dates)
                        if total_production is not None:
                            st.success(f"已提取产量：{total_production:,.0f}")
                        else:
                            st.error("产量文件格式不正确")
                            total_production = 0
        else:
            st.warning("请选择日期")

        st.divider()
        st.write("规则文件")
        st.code(RULE_FILE)
        st.write("原始数据")
        st.code(RAW_DIR)
        st.write("照片库")
        st.code(PHOTO_DIR)

    if not selected_dates:
        st.warning("请选择日期")
        return

    raw = load_raw(selected_dates)
    if raw.empty:
        st.error("无数据")
        return

    df = derive_columns(raw, code_to_cause, code_to_shop, cause_to_shop)

    waste_df = df[df["类型"] == "废品"]
    app_df = df[df["类型"] == "次品外观"]
    uf_df = df[df["类型"] == "次品UF"]

    waste_shop = waste_df["车间"].value_counts().reset_index()
    waste_shop.columns = ["车间", "数量"]
    app_shop = app_df["车间"].value_counts().reset_index()
    app_shop.columns = ["车间", "数量"]
    uf_mac = uf_df["成型设备"].value_counts().reset_index()
    uf_mac.columns = ["成型设备", "数量"]

    uf_check_data = load_uf_check_data()

    if total_production > 0:
        waste_rate = len(waste_df) / total_production
        app_rate = len(app_df) / total_production
        uf_rate = len(uf_df) / total_production
        qual_rate = 1 - (waste_rate + app_rate + uf_rate)
    else:
        waste_rate = app_rate = uf_rate = 0
        qual_rate = 1

    tab1, tab2, tab3 = st.tabs(["综合看板", "废品分析", "次品分析"])

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
        c1, c2 = st.columns(2)

        fig1 = px.bar(waste_shop, x="车间", y="数量", text="数量", text_auto=True)
        c1.plotly_chart(style_bar_chart(fig1, "废品车间分布"), width='stretch', key="tab1_waste_shop")

        fig2 = px.bar(app_shop, x="车间", y="数量", text="数量", text_auto=True)
        c2.plotly_chart(style_bar_chart(fig2, "次品外观车间分布"), width='stretch', key="tab1_app_shop")

        fig3 = px.bar(uf_mac, x="成型设备", y="数量", text="数量", text_auto=True)
        st.plotly_chart(style_bar_chart(fig3, "UF次品成型机分布"), width='stretch', key="tab1_uf_mac")

        # ---------- 废品 + 次品外观 综合分析 ----------
        st.subheader("废品 + 次品外观 综合分析")
        combined = df[df["类型"].isin(["废品", "次品外观"])]

        summary = combined.groupby(["病象", "车间"]).agg(
            总数=("类型", "count"),
            废品数=("类型", lambda x: (x == "废品").sum()),
            次品数=("类型", lambda x: (x == "次品外观").sum())
        ).reset_index()
        summary = summary[["病象", "总数", "废品数", "次品数", "车间"]].sort_values("总数", ascending=False)

        col_left, col_right = st.columns([1, 1.3])
        with col_left:
            st.markdown("<span style='color:#FFFFFF;'>单击行查看该病象/车间的条码明细</span>", unsafe_allow_html=True)
            event_summary = st.dataframe(
                summary,
                width='stretch',
                height=520,
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
                    detail_cols = ["条码", "成型设备", "硫化机台", "规格", "花纹", "成型主手", "硫化人"]
                    detail_cols = [c for c in detail_cols if c in detail.columns]
                    st.markdown(f"<span style='color:#EE6F44;'>{selected_cause}（{selected_shop}）的明细</span>", unsafe_allow_html=True)
                    st.dataframe(
                        detail[detail_cols],
                        width='stretch',
                        height=520,
                        hide_index=True
                    )
                else:
                    st.info("无明细数据")
            else:
                st.markdown("<span style='color:#FFFFFF;'>请单击左侧表格的行查看明细</span>", unsafe_allow_html=True)

        # ---------- 成型/硫化人员分析并排显示（不含返修，UF算成型） ----------
        st.subheader("成型/硫化人员分析（不含返修）")
        left_col, right_col = st.columns(2)

        with left_col:
            st.markdown("<span style='color:#EE6F44; font-weight:bold; font-size:22px;'>成型人员分析</span>", unsafe_allow_html=True)
            condition = ((df["车间"] == "成型") | (df["类型"] == "次品UF")) & (df["类型"] != "返修")
            molding_data = df[condition]
            if not molding_data.empty:
                person_detail = molding_data.groupby(["成型主手", "类型", "病象"]).size().reset_index(name="数量")
                person_detail["合计"] = person_detail.groupby("成型主手")["数量"].transform("sum")
                person_detail = person_detail.sort_values(["合计", "成型主手", "类型", "病象"],
                                                          ascending=[False, True, True, True])
                render_merged_person_table(person_detail, "成型主手", max_height="600px")
            else:
                st.info("无成型及UF数据")

        with right_col:
            st.markdown("<span style='color:#EE6F44; font-weight:bold; font-size:22px;'>硫化人员分析</span>", unsafe_allow_html=True)
            vul_data = df[(df["车间"] == "硫化") & (df["类型"].isin(["废品", "次品外观"]))]
            if not vul_data.empty:
                person_detail = vul_data.groupby(["硫化人", "类型", "病象"]).size().reset_index(name="数量")
                person_detail["合计"] = person_detail.groupby("硫化人")["数量"].transform("sum")
                person_detail = person_detail.sort_values(["合计", "硫化人", "类型", "病象"],
                                                          ascending=[False, True, True, True])
                render_merged_person_table(person_detail, "硫化人", max_height="600px")
            else:
                st.info("无硫化数据（废品/次品外观）")

    with tab2:
        st.subheader("废品分析")
        fig = px.bar(waste_shop, x="车间", y="数量", text="数量", text_auto=True)
        st.plotly_chart(style_bar_chart(fig, "废品车间分布"), width='stretch', key="tab2_waste_shop")
        render_detail_table(waste_df, "waste")

    with tab3:
        sub1, sub2 = st.tabs(["外观次品", "UF次品"])
        with sub1:
            fig = px.bar(app_shop, x="车间", y="数量", text="数量", text_auto=True)
            st.plotly_chart(style_bar_chart(fig, "外观次品车间分布"), width='stretch', key="tab3_app_shop")
            render_detail_table(app_df, "app")
        with sub2:
            st.subheader("UF 次品分析")
            uf_mac_all = uf_df["成型设备"].value_counts().reset_index()
            uf_mac_all.columns = ["成型设备", "数量"]
            fig_uf = px.bar(uf_mac_all, x="成型设备", y="数量", text="数量", text_auto=True)
            st.plotly_chart(style_bar_chart(fig_uf, "UF次品成型机分布"), width='stretch', key="tab3_uf_mac")
            render_uf_detail_table(uf_df, uf_check_data, "uf_detail")

if __name__ == "__main__":
    main()