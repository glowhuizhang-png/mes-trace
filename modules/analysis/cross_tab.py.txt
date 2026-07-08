import streamlit as st
import pandas as pd

def render_pivot_table(df_full, selected_dates, shop_order_list):
    st.subheader("机台统计")
    col1, col2 = st.columns(2)
    with col1:
        stat_type = st.radio("统计类型", ["日期统计", "病象统计"], horizontal=True, key="stat_type")
    with col2:
        dimension = st.radio("统计维度", ["全部", "成型", "硫化"], horizontal=True, key="machine_dimension")

    col3, col4, col5 = st.columns(3)
    with col3:
        type_filter = st.selectbox("类型", ["全部", "废品", "次品", "UF次品"], key="machine_date_type")
    with col4:
        shops = ["全部"] + [s for s in shop_order_list if s in df_full["车间"].unique()] + [s for s in df_full["车间"].unique() if s not in shop_order_list]
        selected_shop = st.selectbox("🏭 车间", shops, key="machine_date_shop")
    with col5:
        # 动态缺陷选项
        temp = df_full.copy()
        if type_filter != "全部":
            type_map = {"废品":"废品","次品":"次品外观","UF次品":"次品UF"}
            temp = temp[temp["类型"] == type_map[type_filter]]
        if selected_shop != "全部":
            temp = temp[temp["车间"] == selected_shop]
        defect_options = ["全部"] + sorted(temp["病象"].dropna().unique())
        selected_defect = st.selectbox("🔍 缺陷", defect_options, key="machine_date_defect")

    # 准备数据
    if dimension == "硫化":
        base = df_full[(df_full["车间"]=="硫化") & (df_full["类型"].isin(["废品","次品外观"]))]
        group_col = "硫化"
    elif dimension == "成型":
        base = df_full[((df_full["车间"]=="成型")|(df_full["类型"]=="次品UF")) & (df_full["类型"].isin(["废品","次品外观","次品UF"]))]
        group_col = "成型"
    else:
        base = df_full[df_full["类型"].isin(["废品","次品外观","次品UF"])]
        group_col = "成型"

    if type_filter != "全部":
        type_map = {"废品":"废品","次品":"次品外观","UF次品":"次品UF"}
        base = base[base["类型"] == type_map[type_filter]]
    if selected_shop != "全部":
        base = base[base["车间"] == selected_shop]
    if selected_defect != "全部":
        base = base[base["病象"] == selected_defect]

    if base.empty:
        st.info("无数据")
        return

    if stat_type == "日期统计":
        pivot = base.pivot_table(index=group_col, columns="文件日期", aggfunc="size", fill_value=0)
        sorted_dates = sorted(selected_dates)
        date_cols = [d for d in sorted_dates if d in pivot.columns]
        pivot = pivot[date_cols] if date_cols else pivot
        pivot.insert(0, "合计", pivot.sum(axis=1))
        pivot = pivot.reset_index().sort_values("合计", ascending=False)
        pivot.columns = [group_col] + ["合计"] + [pd.to_datetime(c, format='%Y%m%d').strftime('%m/%d') for c in date_cols]
    else:
        pivot = base.pivot_table(index=group_col, columns="病象", aggfunc="size", fill_value=0)
        pivot["合计"] = pivot.sum(axis=1)
        pivot = pivot.sort_values("合计", ascending=False)
        cols = ["合计"] + [c for c in pivot.columns if c != "合计"]
        pivot = pivot[cols].reset_index()

    st.data_editor(pivot, disabled=True, use_container_width=True, height=680, hide_index=True, key="machine_editor")