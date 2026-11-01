import streamlit as st
import pandas as pd
import os
import re
from modules.utils import clean_str, full_to_half
from config import DETECT_DATE_COLUMN, SHIFT_BOUNDARY_HOUR, DEDUPE_KEY

# 单文件日期扫描的增量缓存： (路径, 修改时间ns, 大小) -> 生产日集合
_FILE_DATE_CACHE = {}


def iter_raw_files(raw_dir):
    """按名称排序返回原始数据文件路径列表"""
    paths = []
    if not os.path.isdir(raw_dir):
        return paths
    for ext in (".xls", ".xlsx"):
        for name in sorted(os.listdir(raw_dir)):
            if name.lower().endswith(ext):
                paths.append(os.path.join(raw_dir, name))
    return paths


def date_from_filename(path):
    """从文件名解析 YYYYMMDD，解析不出返回 None"""
    stem = os.path.splitext(os.path.basename(path))[0].strip()
    if len(stem) == 8 and stem.isdigit():
        return stem
    return None


def derive_date_series(detect_values):
    """把检测日期列换算成生产日(YYYYMMDD 字符串)：08:00 前的记录归入上一生产日"""
    ts = pd.to_datetime(detect_values, errors="coerce")
    day = ts.dt.normalize()
    is_early = ts.dt.hour < SHIFT_BOUNDARY_HOUR
    shifted = day - pd.to_timedelta(is_early.astype(int), unit="D")
    return shifted.dt.strftime("%Y%m%d")


def read_detect_dates(path):
    """只读取检测日期列，返回 Series；文件中无该列时返回 None"""
    try:
        df = pd.read_excel(path, usecols=lambda c: str(c).strip() == DETECT_DATE_COLUMN)
    except Exception:
        return None
    if df is None or len(df.columns) == 0:
        return None
    return df.iloc[:, 0]


def _scan_file_dates(path):
    """读取单个文件包含的生产日集合（检测日期列优先，回退文件名）"""
    name_date = date_from_filename(path)
    series = read_detect_dates(path)
    dates = set()
    if series is not None:
        derived = derive_date_series(series)
        dates = {d for d in derived.dropna().unique()}
    if not dates and name_date:
        dates = {name_date}
    return dates


def assign_file_date(df, path):
    """给每行写入“文件日期”（生产日）：优先取检测日期列，缺失时回退文件名"""
    fallback = date_from_filename(path)
    if DETECT_DATE_COLUMN in df.columns:
        derived = derive_date_series(df[DETECT_DATE_COLUMN])
        df["文件日期"] = derived.where(derived.notna(), fallback)
    else:
        df["文件日期"] = fallback
    return df


def dedupe_records(df):
    """
    移除重复的检测记录。

    仅对带有条码的记录去重（条码是检测记录的身份标识）；
    条码缺失或关键字段为空的行一律保留，避免不同记录因空值而被误判为重复。
    """
    key = [c for c in DEDUPE_KEY if c in df.columns]
    if len(key) < 2 or "条码" not in key:
        return df
    has_id = df["条码"].notna() & (df["条码"].astype(str).str.strip() != "")
    if not has_id.any():
        return df
    dup_mask = df.duplicated(subset=key, keep="first")
    # 空值行不参与去重
    dup_mask = dup_mask & has_id
    if not dup_mask.any():
        return df
    return df[~dup_mask]


@st.cache_data(ttl=300)
def build_date_index(raw_dir):
    """
    扫描原始文件，用检测日期列建立 “生产日 -> 文件列表” 索引。

    单个文件的日期扫描结果按 (路径, 修改时间, 大小) 增量缓存，
    只有新增或改动过的文件才会被重新读取，避免每次重建都全量扫描。
    """
    index = {}
    for path in iter_raw_files(raw_dir):
        try:
            stt = os.stat(path)
            sig = (path, stt.st_mtime_ns, stt.st_size)
        except OSError:
            continue
        dates = _FILE_DATE_CACHE.get(sig)
        if dates is None:
            dates = _scan_file_dates(path)
            _FILE_DATE_CACHE[sig] = dates
        for d in dates:
            index.setdefault(d, []).append(path)
    return index


def extract_single_daily_production(file_path, date_str):
    try:
        df_prod = pd.read_excel(file_path, header=None, dtype=str)
        header_row = df_prod.iloc[0].fillna("").astype(str).str.strip()
        header_row = [re.sub(r"[\s　]+", "", x) for x in header_row]
        dt = pd.to_datetime(date_str, format='%Y%m%d')
        patterns = [
            f"{dt.month:02d}-{dt.day:02d}", f"{dt.month}-{dt.day}",
            f"{dt.month:02d}.{dt.day:02d}", f"{dt.month}.{dt.day}",
            f"{dt.month:02d}/{dt.day:02d}", f"{dt.month}/{dt.day}",
            f"{dt.month}月{dt.day}日",
            f"{dt.year}-{dt.month:02d}-{dt.day:02d}",
            f"{dt.year}/{dt.month:02d}/{dt.day:02d}",
        ]
        for i, cell in enumerate(header_row):
            if cell in patterns:
                col_data = df_prod.iloc[1:, i]
                return pd.to_numeric(col_data, errors='coerce').sum()
        return 0
    except Exception as e:
        st.warning(f"产量提取失败: {file_path} - {e}")
        return 0

@st.cache_data(ttl=300)
def load_rule(rule_file):
    if not os.path.exists(rule_file):
        st.error(f"规则文件不存在：{rule_file}")
        st.stop()
    df_rule = pd.read_excel(rule_file, sheet_name=0, header=1)
    df_rule = df_rule.iloc[:, 1:5]
    df_rule.columns = ["MES代码", "病象", "分类", "车间"]
    df_rule["MES代码"] = df_rule["MES代码"].astype(str).str.strip()
    code_to_cause = dict(zip(df_rule["MES代码"], df_rule["病象"]))
    code_to_shop = dict(zip(df_rule["MES代码"], df_rule["车间"]))
    cause_to_shop = dict(zip(df_rule["病象"], df_rule["车间"]))
    return code_to_cause, code_to_shop, cause_to_shop

@st.cache_data(ttl=300)
def load_raw(selected_dates, raw_dir):
    """
    加载原始数据。

    日期识别口径：优先使用 Excel 内的“检测日期”列（按 08:00 班次分界换算生产日），
    而不是文件名。每个生产日的数据可能分散在多个文件中，因此按日期索引定位文件后，
    再按行自身的生产日做精确过滤。
    """
    if not selected_dates:
        return pd.DataFrame()

    selected = set(selected_dates)
    index = build_date_index(raw_dir)

    # 命中任一所选生产日的文件都需要读取
    target_files = []
    for d in sorted(selected):
        for p in index.get(d, []):
            if p not in target_files:
                target_files.append(p)

    all_df = []
    for fp in target_files:
        try:
            df = pd.read_excel(fp)
            df.columns = [clean_str(c) for c in df.columns]
            df = assign_file_date(df, fp)
            # 只保留真正属于所选生产日的行
            df = df[df["文件日期"].isin(selected)]
            if not df.empty:
                all_df.append(df)
        except Exception as e:
            st.warning(f"读取失败：{fp} - {e}")

    if not all_df:
        return pd.DataFrame()

    merged = pd.concat(all_df, ignore_index=True)
    return dedupe_records(merged)


@st.cache_data(ttl=300)
def load_production(selected_dates, production_file):
    if not os.path.exists(production_file):
        return None
    total = sum(extract_single_daily_production(production_file, d) for d in selected_dates)
    return total

@st.cache_data(ttl=300)
def load_daily_production_dict(selected_dates, production_file):
    if not os.path.exists(production_file):
        return {}
    return {d: extract_single_daily_production(production_file, d) for d in selected_dates}

@st.cache_data(ttl=300)
def load_uf_check_data(uf_data_dir):
    UF_COLUMNS = [
        "CWRFVOA_kgf", "CWRFVOA1H_kgf", "CWLFVOA_kgf",
        "CCWRFVOA_kgf", "CCWRFVOA1H_kgf", "CCWLFVOA_kgf",
        "CON_kgf", "Upper_g", "Lower_g"
    ]
    all_uf = []
    if not os.path.exists(uf_data_dir):
        return pd.DataFrame(columns=["条码"] + UF_COLUMNS)
    for fname in os.listdir(uf_data_dir):
        if fname.upper().startswith("UFDATA_") and fname.lower().endswith(('.xls', '.xlsx')):
            file_path = os.path.join(uf_data_dir, fname)
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
                df_uf["条码"] = full_to_half(df_uf["条码"])
                df_uf["条码"] = df_uf["条码"].astype(str).str.replace(r'\.0$', '', regex=True)
                available = [c for c in UF_COLUMNS if c in df_uf.columns]
                df_uf = df_uf[["条码"] + available].copy()
                all_uf.append(df_uf)
            except Exception as e:
                st.warning(f"读取UF文件失败：{file_path} - {e}")
    if all_uf:
        return pd.concat(all_uf, ignore_index=True)
    return pd.DataFrame(columns=["条码"] + UF_COLUMNS)

def get_all_dates(raw_dir):
    """返回所有可用的生产日（YYYYMMDD 字符串），来自检测日期列，倒序"""
    index = build_date_index(raw_dir)
    return sorted(index.keys(), reverse=True)