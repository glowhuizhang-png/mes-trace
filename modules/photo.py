import os
import streamlit as st
import base64

@st.cache_resource
def build_photo_index(photo_base_dir):
    """构建条码→图片路径索引（缓存）"""
    photo_index = {}
    if not os.path.exists(photo_base_dir):
        return photo_index
    for root, _, files in os.walk(photo_base_dir):
        for file in files:
            if file.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif')):
                barcode = os.path.splitext(file)[0]
                photo_index[barcode] = os.path.abspath(os.path.join(root, file))
    return photo_index

def get_photo_data(photo_index, barcode):
    """
    根据条码获取图片的 base64 数据和有效条码。
    返回 (display_barcode, base64_str) 或 (None, None)
    """
    if not photo_index:
        return None, None
    barcode = str(barcode).strip()
    img_path = photo_index.get(barcode)
    if img_path is None:
        # 模糊匹配
        matched = [k for k in photo_index if barcode in k]
        if matched:
            barcode = matched[0]
            img_path = photo_index[barcode]
    if img_path is None or not os.path.exists(img_path):
        return None, None
    try:
        with open(img_path, "rb") as f:
            data = base64.b64encode(f.read()).decode()
        return barcode, data
    except Exception:
        return None, None

def trigger_image_popup(barcode, photo_index, fuzzy=False):
    """旧版兼容函数（已弃用，建议使用 get_photo_data）"""
    if photo_index is None:
        return
    barcode, data = get_photo_data(photo_index, barcode)
    if barcode is None:
        st.warning(f"未找到 {barcode} 图片")
        return
    st.session_state["selected_photo"] = {"barcode": barcode, "data": data}

def render_photo_panel():
    """旧版面板（已弃用）"""
    pass