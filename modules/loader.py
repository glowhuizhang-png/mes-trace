import streamlit as st
import pandas as pd
import os
import re
from datetime import timedelta
from modules.utils import clean_str, find_col, full_to_half, extract_chinese, short_name

# ---------- 产量提取辅助函数 ----------
def extract_single_daily_production(file_path, date_str):
    """从production.xls中提取指定日期的产量总和"""
    try:
        df_prod = pd.read_excel(file_path, header=None, dtype=str)
        header_row = df_prod.iloc[0].fillna("").astype(str).str.strip()
        header_row = [re.sub(r"[\s　\n\r\t]+", "", x) for x in header_row]
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
        for i, cell in enumerate(header_row):
            if cell in patterns:
                col_data = df_prod.iloc[1:, i]
                return pd.to_numeric(col_data, errors='coerce').sum()
        return 0
    except Exception:
        return 0

@st.cache_data(ttl=300)
def load_daily_production_dict(selected_dates, production_file):
    """加载每日产量字典，生产文件只读取一次"""
    if not os.path.exists(production_file):
        return {}
    try:
        df_prod = pd.read_excel(production_file, header=None, dtype=str)
    except Exception:
        return {}
    header_row = df_prod.iloc[0].fillna("").astype(str).str.strip()
    header_row = [re.sub(r"[\s　\n\r\t]+", "", x) for x in header_row]
    values = df_prod.iloc[1:]
    prod_dict = {}
    for d in selected_dates:
        try:
            dt = pd.to_datetime(d, format='%Y%m%d')
        except Exception:
            prod_dict[d] = 0
            continue
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
        col_idx = next((i for i, cell in enumerate(header_row) if cell in patterns), None)
        if col_idx is not None:
            col_data = values.iloc[:, col_idx]
            prod_dict[d] = pd.to_numeric(col_data, errors='coerce').sum()
        else:
            prod_dict[d] = 0
    return prod_dict

# ---------- 主数据加载函数 ----------
@st.cache_data(ttl=300)
def load_rule(rule_file):
    if not os.path.exists(rule_file):
        st.error(f"规则文件不存在：{rule_file}")
        st.stop()
    df_rule = pd.read_excel(rule_file, sheet_name=0, header=1)
    df_rule = df_rule.iloc[:, 1:5]
    df_rule.columns = ["MES代码", "病象", "分类", "车间"]
    df_rule["MES代码"] = df_rule["MES代码"].astype(str)
    code_to_cause = dict(zip(df_rule["MES代码"], df_rule["病象"]))
    code_to_shop = dict(zip(df_rule["MES代码"], df_rule["车间"]))
    cause_to_shop = dict(zip(df_rule["病象"], df_rule["车间"]))
    return code_to_cause, code_to_shop, cause_to_shop

@st.cache_data(ttl=300)
def load_raw(selected_dates, raw_dir):
    """加载原始数据，合并多日期文件"""
    all_df = []
    for d in selected_dates:
        fp1 = os.path.join(raw_dir, f"{d}.xls")
        fp2 = os.path.join(raw_dir, f"{d}.xlsx")
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

@st.cache_data(ttl=300)
def load_production(selected_dates, production_file):
    """加载总产量"""
    if not os.path.exists(production_file):
        return None
    total = 0
    for d in selected_dates:
        total += extract_single_daily_production(production_file, d)
    return total

@st.cache_data(ttl=300)
def load_daily_production_dict(selected_dates, production_file):
    """加载每日产量字典"""
    if not os.path.exists(production_file):
        return {}
    prod_dict = {}
    for d in selected_dates:
        prod_dict[d] = extract_single_daily_production(production_file, d)
    return prod_dict

@st.cache_data(ttl=300)
def load_uf_check_data(uf_data_dir):
    """加载UF检查数据"""
    UF_COLUMNS = [
        "CWRFVOA_kgf", "CWRFVOA1H_kgf", "CWLFVOA_kgf",
        "CCWRFVOA_kgf", "CCWRFVOA1H_kgf", "CCWLFVOA_kgf",
        "CON_kgf", "Upper_g", "Lower_g"
    ]
    all_uf = []
    if not os.path.exists(uf_data_dir):
        return pd.DataFrame(columns=["条码"] + UF_COLUMNS)
    for fname in os.listdir(uf_data_dir):
        if fname.startswith("UFDATA_") and (fname.endswith(".xls") or fname.endswith(".xlsx")):
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
                df_uf["条码"] = df_uf["条码"].apply(full_to_half)
                available = [c for c in UF_COLUMNS if c in df_uf.columns]
                df_uf = df_uf[["条码"] + available].copy()
                all_uf.append(df_uf)
            except Exception as e:
                st.warning(f"读取UF文件失败：{file_path} - {e}")
    if all_uf:
        return pd.concat(all_uf, ignore_index=True)
    return pd.DataFrame(columns=["条码"] + UF_COLUMNS)

# ---------- 派生字段（核心数据处理）----------
def derive_columns(df, code_to_cause, code_to_shop, cause_to_shop):
    """
    为原始数据添加派生字段：类型、病象、车间、成型、硫化等
    返回处理后的DataFrame
    """
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

    # 向量化病象/车间映射，避免逐行遍历
    if col_u:
        code_series = df[col_u].astype(str).apply(clean_str)
    else:
        code_series = pd.Series([""] * len(df), index=df.index)
    if col_r:
        reason_series = df[col_r].astype(str).apply(clean_str)
    else:
        reason_series = pd.Series([""] * len(df), index=df.index)

    mapped_causes = code_series.map(code_to_cause)
    mapped_shops = code_series.map(code_to_shop)
    fallback_shops = reason_series.map(cause_to_shop)

    df["病象"] = mapped_causes.fillna(reason_series)
    df["车间"] = mapped_shops.fillna(fallback_shops).fillna("未知")

    if col_vul:
        df["硫化日期"] = pd.to_datetime(df[col_vul], errors="coerce")
        df["统计日期"] = df["硫化日期"].apply(
            lambda x: (x - timedelta(days=1)).date() if pd.notna(x) and x.hour < 8 else x.date() if pd.notna(x) else None
        )

    rename_map = {
        "模具位置": "位置", "上下模": "位置", "硫化机台": "硫化",
        "成型主手": "成型主手", "花纹": "花纹", "规格": "规格",
        "成型时间": "成型时间", "硫化人": "硫化主手", "条码": "条码"
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