import streamlit as st
import os
from PIL import Image
from modules.utils import full_to_half

@st.cache_resource
def build_photo_index(photo_base_dir):
    """构建条码到照片路径的映射"""
    photo_map = {}
    if not os.path.exists(photo_base_dir):
        return photo_map
    for root, dirs, files in os.walk(photo_base_dir):
        for file in files:
            if file.lower().endswith((".jpg", ".jpeg", ".png", ".bmp", ".gif")):
                barcode = os.path.splitext(file)[0]
                # 若同一barcode有多个图片，取第一个
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
        st.image(img, width=700)
    except Exception as e:
        st.error(f"无法打开图片: {e}")

def trigger_image_popup(barcode, photo_index):
    fp = find_photo(barcode, photo_index)
    if fp:
        show_big_image(fp)
    else:
        st.warning(f"未找到图片，条码：{barcode}")