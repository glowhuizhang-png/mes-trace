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
# 工业风格样式（主Tab固定，子Tab不固定，表格字体加大）
# =====================================================
st.markdown("""
<style>
html, body, [class*="css"] {
    font-size: 16px;
    font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
    color: #000000 !important;
}
.metric-card {
    background: linear-gradient(145deg, #f0f7ff 0%, #e6f0fa 100%);
    border-radius: 16px;
    padding: 20px 16px;
    border-left: 6px solid #1976D2;
    box-shadow: 0 8px 20px rgba(0,0,0,0.08);
    margin-bottom: 10px;
}
.metric-title { font-size: 18px; color: #000000; font-weight: 600; }
.metric-value { font-size: 46px; font-weight: 800; color: #000000; line-height: 1.2; margin: 5px 0; }
.metric-rate { font-size: 18px; color: #000000; font-weight: 600; }

table {
    text-align: center !important;
    border-collapse: collapse;
    color: #000000;
}
th {
    background-color: #1a3b5c !important;
    color: #ffffff !important;
    font-weight: 600;
    padding: 12px 8px !important;
    font-size: 16px;
}
td {
    padding: 12px 8px !important;
    font-size: 18px;
    border-bottom: 1px solid #e0e0e0;
    color: #000000;
    line-height: 1.8;
}
.table-header {
    font-size: 22px;
    font-weight: 700;
    color: #000000;
    margin: 20px 0 10px 0;
    border-left: 5px solid #1976D2;
    padding-left: 12px;
}

/* ========== 固定主Tab ========== */
.stTabs [data-baseweb="tab-list"] {
    position: fixed !important;
    top: 3.5rem;
    z-index: 9999;
    background: white;
    border-bottom: 3px solid #1976D2;
    padding-top: 5px; padding-bottom: 5px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    width: calc(100% - 2rem);
    left: 1rem; right: 1rem;
}
.stTabs [data-baseweb="tab"] {
    font-size: 24px !important; font-weight: 700 !important;
    height: 60px; color: #000000 !important;
}
.stTabs [aria-selected="true"] {
    color: #1976D2 !important;
    border-bottom: 4px solid #1976D2 !important;
}
.stTabs [role="tabpanel"] {
    padding-top: 120px !important;
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
}
.stTabs .stTabs [role="tabpanel"] {
    padding-top: 0 !important;
}
.stTabs .stTabs [data-baseweb="tab"] {
    font-size: 18px !important;
    height: 45px !important;
}

section[data-testid="stSidebar"] {
    background-color: #fafbfc;
    border-right: 1px solid #e0e0e0;
}
</style>
""", unsafe_allow_html=True)

# =====================================================
# 默认路径
# =====================================================
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RULE_FILE = os.path.join(BASE_DIR, "data", "0.rule.xlsx")
RAW_DIR = os.path.join(BASE_DIR, "data", "质量原始数据")
PHOTO_DIR = os.path.join(BASE_DIR, "data", "照片库")
PRODUCTION_FILE = os.path.join(BASE_DIR, "data", "硫化产量", "硫化产量.xls")
UF_DATA_DIR = os.path.join(BASE_DIR, "data", "UF检查数据")

# =====================================================
# 图表美化
# =====================================================
def style_bar_chart(fig, title):
    max_y = 0
    for trace in fig.data:
        if hasattr(trace, 'y') and len(trace.y) > 0:
            max_y = max(max_y, max(trace.y))
    fig.update_traces(
        textfont=dict(size=20, color="black", family="Arial Black"),
        textposition="outside",
        marker=dict(line=dict(width=1, color="#333333"))
    )
    y_max = max_y * 1.2 if max_y > 0 else 1
    fig.update_layout(
        template="plotly_white",
        title=dict(text=title, font=dict(size=28, color="#000000")),
        xaxis=dict(title_font=dict(size=20, color="#000000"), tickfont=dict(size=18, color="#000000")),
        yaxis=dict(title_font=dict(size=20, color="#000000"), tickfont=dict(size=18, color="#000000"), range=[0, y_max]),
        hoverlabel=dict(font_size=18),
        margin=dict(t=100, b=50, l=80, r=40)
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

# =====================================================
# 读取规则
# =====================================================
@st.cache_data
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
# 日期文件 & 数据加载
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

@st.cache_data
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
    return df

# =====================================================
# 产量提取
# =====================================================
def extract_production(file_path, selected_dates):
    try:
        df_prod = pd.read_excel(file_path, header=None, dtype=str)
        header_row = df_prod.iloc[0].fillna("").astype(str).str.strip()
        total = 0
        for date_str in selected_dates:
            try:
                dt = pd.to_datetime(date_str, format='%Y%m%d')
                patterns = [
                    f"{dt.month}.{dt.day}",
                    f"{dt.month:02d}.{dt.day:02d}",
                    f"{dt.month}-{dt.day}",
                    f"{dt.month:02d}-{dt.day:02d}",
                    f"{dt.month}/{dt.day}",
                    f"{dt.month}/{dt.day:02d}",
                    f"{dt.month}月{dt.day}日",
                ]
            except:
                continue
            col_idx = None
            for i, cell in enumerate(header_row):
                for pat in patterns:
                    if pat in cell:
                        col_idx = i
                        break
                if col_idx is not None:
                    break
            if col_idx is not None:
                col_data = df_prod.iloc[1:, col_idx]
                total += pd.to_numeric(col_data, errors='coerce').sum()
        return total
    except Exception as e:
        st.warning(f"产量文件解析失败：{e}")
        return None

@st.cache_data
def load_production(selected_dates):
    if not os.path.exists(PRODUCTION_FILE):
        return None
    return extract_production(PRODUCTION_FILE, selected_dates)

# =====================================================
# UF检查数据加载（文件夹内所有文件）
# =====================================================
UF_COLUMNS = [
    "CWRFVOA_kgf", "CWRFVOA1H_kgf", "CWLFVOA_kgf",
    "CCWRFVOA_kgf", "CCWRFVOA1H_kgf", "CCWLFVOA_kgf",
    "CON_kgf", "Upper_g", "Lower_g"
]

@st.cache_data
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
# 明细表
# =====================================================
def render_detail_table(df, key_prefix):
    if df.empty:
        st.info("无数据")
        return

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        shops = ["全部"] + sorted(df["车间"].dropna().astype(str).unique().tolist())
        selected_shop = st.selectbox("🏭 车间", shops, key=f"shop_{key_prefix}")
    with col2:
        causes = ["全部"] + sorted(df["病象"].dropna().astype(str).unique().tolist())
        selected_cause = st.selectbox("🔍 病象", causes, key=f"cause_{key_prefix}")
    with col3:
        masters = ["全部"] + sorted(df["成型主手"].dropna().astype(str).unique().tolist())
        selected_master = st.selectbox("👤 成型主手", masters, key=f"master_{key_prefix}")
    with col4:
        machines = ["全部"] + sorted(df["成型设备"].dropna().astype(str).unique().tolist())
        selected_machine = st.selectbox("⚙️ 成型机", machines, key=f"machine_{key_prefix}")

    filtered_df = df.copy()
    if selected_shop != "全部": filtered_df = filtered_df[filtered_df["车间"] == selected_shop]
    if selected_cause != "全部": filtered_df = filtered_df[filtered_df["病象"] == selected_cause]
    if selected_master != "全部": filtered_df = filtered_df[filtered_df["成型主手"] == selected_master]
    if selected_machine != "全部": filtered_df = filtered_df[filtered_df["成型设备"] == selected_machine]

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
        height=400,
        hide_index=True,
        selection_mode="single-row",
        on_select="rerun",
        key=f"detail_table_{key_prefix}"
    )

    if event.selection.rows:
        selected_row = event.selection.rows[0]
        barcode = str(filtered_df.iloc[selected_row]["条码"])
        trigger_image_popup(barcode)

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
        height=400,
        hide_index=True
    )

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
            ("综合合格率", f"{qual_rate:.2%}", f"产量：{total_production:,.0f}")   # 新增产量显示
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
        c1.plotly_chart(style_bar_chart(fig1, "废品车间分析"), width='stretch', key="tab1_waste_shop")

        fig2 = px.bar(app_shop, x="车间", y="数量", text="数量", text_auto=True)
        c2.plotly_chart(style_bar_chart(fig2, "次品外观车间分析"), width='stretch', key="tab1_app_shop")

        fig3 = px.bar(uf_mac, x="成型设备", y="数量", text="数量", text_auto=True)
        st.plotly_chart(style_bar_chart(fig3, "UF次品成型机分析"), width='stretch', key="tab1_uf_mac")

        st.subheader("废品 + 次品外观 综合分析")
        combined = df[df["类型"].isin(["废品", "次品外观"])]
        summary = combined.groupby(["病象", "车间"]).agg(
            总数=("类型", "count"),
            废品数=("类型", lambda x: (x == "废品").sum()),
            次品数=("类型", lambda x: (x == "次品外观").sum())
        ).reset_index()
        summary = summary[["病象", "总数", "废品数", "次品数", "车间"]].sort_values("总数", ascending=False)
        st.dataframe(summary, width='stretch', hide_index=True)

        st.subheader("成型机 × 病象矩阵")
        pivot = pd.pivot_table(combined, index="成型设备", columns="病象", values="条码", aggfunc="count", fill_value=0)
        pivot["合计"] = pivot.sum(axis=1)
        cols = ["合计"] + [c for c in pivot.columns if c != "合计"]
        pivot = pivot[cols]
        pivot = pivot[pivot.sum(axis=0).sort_values(ascending=False).index]
        st.dataframe(pivot, width='stretch')

    with tab2:
        st.subheader("废品分析")
        fig = px.bar(waste_shop, x="车间", y="数量", text="数量", text_auto=True)
        st.plotly_chart(style_bar_chart(fig, "废品车间分析"), width='stretch', key="tab2_waste_shop")
        render_detail_table(waste_df, "waste")

    with tab3:
        sub1, sub2 = st.tabs(["外观次品", "UF次品"])
        with sub1:
            fig = px.bar(app_shop, x="车间", y="数量", text="数量", text_auto=True)
            st.plotly_chart(style_bar_chart(fig, "外观次品车间分析"), width='stretch', key="tab3_app_shop")
            render_detail_table(app_df, "app")
        with sub2:
            st.subheader("UF 次品分析")
            uf_mac_all = uf_df["成型设备"].value_counts().reset_index()
            uf_mac_all.columns = ["成型设备", "数量"]
            fig_uf = px.bar(uf_mac_all, x="成型设备", y="数量", text="数量", text_auto=True)
            st.plotly_chart(style_bar_chart(fig_uf, "UF次品按成型机分布"), width='stretch', key="tab3_uf_mac")
            render_uf_detail_table(uf_df, uf_check_data, "uf_detail")

if __name__ == "__main__":
    main()