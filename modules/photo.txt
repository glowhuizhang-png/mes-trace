import os
import streamlit as st

@st.cache_resource
def build_photo_index(photo_base_dir):
    photo_index = {}
    if not os.path.exists(photo_base_dir):
        return photo_index
    for root, _, files in os.walk(photo_base_dir):
        for file in files:
            if file.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif')):
                barcode = os.path.splitext(file)[0]
                photo_index[barcode] = os.path.join(root, file)
    return photo_index

def trigger_image_popup(barcode, photo_index, fuzzy=False):
    if photo_index is None:
        return
    barcode = str(barcode).strip()
    img_path = photo_index.get(barcode)
    if img_path is None and fuzzy:
        matched = [k for k in photo_index if barcode in k]
        if matched:
            barcode = matched[0]
            img_path = photo_index[barcode]
    if img_path is None:
        st.warning(f"未找到 {barcode} 图片")
        return
    # 设置全局弹出状态，使用 popup_photo 避免与旧键冲突
    st.session_state["selected_photo"] = {"barcode": barcode, "path": img_path}

def render_photo_panel():
    st.subheader("📷 图片查看")
    photo = st.session_state.get("selected_photo")
    if photo is None:
        st.info("点击明细条码查看图片")
        return
    st.caption(f"条码：{photo['barcode']}")
    st.image(photo["path"], use_container_width=True)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("❌ 清除", key="clear_photo"):
            del st.session_state["selected_photo"]
            st.rerun()
    with col2:
        with open(photo["path"], "rb") as f:
            st.download_button("⬇ 下载", data=f, file_name=os.path.basename(photo["path"]),
                               use_container_width=True, key="download_photo")