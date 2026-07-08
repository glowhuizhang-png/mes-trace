import streamlit as st
import pandas as pd
import json
import os
import shutil
from pathlib import Path

CORRECTIONS_FILE = "data/corrections.json"

def load_corrections():
    """加载修正记录（条码 -> {车间, 病象}）"""
    if os.path.exists(CORRECTIONS_FILE):
        with open(CORRECTIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_corrections(corrections):
    """保存修正记录"""
    os.makedirs(os.path.dirname(CORRECTIONS_FILE), exist_ok=True)
    with open(CORRECTIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(corrections, f, ensure_ascii=False, indent=2)

def apply_corrections_to_df(df, corrections):
    """将修正记录应用到当前 DataFrame"""
    if not corrections:
        return df
    df_corrected = df.copy()
    for barcode, changes in corrections.items():
        mask = df_corrected["条码"].astype(str) == barcode
        if mask.any():
            if "车间" in changes:
                df_corrected.loc[mask, "车间"] = changes["车间"]
            if "病象" in changes:
                df_corrected.loc[mask, "病象"] = changes["病象"]
    return df_corrected

def backup_file(file_path):
    """备份文件（添加 .bak 后缀）"""
    backup_path = file_path + ".bak"
    shutil.copy2(file_path, backup_path)
    return backup_path

def write_corrections_to_source(raw_dir, corrections, rule_file=None):
    """
    将修正记录写回原始 Excel 文件（按条码匹配）
    注意：会直接修改文件，请确保已备份
    """
    if not corrections:
        st.info("没有修正记录需要应用")
        return False

    # 获取所有原始文件
    raw_files = []
    for ext in ["*.xlsx", "*.xls"]:
        raw_files.extend(Path(raw_dir).glob(ext))

    if not raw_files:
        st.error("未找到原始数据文件")
        return False

    total_updated = 0
    progress_bar = st.progress(0, text="正在更新源文件...")
    total_files = len(raw_files)

    for idx, file_path in enumerate(raw_files):
        try:
            # 备份
            backup_file(file_path)
            # 读取
            df_file = pd.read_excel(file_path)
            # 查找条码列
            barcode_col = None
            for col in df_file.columns:
                if "条码" in str(col):
                    barcode_col = col
                    break
            if barcode_col is None:
                st.warning(f"文件 {file_path.name} 中没有找到条码列，跳过")
                progress_bar.progress((idx+1)/total_files)
                continue

            # 应用修正
            updated = False
            for barcode, changes in corrections.items():
                mask = df_file[barcode_col].astype(str) == barcode
                if mask.any():
                    if "车间" in changes and "车间" in df_file.columns:
                        df_file.loc[mask, "车间"] = changes["车间"]
                        updated = True
                    if "病象" in changes and "病象" in df_file.columns:
                        df_file.loc[mask, "病象"] = changes["病象"]
                        updated = True
            if updated:
                # 保存回原文件
                df_file.to_excel(file_path, index=False)
                total_updated += mask.sum()
            progress_bar.progress((idx+1)/total_files)
        except Exception as e:
            st.error(f"处理文件 {file_path.name} 时出错: {e}")

    progress_bar.empty()
    if total_updated > 0:
        st.success(f"✅ 成功更新 {total_updated} 条记录，共涉及 {len(corrections)} 个条码")
        return True
    else:
        st.warning("没有找到任何可更新的记录，请检查条码是否匹配")
        return False