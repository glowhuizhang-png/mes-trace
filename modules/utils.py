import re
import pandas as pd
import numpy as np

def full_to_half(text):
    if isinstance(text, pd.Series):
        return text.fillna("").astype(str).str.translate(str.maketrans('０１２３４５６７８９', '0123456789')).str.replace('\u3000', '', regex=False).str.strip()
    if pd.isna(text):
        return ""
    s = str(text).strip()
    s = s.translate(str.maketrans('０１２３４５６７８９', '0123456789'))
    s = s.replace('\u3000', '').strip()
    return s

def clean_str(x):
    if isinstance(x, pd.Series):
        return x.fillna("").astype(str).str.replace("　", " ", regex=False).str.replace(r"[\n\r\t]", "", regex=True).str.strip()
    if pd.isna(x):
        return ""
    s = str(x).strip().replace("　", " ")
    s = re.sub(r"[\n\r\t]", "", s)
    return s

def find_col(df, candidates):
    cols = [re.sub(r'\s+', '', str(c)) for c in df.columns]
    for cand in candidates:
        cand_clean = re.sub(r'\s+', '', cand)
        for i, real in enumerate(cols):
            if cand_clean == real:
                return df.columns[i]
    return None

def extract_chinese(text):
    if isinstance(text, pd.Series):
        return text.fillna("").astype(str).apply(lambda x: ' '.join(re.findall(r'[\u4e00-\u9fff]+', x)) if re.findall(r'[\u4e00-\u9fff]+', x) else x)
    if pd.isna(text):
        return ""
    chinese = re.findall(r'[\u4e00-\u9fff]+', str(text))
    return ' '.join(chinese) if chinese else str(text)

def short_name(text):
    if isinstance(text, pd.Series):
        return text.fillna("").astype(str).str.strip().str[-3:].where(text.str.len() >= 3, text)
    if pd.isna(text):
        return ""
    s = str(text).strip()
    return s[-3:] if len(s) >= 3 else s