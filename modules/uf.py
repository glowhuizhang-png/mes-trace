# modules/uf.py
import streamlit as st
import pandas as pd
from modules.photo import trigger_image_popup

UF_COLUMNS = [
    "CWRFVOA_kgf", "CWRFVOA1H_kgf", "CWLFVOA_kgf",
    "CCWRFVOA_kgf", "CCWRFVOA1H_kgf", "CCWLFVOA_kgf",
    "CON_kgf", "Upper_g", "Lower_g"
]

UF_HEADER_MAP = {
    "CWRFVOA_kgf": "RVF",
    "CWRFVOA1H_kgf": "R1H",
    "CWLFVOA_kgf": "LFV",
    "CCWRFVOA_kgf": "RFV(ccw)",
    "CCWRFVOA1H_kgf": "R1H(ccw)",
    "CCWLFVOA_kgf": "LFV(ccw)",
    "CON_kgf": "CON",
    "Upper_g": "UPP",
    "Lower_g": "LOW"
}

# ---------- 辅助：安全触发弹窗 ----------
def _safe_trigger_popup(barcode, photo_index):
    if "last_popup_barcode" not in st.session_state:
        st.session_state.last_popup_barcode = None
    if barcode != st.session_state.last_popup_barcode:
        st.session_state.last_popup_barcode = barcode
        trigger_image_popup(barcode, photo_index)


def render_uf_detail_table(df, uf_check_df, key_prefix, height=680, photo_index=None):
    if not uf_check_df.empty:
        df["条码"] = df["条码"].astype(str).str.strip()
        uf_check_df["条码"] = uf_check_df["条码"].astype(str).str.strip()
        merged = df.merge(uf_check_df, on="条码", how="left")
    else:
        merged = df.copy()
        for c in UF_COLUMNS:
            merged[c] = None

    if merged.empty:
        st.info("无UF次品数据")
        return

    merged = merged.sort_values(["成型", "规格", "成型主手"])

    col1, col2, col3 = st.columns(3)
    with col1:
        machines = ["全部"] + sorted(merged["成型"].dropna().astype(str).unique().tolist())
        selected_machine = st.selectbox("⚙️ 成型", machines, key=f"uf_machine_{key_prefix}")
    with col2:
        specs = ["全部"] + sorted(merged["规格"].dropna().astype(str).unique().tolist())
        selected_spec = st.selectbox("📏 规格", specs, key=f"uf_spec_{key_prefix}")
    with col3:
        patterns = ["全部"] + sorted(merged["花纹"].dropna().astype(str).unique().tolist())
        selected_pattern = st.selectbox("🎨 花纹", patterns, key=f"uf_pattern_{key_prefix}")

    filtered = merged.copy()
    if selected_machine != "全部":
        filtered = filtered[filtered["成型"] == selected_machine]
    if selected_spec != "全部":
        filtered = filtered[filtered["规格"] == selected_spec]
    if selected_pattern != "全部":
        filtered = filtered[filtered["花纹"] == selected_pattern]

    if filtered.empty:
        st.warning("无符合条件的数据")
        return

    base_cols = ["条码", "成型", "硫化", "成型时间", "成型主手", "规格", "花纹"]
    base_cols = [c for c in base_cols if c in filtered.columns]
    show_cols = base_cols + UF_COLUMNS
    filtered_display = filtered[show_cols].rename(columns=UF_HEADER_MAP)

    st.markdown("<div class='table-header'>📋 UF 明细数据（含检查指标）</div>", unsafe_allow_html=True)

    # 使用 st.dataframe 支持行选择
    if photo_index is not None:
        # 确保条码列存在
        if "条码" in filtered_display.columns:
            # 注意：filtered_display 中列名已经重命名，但"条码"列保留原名
            event = st.dataframe(
                filtered_display,
                use_container_width=True,
                height=height,
                hide_index=True,
                selection_mode="single-row",
                on_select="rerun",
                key=f"uf_table_{key_prefix}"
            )
            if event.selection.rows:
                selected_row = event.selection.rows[0]
                barcode = str(filtered_display.iloc[selected_row]["条码"])
                _safe_trigger_popup(barcode, photo_index)
        else:
            # 如果没有条码列，仅显示表格
            st.dataframe(
                filtered_display,
                use_container_width=True,
                height=height,
                hide_index=True,
                key=f"uf_table_{key_prefix}"
            )
    else:
        # 如果未提供 photo_index，仅显示表格
        st.dataframe(
            filtered_display,
            use_container_width=True,
            height=height,
            hide_index=True,
            key=f"uf_table_{key_prefix}"
        )