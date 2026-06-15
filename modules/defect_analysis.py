# modules/defect_analysis.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px


def render_defect_analysis(df, waste_df, app_df, selected_dates, photo_index, detail_table_callback):
    combined = df[df["类型"].isin(["废品", "次品外观"])].copy()
    if combined.empty:
        st.info("无废品或外观次品数据")
        return

    if "defect_selected_shop" not in st.session_state:
        st.session_state.defect_selected_shop = "全部"
    if "defect_clicked_cause" not in st.session_state:
        st.session_state.defect_clicked_cause = None

    st.markdown(
        """
        <style>
        div.stButton > button {
            padding-top: 2px !important;
            padding-bottom: 2px !important;
            height: auto !important;
            line-height: 1.2 !important;
        }
        hr {
            margin: 8px 0 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # 车间筛选按钮
    shops = ["全部", "密炼", "部件", "成型", "硫化", "工程", "工艺", "其他"]
    cols = st.columns(len(shops))
    for i, shop in enumerate(shops):
        is_active = st.session_state.defect_selected_shop == shop
        if cols[i].button(
            shop,
            key=f"shop_{shop}",
            use_container_width=True,
            type="primary" if is_active else "secondary",
        ):
            if st.session_state.defect_selected_shop != shop:
                st.session_state.defect_selected_shop = shop
                st.session_state.defect_clicked_cause = None
                st.rerun()

    selected_shop = st.session_state.defect_selected_shop
    filtered = combined if selected_shop == "全部" else combined[combined["车间"] == selected_shop]

    # 第一组图表：病象堆叠柱状图
    if not filtered.empty:
        grouped = filtered.groupby(["病象", "类型"]).size().reset_index(name="数量")
        pivot = grouped.pivot(index="病象", columns="类型", values="数量").fillna(0)
        for col in ["废品", "次品外观"]:
            if col not in pivot.columns:
                pivot[col] = 0
        pivot = pivot.sort_values(by=["废品", "次品外观"], ascending=False)

        fig1 = go.Figure()
        fig1.add_trace(go.Bar(
            x=pivot.index, y=pivot["废品"], name="废品",
            marker_color="#F59E0B", text=pivot["废品"], textposition="inside",
            textfont=dict(size=16, color="black"),
            hovertemplate="病象: %{x}<br>废品: %{y}<extra></extra>"
        ))
        fig1.add_trace(go.Bar(
            x=pivot.index, y=pivot["次品外观"], name="外观次品",
            marker_color="#60A5FA", text=pivot["次品外观"], textposition="inside",
            textfont=dict(size=16, color="black"),
            hovertemplate="病象: %{x}<br>外观次品: %{y}<extra></extra>"
        ))
        fig1.update_layout(
            barmode="stack", title=None, xaxis_title=None, yaxis_title=None,
            height=220, margin=dict(l=20, r=20, t=20, b=20), plot_bgcolor="white",
            hovermode="closest",
            legend=dict(orientation="h", yanchor="top", y=1.0, xanchor="left", x=0.01, font=dict(size=11)),
            xaxis=dict(showgrid=False), yaxis=dict(showgrid=False)
        )
        fig1.update_xaxes(tickangle=-30)
        plot_event = st.plotly_chart(fig1, use_container_width=True, key="defect_bar_chart",
                                     on_select="rerun", selection_mode="points")
        if plot_event and plot_event.selection:
            points = plot_event.selection.points
            if points and len(points) > 0:
                clicked = points[0].get("x") if isinstance(points[0], dict) else getattr(points[0], "x", None)
                if clicked and clicked != st.session_state.defect_clicked_cause:
                    st.session_state.defect_clicked_cause = clicked
                    st.rerun()
    else:
        st.warning(f"车间「{selected_shop}」无数据")

    # 明细表
    clicked_cause = st.session_state.defect_clicked_cause
    if clicked_cause and not filtered.empty:
        detail_df = filtered[filtered["病象"] == clicked_cause].copy()
    else:
        detail_df = filtered.copy()

    if not detail_df.empty:
        detail_df.insert(0, "序号", range(1, len(detail_df) + 1))
        if "病象" in detail_df.columns:
            cols_order = ["序号", "病象"]
        else:
            cols_order = ["序号"]
        detail_df["区分"] = detail_df["类型"].apply(lambda x: "废品" if x == "废品" else "外观次品")
        other_cols = ["条码", "规格", "花纹", "位置", "成型", "成型时间", "成型主手", "硫化", "硫化主手", "硫化日期"]
        other_cols = [c for c in other_cols if c in detail_df.columns]
        display_cols = cols_order + ["区分"] + other_cols
        display_cols = list(dict.fromkeys(display_cols))

        st.dataframe(
            detail_df[display_cols], use_container_width=True, height=400, hide_index=True,
            selection_mode="single-row", on_select="rerun", key="defect_detail_table"
        )
        if st.session_state.get("defect_detail_table", {}).get("selection", {}).get("rows"):
            selected_row_idx = st.session_state.defect_detail_table["selection"]["rows"][0]
            barcode = detail_df.iloc[selected_row_idx]["条码"]
            if barcode:
                from modules.photo import trigger_image_popup
                trigger_image_popup(str(barcode), photo_index)

        col1, col2 = st.columns([1, 4])
        with col1:
            csv_data = detail_df.to_csv(index=False).encode("utf-8-sig")
            filename = f"defect_{clicked_cause}_{selected_shop}.csv" if clicked_cause else f"defect_all_{selected_shop}.csv"
            st.download_button(label="📥 下载当前明细", data=csv_data, file_name=filename, mime="text/csv", use_container_width=True)
    else:
        st.info("当前无明细数据")

    # ========== 设备缺陷分布 ==========
    st.markdown("<hr style='margin: 8px 0;'>", unsafe_allow_html=True)
    device_options = ["全部", "成型", "硫化", "工程", "工艺", "其他"]
    device_cols = st.columns(len(device_options))
    if "defect_selected_device" not in st.session_state:
        st.session_state.defect_selected_device = "全部"
    for i, dev in enumerate(device_options):
        is_active = st.session_state.defect_selected_device == dev
        if device_cols[i].button(
            dev, key=f"device_{dev}", use_container_width=True,
            type="primary" if is_active else "secondary"
        ):
            if st.session_state.defect_selected_device != dev:
                st.session_state.defect_selected_device = dev
                st.rerun()
    selected_device = st.session_state.defect_selected_device

    device_data = combined.copy()
    if not device_data.empty:
        # 筛选车间
        if selected_device != "全部":
            if selected_device == "成型":
                device_data = device_data[device_data["车间"] == "成型"]
            elif selected_device == "硫化":
                device_data = device_data[device_data["车间"] == "硫化"]
            elif selected_device == "工程":
                device_data = device_data[device_data["车间"] == "工程"]
            elif selected_device == "工艺":
                device_data = device_data[device_data["车间"] == "工艺"]
            elif selected_device == "其他":
                main_shops = ["密炼", "部件", "部件成型", "成型", "硫化", "工程", "工艺"]
                device_data = device_data[~device_data["车间"].isin(main_shops)]

        if device_data.empty:
            st.info(f"车间「{selected_device}」无设备数据")
        else:
            # 横坐标规则：工程用硫化机，工艺用成型机，硫化用硫化机，其余用成型机
            if selected_device in ["硫化", "工程"]:
                device_col = "硫化"
            else:
                device_col = "成型"
            # 兼容列名：可能叫"成型"或"成型机台"，硫化同理
            if device_col not in device_data.columns:
                # 尝试替代列名
                if device_col == "成型" and "成型机台" in device_data.columns:
                    device_col = "成型机台"
                elif device_col == "硫化" and "硫化机台" in device_data.columns:
                    device_col = "硫化机台"
                else:
                    st.info(f"数据中无{device_col}相关列，无法绘制设备图")
                    device_data = pd.DataFrame()

            if not device_data.empty:
                grouped = device_data.groupby([device_col, "病象"]).size().reset_index(name="数量")
                grouped = grouped[grouped[device_col].notna() & (grouped[device_col] != "")]
                if grouped.empty:
                    st.info("无有效设备数据")
                else:
                    causes = grouped["病象"].unique()
                    color_palette = ["#1F77B4", "#2CA02C", "#9467BD", "#8C564B", "#E377C2",
                                     "#7F7F7F", "#BCBD22", "#17BECF", "#FFBB78", "#98DF8A",
                                     "#C5B0D5", "#F7B6D2", "#DBDB8D", "#9EDAE5"]
                    fig2 = go.Figure()
                    for i, cause in enumerate(causes):
                        cause_data = grouped[grouped["病象"] == cause]
                        fig2.add_trace(go.Bar(
                            x=cause_data[device_col], y=cause_data["数量"], name=cause,
                            marker_color=color_palette[i % len(color_palette)],
                            text=cause_data["数量"], textposition="inside",
                            textfont=dict(size=14, color="black"),
                            hovertemplate=f"设备: %{{x}}<br>病象: {cause}<br>数量: %{{y}}<extra></extra>"
                        ))
                    fig2.update_layout(
                        barmode="stack", title=None, xaxis_title=None, yaxis_title=None,
                        height=320, margin=dict(l=20, r=20, t=10, b=10), plot_bgcolor="white",
                        hovermode="closest", showlegend=False,
                        xaxis=dict(showgrid=False), yaxis=dict(showgrid=False),
                        hoverlabel=dict(font_size=14, font_color="black")
                    )
                    fig2.update_xaxes(tickangle=-30)
                    st.plotly_chart(fig2, use_container_width=True, key="device_bar_chart")

    # ========== 人员缺陷分布 ==========
    st.markdown("<hr style='margin: 8px 0;'>", unsafe_allow_html=True)
    person_options = ["全部", "成型", "硫化", "工程", "工艺"]
    person_cols = st.columns(len(person_options))
    if "defect_selected_person" not in st.session_state:
        st.session_state.defect_selected_person = "全部"
    for i, p in enumerate(person_options):
        is_active = st.session_state.defect_selected_person == p
        if person_cols[i].button(
            p, key=f"person_{p}", use_container_width=True,
            type="primary" if is_active else "secondary"
        ):
            if st.session_state.defect_selected_person != p:
                st.session_state.defect_selected_person = p
                st.rerun()
    selected_person = st.session_state.defect_selected_person

    person_data = combined.copy()
    if not person_data.empty:
        if selected_person != "全部":
            if selected_person == "成型":
                person_data = person_data[person_data["车间"] == "成型"]
            elif selected_person == "硫化":
                person_data = person_data[person_data["车间"] == "硫化"]
            elif selected_person == "工程":
                person_data = person_data[person_data["车间"] == "工程"]
            elif selected_person == "工艺":
                person_data = person_data[person_data["车间"] == "工艺"]

        if person_data.empty:
            st.info(f"车间「{selected_person}」无人员数据")
        else:
            # 横坐标规则：工程用硫化主手，工艺用成型主手，硫化用硫化主手，其余用成型主手
            if selected_person in ["硫化", "工程"]:
                person_col = "硫化主手"
            else:
                person_col = "成型主手"
            # 检查列是否存在
            if person_col not in person_data.columns:
                st.info(f"数据中无{person_col}列，无法绘制人员图")
            else:
                grouped = person_data.groupby([person_col, "病象"]).size().reset_index(name="数量")
                grouped = grouped[grouped[person_col].notna() & (grouped[person_col] != "")]
                if grouped.empty:
                    st.info("无有效人员数据")
                else:
                    causes = grouped["病象"].unique()
                    color_palette = ["#1F77B4", "#2CA02C", "#9467BD", "#8C564B", "#E377C2",
                                     "#7F7F7F", "#BCBD22", "#17BECF", "#FFBB78", "#98DF8A",
                                     "#C5B0D5", "#F7B6D2", "#DBDB8D", "#9EDAE5"]
                    fig3 = go.Figure()
                    for i, cause in enumerate(causes):
                        cause_data = grouped[grouped["病象"] == cause]
                        fig3.add_trace(go.Bar(
                            x=cause_data[person_col], y=cause_data["数量"], name=cause,
                            marker_color=color_palette[i % len(color_palette)],
                            text=cause_data["数量"], textposition="inside",
                            textfont=dict(size=14, color="black"),
                            hovertemplate=f"人员: %{{x}}<br>病象: {cause}<br>数量: %{{y}}<extra></extra>"
                        ))
                    fig3.update_layout(
                        barmode="stack", title=None, xaxis_title=None, yaxis_title=None,
                        height=320, margin=dict(l=20, r=20, t=10, b=10), plot_bgcolor="white",
                        hovermode="closest", showlegend=False,
                        xaxis=dict(showgrid=False), yaxis=dict(showgrid=False),
                        hoverlabel=dict(font_size=14, font_color="black")
                    )
                    fig3.update_xaxes(tickangle=-30)
                    st.plotly_chart(fig3, use_container_width=True, key="person_bar_chart")

    # 保留折叠的机台统计
    with st.expander("🔧 机台统计（按日期/病象）", expanded=False):
        st.info("机台统计功能已折叠，点击展开查看。")