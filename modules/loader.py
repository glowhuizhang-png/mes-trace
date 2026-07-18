import streamlit as st
import pandas as pd
import os
import re
from modules.utils import clean_str, full_to_half

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
    all_df = []
    for d in selected_dates:
        fp = None
        for ext in ['.xls', '.xlsx']:
            candidate = os.path.join(raw_dir, f"{d}{ext}")
            if os.path.exists(candidate):
                fp = candidate
                break
        if fp:
            try:
                df = pd.read_excel(fp)
                df.columns = [clean_str(c) for c in df.columns]
                df["文件日期"] = d
                all_df.append(df)
            except Exception as e:
                st.warning(f"读取失败：{fp} - {e}")
    return pd.concat(all_df, ignore_index=True) if all_df else pd.DataFrame()

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
    files = []
    if not os.path.exists(raw_dir):
        return files
    for f in os.listdir(raw_dir):
        if f.endswith(('.xls', '.xlsx')):
            name = f.rsplit('.', 1)[0]
            if len(name) == 8 and name.isdigit():
                files.append(name)
    return sorted(files, reverse=True)