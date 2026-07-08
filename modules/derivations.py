import pandas as pd
import numpy as np
from datetime import timedelta
from modules.utils import clean_str, find_col, full_to_half, extract_chinese, short_name

def derive_columns(df, code_to_cause, code_to_shop, cause_to_shop):
    df = df.copy()
    col_detect = find_col(df, ["检测分类", "分类"])
    col_reason = find_col(df, ["溯源原因简码", "原因简码", "简码", "原因代码"])
    col_r = find_col(df, ["检测原因"])
    col_u = find_col(df, ["缺陷原因"])
    col_build = find_col(df, ["成型机台", "成型设备", "机台"])
    col_vul = find_col(df, ["硫化日期", "日期"])

    df["成型"] = df[col_build].apply(short_name) if col_build else "未知"

    # 类型：严格按照原始逻辑逐条赋值（先废品、返修，再 MBA/MBB）
    df["类型"] = "其他"
    if col_detect:
        ser_detect = df[col_detect].astype(str).str.strip()
        df.loc[ser_detect == "废品", "类型"] = "废品"
        df.loc[ser_detect == "返修", "类型"] = "返修"
    if col_reason:
        ser_reason = df[col_reason].astype(str).str.strip()
        df.loc[ser_reason == "MBA", "类型"] = "次品外观"
        df.loc[ser_reason == "MBB", "类型"] = "次品UF"

    # 病象
    if col_u:
        df["病象"] = df[col_u].astype(str).map(code_to_cause).fillna("")
    else:
        df["病象"] = ""
    if col_r:
        mask = (df["病象"] == "")
        df.loc[mask, "病象"] = df.loc[mask, col_r].astype(str)

    # 车间
    df["车间"] = df["病象"].map(cause_to_shop).fillna("未知")

    # 硫化日期与统计日期
    if col_vul:
        df["硫化日期"] = pd.to_datetime(df[col_vul], errors="coerce")
        df["统计日期"] = df["硫化日期"].apply(
            lambda x: (x - timedelta(days=1)).date() if pd.notna(x) and x.hour < 8 else (x.date() if pd.notna(x) else None)
        )

    # 列重命名
    rename_map = {
        "模具位置":"位置", "上下模":"位置", "硫化机台":"硫化",
        "成型主手":"成型主手", "花纹":"花纹", "规格":"规格",
        "成型时间":"成型时间", "硫化人":"硫化主手", "条码":"条码"
    }
    for old, new in rename_map.items():
        if old in df.columns:
            df.rename(columns={old: new}, inplace=True)

    # 条码处理
    if "条码" in df.columns:
        df["条码"] = full_to_half(df["条码"])
        df["条码"] = df["条码"].astype(str).str.replace(r'\.0$', '', regex=True)

    if "位置" in df.columns:
        df["位置"] = extract_chinese(df["位置"])

    if "硫化" in df.columns:
        df["硫化"] = df["硫化"].apply(short_name)

    return df