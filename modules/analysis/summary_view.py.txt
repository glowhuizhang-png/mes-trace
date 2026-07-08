import streamlit as st
import pandas as pd
from modules.photo import trigger_image_popup

def render_summary_with_drilldown(combined_df, photo_index):
    combined = combined_df.copy()
    combined["规格-花纹"] = combined["规格"].astype(str) + " - " + combined["花纹"].astype(str)
    # 排序
    type_order = {"废品": 0, "次品外观": 1}
    shop_order = ["密炼","部件","部件成型","成型","硫化","工程","工艺"]
    combined["type_sort"] = combined["类型"].map(type_order)
    combined["shop_sort"] = combined["车间"].apply(lambda x: shop_order.index(x) if x in shop_order else 99)
    combined = combined.sort_values(["type_sort","shop_sort","病象","成型","规格"])
    # 汇总
    summary = combined.groupby(["病象","车间"]).agg(总数=("类型","count"), 废品=("类型", lambda x: (x=="废品").sum()), 次品=("类型", lambda x: (x=="次品外观").sum())).reset_index()
    summary = summary.sort_values("总数", ascending=False)

    col_left, col_right = st.columns([1, 1.3])
    with col_left:
        event = st.dataframe(summary, use_container_width=True, height=480, hide_index=True, selection_mode="single-row", on_select="rerun", key="summary_app")
    with col_right:
        if event and event.selection.rows:
            row = event.selection.rows[0]
            selected = summary.iloc[row]
            detail = combined[(combined["病象"]==selected["病象"]) & (combined["车间"]==selected["车间"])]
            if not detail.empty:
                display_cols = [c for c in ["条码","类型","成型","硫化","规格","花纹","成型主手","硫化主手"] if c in detail.columns]
                st.markdown(f"**{selected['病象']}（{selected['车间']}）的明细**")
                detail_event = st.dataframe(detail[display_cols], use_container_width=True, height=480, hide_index=True, selection_mode="single-row", on_select="rerun", key=f"detail_summary_{row}")
                if detail_event.selection.rows:
                    barcode = str(detail.iloc[detail_event.selection.rows[0]]["条码"])
                    trigger_image_popup(barcode, photo_index)
            else:
                st.info("无明细数据")
        else:
            st.info("请单击左侧表格的行查看明细")