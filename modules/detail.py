import streamlit as st
import pandas as pd
from modules.photo import trigger_image_popup

def render_summary_table(summary_df, key_prefix, height=480):
    """渲染汇总表（用于外观废次品分析左侧表格）"""
    if summary_df.empty:
        st.info("无汇总数据")
        return None
    st.caption("单击行查看该病象/车间的条码明细")
    event = st.dataframe(
        summary_df,
        width='stretch',
        height=height,
        hide_index=True,
        selection_mode="single-row",
        on_select="rerun",
        key=f"summary_{key_prefix}"
    )
    return event


def render_detail_table(df, key_prefix, height=680, enable_click=True, photo_index=None):
    """渲染明细表（外观废次品、废品、次品外观的明细）"""
    if df.empty:
        st.info("无数据")
        return

    shop_order = ["密炼", "部件", "部件成型", "成型", "硫化", "工程", "工艺"]
    all_shops = df["车间"].dropna().astype(str).unique().tolist()
    sorted_shops = [s for s in shop_order if s in all_shops] + sorted([s for s in all_shops if s not in shop_order])
    shops = ["全部"] + sorted_shops
    causes = ["全部"] + sorted(df["病象"].dropna().astype(str).unique().tolist())
    machines = ["全部"] + sorted(df["成型"].dropna().astype(str).unique().tolist())
    masters = ["全部"] + sorted(df["成型主手"].dropna().astype(str).unique().tolist())
    vul_machines = ["全部"] + sorted(df["硫化"].dropna().astype(str).unique().tolist())
    vul_workers = ["全部"] + sorted(df["硫化主手"].dropna().astype(str).unique().tolist())

    cols = st.columns(6)
    with cols[0]:
        selected_shop = st.selectbox("🏭 车间", shops, key=f"shop_{key_prefix}")
    with cols[1]:
        selected_cause = st.selectbox("🔍 病象", causes, key=f"cause_{key_prefix}")
    with cols[2]:
        selected_machine = st.selectbox("⚙️ 成型", machines, key=f"machine_{key_prefix}")
    with cols[3]:
        selected_master = st.selectbox("👤 成型主手", masters, key=f"master_{key_prefix}")
    with cols[4]:
        selected_vul_machine = st.selectbox("🔥 硫化", vul_machines, key=f"vul_machine_{key_prefix}")
    with cols[5]:
        selected_vul_worker = st.selectbox("👨‍🏭 硫化主手", vul_workers, key=f"vul_worker_{key_prefix}")

    filtered_df = df.copy()
    if selected_shop != "全部":
        filtered_df = filtered_df[filtered_df["车间"] == selected_shop]
    if selected_cause != "全部":
        filtered_df = filtered_df[filtered_df["病象"] == selected_cause]
    if selected_machine != "全部":
        filtered_df = filtered_df[filtered_df["成型"] == selected_machine]
    if selected_master != "全部":
        filtered_df = filtered_df[filtered_df["成型主手"] == selected_master]
    if selected_vul_machine != "全部":
        filtered_df = filtered_df[filtered_df["硫化"] == selected_vul_machine]
    if selected_vul_worker != "全部":
        filtered_df = filtered_df[filtered_df["硫化主手"] == selected_vul_worker]

    if filtered_df.empty:
        st.warning("无符合条件的数据")
        return

    show_cols = ["病象", "条码", "硫化", "硫化主手", "硫化日期",
                 "成型", "成型时间", "成型主手", "规格", "花纹", "位置", "车间"]
    show_cols = [c for c in show_cols if c in filtered_df.columns]

    st.markdown("<div class='table-header'>📋 明细数据</div>", unsafe_allow_html=True)

    if enable_click and photo_index is not None:
        event = st.dataframe(
            filtered_df[show_cols],
            width='stretch',
            height=height,
            hide_index=True,
            selection_mode="single-row",
            on_select="rerun",
            key=f"detail_table_{key_prefix}"
        )
        if event.selection.rows:
            selected_row = event.selection.rows[0]
            barcode = str(filtered_df.iloc[selected_row]["条码"])
            trigger_image_popup(barcode, photo_index)
    else:
        st.dataframe(
            filtered_df[show_cols],
            width='stretch',
            height=height,
            hide_index=True,
            key=f"detail_table_{key_prefix}"
        )


def render_waste_appearance_analysis(combined_df, photo_index, waste_df, app_df, df_full, selected_dates, shop_order_list):
    """
    完整的外观废次品分析模块（包含汇总、明细、机台统计）
    """
    st.subheader("外观废次品分析")

    # ---------- 1. 汇总表与明细交互 ----------
    combined = combined_df.copy()
    type_order = {"废品": 0, "次品外观": 1}
    combined["类型排序"] = combined["类型"].map(type_order)
    combined["车间排序"] = combined["车间"].apply(lambda x: shop_order_list.index(x) if x in shop_order_list else 99)
    combined = combined.sort_values(["类型排序", "车间排序", "病象", "成型", "规格"])
    combined.drop(columns=["类型排序", "车间排序"], inplace=True)

    summary = combined.groupby(["病象", "车间"]).agg(
        总数=("类型", "count"),
        废品=("类型", lambda x: (x == "废品").sum()),
        次品=("类型", lambda x: (x == "次品外观").sum())
    ).reset_index()
    summary = summary[["病象", "总数", "废品", "次品", "车间"]].sort_values("总数", ascending=False)

    col_left, col_right = st.columns([1, 1.3])
    with col_left:
        event_summary = render_summary_table(summary, key_prefix="app", height=480)

    with col_right:
        if event_summary and event_summary.selection.rows:
            selected_row = event_summary.selection.rows[0]
            selected_data = summary.iloc[selected_row]
            selected_cause = selected_data["病象"]
            selected_shop = selected_data["车间"]
            detail = combined[(combined["病象"] == selected_cause) & (combined["车间"] == selected_shop)]
            if not detail.empty:
                detail_cols = ["条码", "类型", "成型", "硫化", "规格", "花纹", "成型主手", "硫化主手"]
                detail_cols = [c for c in detail_cols if c in detail.columns]
                st.markdown(f"**{selected_cause}（{selected_shop}）的明细**")
                # ---------- 修改点：将高度从 680 改为 480，与左侧汇总表一致 ----------
                event_detail = st.dataframe(
                    detail[detail_cols],
                    width='stretch',
                    height=480,          # 修改为480
                    hide_index=True,
                    selection_mode="single-row",
                    on_select="rerun",
                    key=f"detail_summary_{selected_row}"
                )
                if event_detail.selection.rows:
                    detail_row = event_detail.selection.rows[0]
                    barcode = str(detail.iloc[detail_row]["条码"])
                    trigger_image_popup(barcode, photo_index)
            else:
                st.info("无明细数据")
        else:
            st.info("请单击左侧表格的行查看明细")

    # ---------- 2. 下方明细切换 ----------
    st.divider()
    waste_type = st.radio("选择明细类型", ["全选", "废品", "外观次品"], horizontal=True)
    if waste_type == "全选":
        render_detail_table(combined, "all_detail", height=680, enable_click=False, photo_index=None)
    elif waste_type == "废品":
        render_detail_table(waste_df, "waste_detail", height=680, enable_click=True, photo_index=photo_index)
    else:
        render_detail_table(app_df, "app_detail", height=680, enable_click=True, photo_index=photo_index)

    # ---------- 3. 机台统计（精简为两行） ----------
    st.divider()
    st.subheader("机台统计")

    col1, col2 = st.columns(2)
    with col1:
        stat_type = st.radio("统计类型", ["日期统计", "病象统计"], horizontal=True, key="stat_type")
    with col2:
        dimension = st.radio("统计维度", ["全部", "成型", "硫化"], horizontal=True, key="machine_dimension")

    if dimension == "硫化":
        base_data = df_full[(df_full["车间"] == "硫化") & (df_full["类型"].isin(["废品", "次品外观"]))]
        group_col = "硫化"
    elif dimension == "成型":
        base_data = df_full[((df_full["车间"] == "成型") | (df_full["类型"] == "次品UF")) & (df_full["类型"].isin(["废品", "次品外观", "次品UF"]))]
        group_col = "成型"
    else:
        base_data = df_full[df_full["类型"].isin(["废品", "次品外观", "次品UF"])]
        group_col = "成型"

    col3, col4, col5 = st.columns(3)
    with col3:
        type_filter = st.selectbox("类型", ["全部", "废品", "次品", "UF次品"], key="machine_date_type")
    with col4:
        available_shops = base_data["车间"].dropna().unique().tolist()
        sorted_shop_options = ["全部"] + [s for s in shop_order_list if s in available_shops] + [s for s in available_shops if s not in shop_order_list]
        selected_shop_machine = st.selectbox("🏭 车间", sorted_shop_options, key="machine_date_shop")
    with col5:
        filtered_temp = base_data.copy()
        if type_filter == "废品":
            filtered_temp = filtered_temp[filtered_temp["类型"] == "废品"]
        elif type_filter == "次品":
            filtered_temp = filtered_temp[filtered_temp["类型"] == "次品外观"]
        elif type_filter == "UF次品":
            filtered_temp = filtered_temp[filtered_temp["类型"] == "次品UF"]
        if selected_shop_machine != "全部":
            filtered_temp = filtered_temp[filtered_temp["车间"] == selected_shop_machine]
        defect_options = ["全部"] + sorted(filtered_temp["病象"].dropna().unique().tolist())
        selected_defect = st.selectbox("🔍 缺陷", defect_options, key="machine_date_defect")

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