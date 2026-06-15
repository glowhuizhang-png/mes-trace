import re
import pandas as pd

def full_to_half(text):
    """全角数字转半角，并去除全角空格"""
    if pd.isna(text):
        return ""
    s = str(text).strip()
    full = '０１２３４５６７８９'
    half = '0123456789'
    trans = str.maketrans(full, half)
    s = s.translate(trans)
    s = s.replace('\u3000', '').strip()
    return s

def clean_str(x):
    """清理字符串：去除首尾空格、替换全角空格、移除换行符"""
    if pd.isna(x):
        return ""
    s = str(x).strip()
    s = s.replace("　", " ")
    s = re.sub(r"[\n\r\t]", "", s)
    return s

def find_col(df, candidates):
    """在DataFrame列名中查找候选列名（忽略大小写和空格）"""
    cols = [clean_str(c) for c in df.columns]
    for cand in candidates:
        cand_clean = clean_str(cand)
        for i, real in enumerate(cols):
            if cand_clean == real:
                return df.columns[i]
    return None

def extract_chinese(text):
    """提取字符串中的中文字符"""
    if pd.isna(text):
        return ""
    chinese = re.findall(r'[\u4e00-\u9fff]+', str(text))
    return ' '.join(chinese) if chinese else str(text)

def short_name(text):
    """取字符串后3位，用于机台简称"""
    if pd.isna(text):
        return ""
    s = str(text).strip()
    return s[-3:] if len(s) >= 3 else s