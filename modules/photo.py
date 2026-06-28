import streamlit as st
import os
from PIL import Image
from modules.utils import full_to_half

def build_photo_index(photo_base_dir):
    """扫描照片目录，建立条码到文件路径的映射（无缓存）"""
    photo_map = {}
    if not os.path.exists(photo_base_dir):
        return photo_map
    for root, _, files in os.walk(photo_base_dir):
        for file in files:
            if file.lower().endswith((".jpg", ".jpeg", ".png")):
                barcode = os.path.splitext(file)[0]
                # 若存在重复条码，保留第一个（或改为覆盖，取决于需求）
                if barcode not in photo_map:
                    photo_map[barcode] = os.path.join(root, file)
    return photo_map

def find_photo(barcode, photo_index):
    barcode = full_to_half(str(barcode).strip())
    return photo_index.get(barcode)

@st.dialog("轮胎照片", width="large")
def show_big_image(img_path):
    try:
        img = Image.open(img_path)
        st.image(img, use_container_width=True)  # 自适应宽度
    except Exception as e:
        st.warning(f"图片加载失败：{e}")

import time

def trigger_image_popup(barcode, photo_index):
    # 防抖：如果 2 秒内已经弹过，则忽略
    now = time.time()
    if "last_popup_time" in st.session_state and (now - st.session_state.last_popup_time) < 2:
        return
    fp = find_photo(barcode, photo_index)
    if fp:
        st.session_state.last_popup_time = now
        show_big_image(fp)
    else:
        st.warning(f"未找到图片：{barcode}")