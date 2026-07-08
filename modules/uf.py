# modules/uf.py

import streamlit as st
import pandas as pd

UF_COLUMNS = [
    "CWRFVOA_kgf",
    "CWRFVOA1H_kgf",
    "CWLFVOA_kgf",
    "CCWRFVOA_kgf",
    "CCWRFVOA1H_kgf",
    "CCWLFVOA_kgf",
    "CON_kgf",
    "Upper_g",
    "Lower_g"
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


def render_uf_detail_table(
    df,
    uf_check_df,
    key_prefix,
    height=680
):
    """UF 明细数据"""

    if not uf_check_df.empty:
        df = df.copy()
        uf_check_df = uf_check_df.copy()

        df["条码"] = df["条码"].astype(str).str.strip()
        uf_check_df["条码"] = uf_check_df["条码"].astype(str).str.strip()

        merged = df.merge(
            uf_check_df,
            on="条码",
            how="left"
        )

    else:
        merged = df.copy()

        for c in UF_COLUMNS:
            merged[c] = None

    if merged.empty:
        st.info("无UF次品数据")
        return

    merged = merged.sort_values(
        ["成型", "规格", "成型主手"]
    )

    # ------------------------
    # 筛选
    # ------------------------

    col1, col2, col3 = st.columns(3)

    with col1:
        machines = ["全部"] + sorted(
            merged["成型"].dropna().astype(str).unique().tolist()
        )

        selected_machine = st.selectbox(
            "⚙️ 成型",
            machines,
            key=f"uf_machine_{key_prefix}"
        )

    with col2:
        specs = ["全部"] + sorted(
            merged["规格"].dropna().astype(str).unique().tolist()
        )

        selected_spec = st.selectbox(
            "📏 规格",
            specs,
            key=f"uf_spec_{key_prefix}"
        )

    with col3:
        patterns = ["全部"] + sorted(
            merged["花纹"].dropna().astype(str).unique().tolist()
        )

        selected_pattern = st.selectbox(
            "🎨 花纹",
            patterns,
            key=f"uf_pattern_{key_prefix}"
        )

    filtered = merged.copy()

    if selected_machine != "全部":
        filtered = filtered[
            filtered["成型"] == selected_machine
        ]

    if selected_spec != "全部":
        filtered = filtered[
            filtered["规格"] == selected_spec
        ]

    if selected_pattern != "全部":
        filtered = filtered[
            filtered["花纹"] == selected_pattern
        ]

    if filtered.empty:
        st.warning("无符合条件的数据")
        return

    # ------------------------
    # 显示列
    # ------------------------

    base_cols = [
        "条码",
        "成型",
        "硫化",
        "成型时间",
        "成型主手",
        "规格",
        "花纹"
    ]

    base_cols = [
        c for c in base_cols
        if c in filtered.columns
    ]

    show_cols = base_cols + UF_COLUMNS

    filtered_display = (
        filtered[show_cols]
        .rename(columns=UF_HEADER_MAP)
    )

    st.markdown(
        "<div class='table-header'>📋 UF 明细数据（含检查指标）</div>",
        unsafe_allow_html=True
    )

    st.dataframe(
        filtered_display,
        use_container_width=True,
        height=height,
        hide_index=True,
        key=f"uf_table_{key_prefix}"
    )