import streamlit as st
import pandas as pd

def render_machine_statistics(df, selected_dates, shop_order_list):
    """
    渲染机台统计部分（两行布局）
    df: 完整数据（已派生）
    selected_dates: 当前选择的日期列表
    shop_order_list: 车间排序列表
    """
    st.subheader("机台统计")

    stat_type = st.radio("统计类型", ["日期统计", "病象统计"], horizontal=True, key="stat_type")
    dimension = st.radio("统计维度", ["全部", "成型", "硫化"], horizontal=True, key="machine_dimension")

    # 第一行：统计类型 + 统计维度
    col1, col2 = st.columns(2)
    with col1:
        stat_type = st.radio("统计类型", ["日期统计", "病象统计"], horizontal=True, key="stat_type_outer")
    with col2:
        dimension = st.radio("统计维度", ["全部", "成型", "硫化"], horizontal=True, key="machine_dimension_outer")

    # 第二行：类型、车间、缺陷（三个下拉框）
    col3, col4, col5 = st.columns(3)
    with col3:
        type_filter = st.selectbox("类型", ["全部", "废品", "次品", "UF次品"], key="machine_date_type")
    with col4:
        # 车间下拉
        available_shops = df["车间"].dropna().unique().tolist()
        sorted_shop_options = ["全部"] + [s for s in shop_order_list if s in available_shops] + [s for s in available_shops if s not in shop_order_list]
        selected_shop_machine = st.selectbox("车间", sorted_shop_options, key="machine_date_shop")
    with col5:
        # 缺陷下拉（依赖前面的过滤）
        filtered_temp = df.copy()
        if type_filter == "废品":
            filtered_temp = filtered_temp[filtered_temp["类型"] == "废品"]
        elif type_filter == "次品":
            filtered_temp = filtered_temp[filtered_temp["类型"] == "次品外观"]
        elif type_filter == "UF次品":
            filtered_temp = filtered_temp[filtered_temp["类型"] == "次品UF"]
        if selected_shop_machine != "全部":
            filtered_temp = filtered_temp[filtered_temp["车间"] == selected_shop_machine]
        defect_options = ["全部"] + sorted(filtered_temp["病象"].dropna().unique().tolist())
        selected_defect = st.selectbox("缺陷", defect_options, key="machine_date_defect")

    # 根据维度确定分组列
    if dimension == "硫化":
        base_data = df[(df["车间"] == "硫化") & (df["类型"].isin(["废品", "次品外观"]))]
        group_col = "硫化"
    else:
        if dimension == "成型":
            base_data = df[((df["车间"] == "成型") | (df["类型"] == "次品UF")) & (df["类型"].isin(["废品", "次品外观", "次品UF"]))]
        else:
            base_data = df[df["类型"].isin(["废品", "次品外观", "次品UF"])]
        group_col = "成型"

    # 应用过滤
    if type_filter == "废品":
        base_data = base_data[base_data["类型"] == "废品"]
    elif type_filter == "次品":
        base_data = base_data[base_data["类型"] == "次品外观"]
    elif type_filter == "UF次品":
        base_data = base_data[base_data["类型"] == "次品UF"]
    if selected_shop_machine != "全部":
        base_data = base_data[base_data["车间"] == selected_shop_machine]
    if selected_defect != "全部":
        base_data = base_data[base_data["病象"] == selected_defect]

    # 生成透视表
    if not base_data.empty:
        if stat_type == "日期统计":
            if selected_dates:
                pivot = base_data.groupby([group_col, "文件日期"]).size().unstack(fill_value=0)
                sorted_dates = sorted(selected_dates)
                date_columns = [d for d in sorted_dates if d in pivot.columns]
                if not date_columns:
                    date_columns = sorted(pivot.columns.tolist())
                pivot = pivot[date_columns]
                pivot.insert(0, "合计", pivot.sum(axis=1))
                rename_dates = {d: pd.to_datetime(d, format='%Y%m%d').strftime('%m/%d') for d in date_columns}
                pivot.rename(columns=rename_dates, inplace=True)
                pivot = pivot.reset_index()
                pivot = pivot.sort_values("合计", ascending=False)
                st.data_editor(
                    pivot, disabled=True, use_container_width=True, height=680, hide_index=True, key="machine_date_editor"
                )
            else:
                st.info("请至少选择一个日期")
        else:
            pivot = base_data.groupby([group_col, "病象"]).size().unstack(fill_value=0)
            pivot["合计"] = pivot.sum(axis=1)
            pivot = pivot.sort_values("合计", ascending=False)
            cols = ["合计"] + [c for c in pivot.columns if c != "合计"]
            pivot = pivot[cols]
            pivot = pivot.reset_index()
            st.data_editor(
                pivot, disabled=True, use_container_width=True, height=680, hide_index=True, key="machine_cause_editor"
            )
    else:
        st.info("无数据")