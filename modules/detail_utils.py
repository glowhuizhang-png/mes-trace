import streamlit as st
import pandas as pd
from modules.photo import trigger_image_popup

DEFAULT_DISPLAY_COLS = ["病象", "条码", "硫化", "硫化主手", "硫化日期", "成型", "成型时间", "成型主手", "规格", "花纹", "位置", "车间"]

def render_summary_table(summary_df, key_prefix, height=480):
    if summary_df.empty:
        st.info("无汇总数据")
        return None
    st.caption("单击行查看明细")
    event = st.dataframe(summary_df, use_container_width=True, hide_index=True, height=height, selection_mode="single-row", on_select="rerun", key=f"summary_{key_prefix}")
    return event

def render_detail_table(df, key_prefix, height=450, enable_click=True, photo_index=None, show_filters=True, use_buttons=False):
    if df.empty:
        st.info("无数据")
        return
    filtered_df = df.copy()
    display_cols = [c for c in DEFAULT_DISPLAY_COLS if c in filtered_df.columns]

    # 处理高度：允许 'content' 或正整数，None 转为 'content'
    if height is None:
        height = "content"

    event = st.dataframe(
        filtered_df[display_cols],
        use_container_width=True,
        hide_index=True,
        height=height,
        selection_mode="single-row",
        on_select="rerun",
        key=f"detail_table_{key_prefix}"
    )

    if enable_click and photo_index is not None and event.selection.rows:
        row = event.selection.rows[0]
        barcode = str(filtered_df.iloc[row]["条码"])
        state_key = f"last_barcode_{key_prefix}"
        last = st.session_state.get(state_key)
        if barcode != last:
            st.session_state[state_key] = barcode
            trigger_image_popup(barcode, photo_index)
    st.session_state["dashboard_detail"] = filtered_df