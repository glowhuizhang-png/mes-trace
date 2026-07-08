import streamlit as st
import pandas as pd
import plotly.express as px
from modules.detail_utils import render_detail_table
from modules.photo import trigger_image_popup

# 全局图片尺寸
IMG_WIDTH = 400
IMG_HEIGHT = 300

def _show_image(barcode, photo_index):
    """在右侧显示固定大小的图片，点击可看原图"""
    if photo_index is None:
        st.warning("照片索引未加载")
        return
    img_path = photo_index.get(str(barcode).strip())
    if img_path:
        # 显示小图，点击弹出大图
        cols = st.columns([1, 3])
        with cols[0]:
            st.image(img_path, width=IMG_WIDTH, caption="点击查看原图")
            if st.button("🔍 查看原图", key=f"full_{barcode}"):
                trigger_image_popup(barcode, photo_index)
    else:
        st.info("未找到图片")

def render_waste_chart(df, photo_index=None):
    waste_df = df[df["类型"] == "废品"]
    if waste_df.empty:
        st.info("无废品数据")
        return

    # ---------- 上方：左侧条形图 + 右侧明细 ----------
    left, right = st.columns([4, 6])
    with left:
        # 水平条形图
        counts = waste_df["病象"].value_counts().reset_index()
        counts.columns = ["病象", "数量"]
        fig = px.bar(counts, y="病象", x="数量", text="数量", orientation='h', title="废品 Pareto")
        fig.update_traces(textposition="outside")
        fig.update_layout(clickmode="event+select", height=450, template="plotly_white", margin=dict(l=10, r=10, t=40, b=10))
        event = st.plotly_chart(fig, use_container_width=True, on_select="rerun", key="waste_hbar")
        selected_cause = None
        if event and event.selection and event.selection.points:
            selected_cause = event.selection.points[0]["y"]
            st.session_state["waste_selected"] = selected_cause

    with right:
        # 明细表：根据选择显示
        cause = st.session_state.get("waste_selected")
        if cause:
            detail = waste_df[waste_df["病象"] == cause]
            st.subheader(f"📋 {cause}")
            render_detail_table(detail, "waste_detail", height=400, enable_click=True, photo_index=photo_index, show_filters=False)
        else:
            st.subheader("📋 全部废品")
            render_detail_table(waste_df, "waste_detail", height=400, enable_click=True, photo_index=photo_index, show_filters=False)

    # ---------- 下方：点击后展开的详细分析区 ----------
    if "waste_selected" in st.session_state:
        selected = st.session_state["waste_selected"]
        detail_df = waste_df[waste_df["病象"] == selected]
        if not detail_df.empty:
            st.divider()
            st.subheader(f"🔍 深入分析：{selected}")
            # 左右分栏：左边分析，右边图片
            ana_col, img_col = st.columns([3, 2])
            with ana_col:
                # 统计信息
                total = len(detail_df)
                spec_counts = detail_df["规格"].value_counts()
                machine_counts = detail_df["成型"].value_counts()
                builder_counts = detail_df["成型主手"].value_counts()
                st.metric("缺陷总数", total)
                if not spec_counts.empty:
                    st.write(f"**主要规格**：{spec_counts.index[0]}（{spec_counts.iloc[0]/total:.0%}）")
                if not machine_counts.empty:
                    st.write(f"**主要成型机**：{machine_counts.index[0]}（{machine_counts.iloc[0]/total:.0%}）")
                if not builder_counts.empty:
                    st.write(f"**主要成型主手**：{builder_counts.index[0]}（{builder_counts.iloc[0]/total:.0%}）")
                # 可以加更多分析...
            with img_col:
                # 取第一条数据的条码显示图片（或可让用户点击表格选择）
                barcode = detail_df.iloc[0]["条码"]
                _show_image(barcode, photo_index)

            # 全部清除按钮
            if st.button("返回全部数据", key="waste_clear"):
                st.session_state.pop("waste_selected", None)
                st.rerun()

def render_appearance_chart(df, photo_index=None):
    app_df = df[df["类型"] == "次品外观"]
    if app_df.empty:
        st.info("无外观次品数据")
        return

    left, right = st.columns([4, 6])
    with left:
        counts = app_df["病象"].value_counts().reset_index()
        counts.columns = ["病象", "数量"]
        fig = px.bar(counts, y="病象", x="数量", text="数量", orientation='h', title="外观次品 Pareto")
        fig.update_traces(textposition="outside")
        fig.update_layout(clickmode="event+select", height=450, template="plotly_white", margin=dict(l=10, r=10, t=40, b=10))
        event = st.plotly_chart(fig, use_container_width=True, on_select="rerun", key="app_hbar")
        if event and event.selection and event.selection.points:
            st.session_state["app_selected"] = event.selection.points[0]["y"]

    with right:
        cause = st.session_state.get("app_selected")
        if cause:
            detail = app_df[app_df["病象"] == cause]
            st.subheader(f"📋 {cause}")
            render_detail_table(detail, "app_detail", height=400, enable_click=True, photo_index=photo_index, show_filters=False)
        else:
            st.subheader("📋 全部外观次品")
            render_detail_table(app_df, "app_detail", height=400, enable_click=True, photo_index=photo_index, show_filters=False)

    if "app_selected" in st.session_state:
        selected = st.session_state["app_selected"]
        detail_df = app_df[app_df["病象"] == selected]
        if not detail_df.empty:
            st.divider()
            st.subheader(f"🔍 深入分析：{selected}")
            ana_col, img_col = st.columns([3, 2])
            with ana_col:
                total = len(detail_df)
                spec_counts = detail_df["规格"].value_counts()
                machine_counts = detail_df["成型"].value_counts()
                builder_counts = detail_df["成型主手"].value_counts()
                st.metric("缺陷总数", total)
                if not spec_counts.empty:
                    st.write(f"**主要规格**：{spec_counts.index[0]}（{spec_counts.iloc[0]/total:.0%}）")
                if not machine_counts.empty:
                    st.write(f"**主要成型机**：{machine_counts.index[0]}（{machine_counts.iloc[0]/total:.0%}）")
                if not builder_counts.empty:
                    st.write(f"**主要成型主手**：{builder_counts.index[0]}（{builder_counts.iloc[0]/total:.0%}）")
            with img_col:
                barcode = detail_df.iloc[0]["条码"]
                _show_image(barcode, photo_index)

            if st.button("返回全部数据", key="app_clear"):
                st.session_state.pop("app_selected", None)
                st.rerun()