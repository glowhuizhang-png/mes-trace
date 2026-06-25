import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from modules.photo import trigger_image_popup

def render_summary_table(summary_df, key_prefix, height=480):
    """渲染汇总表"""
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


def render_detail_table(df, key_prefix, height='content', enable_click=True, photo_index=None):
    """渲染明细表，显示全部行"""
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
    st.subheader("外观废次品分析")

    # ---------- 1. 汇总表与明细交互 ----------
    combined = combined_df.copy()
    combined["规格-花纹"] = combined["规格"].astype(str) + " - " + combined["花纹"].astype(str)

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
                event_detail = st.dataframe(
                    detail[detail_cols],
                    width='stretch',
                    height=480,
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

    # ---------- 2. 集中性分析 ----------
    st.divider()
    st.subheader("📊 集中性分析（点击柱子深入归因）")

    if combined.empty:
        st.info("无数据可分析")
        return

    # 维度按钮（车间放在最前面）
    dim_options = ["车间", "病象", "成型机", "硫化机", "规格-花纹", "成型主手", "硫化主手"]
    selected_dim = st.radio(
        "选择分析维度",
        dim_options,
        horizontal=True,
        index=0,
        key="dim_selector"
    )
    dim_col = {
        "车间": "车间",
        "病象": "病象",
        "成型机": "成型",
        "硫化机": "硫化",
        "规格-花纹": "规格-花纹",
        "成型主手": "成型主手",
        "硫化主手": "硫化主手"
    }[selected_dim]

    # 数据处理（取前12项，其余合并为“其他”）
    grouped = combined.groupby([dim_col, "类型"]).size().reset_index(name="数量")
    pivot = grouped.pivot(index=dim_col, columns="类型", values="数量").fillna(0).reset_index()
    for col in ["废品", "次品外观"]:
        if col not in pivot.columns:
            pivot[col] = 0
    pivot["总数"] = pivot["废品"] + pivot["次品外观"]
    pivot = pivot.sort_values("总数", ascending=False)

    if len(pivot) > 12:
        top12 = pivot.head(12)
        other = pivot.iloc[12:].copy()
        other_sum = other[["废品", "次品外观", "总数"]].sum()
        other_row = pd.DataFrame({
            dim_col: ["其他"],
            "废品": [other_sum["废品"]],
            "次品外观": [other_sum["次品外观"]],
            "总数": [other_sum["总数"]]
        })
        pivot = pd.concat([top12, other_row], ignore_index=True)

    top12_values = pivot[pivot[dim_col] != "其他"][dim_col].tolist()

    # 绘图（字体放大）
    fig = px.bar(
        pivot,
        x=dim_col,
        y=["废品", "次品外观"],
        title=f"{selected_dim} 分布（废品/次品堆积）",
        labels={"value": "数量", "variable": "类型"},
        barmode="stack",
        text_auto=True,
        color_discrete_map={"废品": "#ff7f0e", "次品外观": "#1f77b4"}
    )
    fig.update_traces(
        textposition="inside",
        textfont=dict(size=18, family="Microsoft YaHei", color="black"),
        hovertemplate="<b>%{x}</b><br>废品: %{customdata[0]}<br>次品: %{customdata[1]}<br>总数: %{customdata[2]}<extra></extra>",
        customdata=pivot[["废品", "次品外观", "总数"]].values
    )
    fig.update_layout(
        title=dict(font=dict(size=28, family="Microsoft YaHei", color="black")),
        xaxis=dict(title=None, tickfont=dict(size=20, family="Microsoft YaHei", color="black"), tickangle=45),
        yaxis=dict(title="数量", tickfont=dict(size=20, family="Microsoft YaHei", color="black")),
        height=550,
        template="plotly_white",
        legend=dict(font=dict(size=18, family="Microsoft YaHei", color="black")),
        hoverlabel=dict(font_size=20, font_family="Microsoft YaHei", font_color="black"),
        clickmode="event+select",
        font=dict(color="black")
    )

    # 显示图表并捕获点击
    event = st.plotly_chart(
        fig,
        use_container_width=True,
        key=f"chart_{selected_dim}",
        on_select="rerun"
    )

    # ---------- 点击后归因分析 ----------
    st.markdown("**点击柱形图查看深入归因分析**")
    drill_df = pd.DataFrame()

    if event and event.selection and event.selection.points:
        clicked_point = event.selection.points[0]
        clicked_value = clicked_point["x"]

        if clicked_value == "其他":
            drill_df = combined[~combined[dim_col].isin(top12_values)]
        else:
            drill_df = combined[combined[dim_col] == clicked_value]

        if not drill_df.empty:
            total_count = len(drill_df)

            cause_counts = drill_df["病象"].value_counts()
            spec_counts = drill_df["规格"].astype(str).replace("nan", "").replace("None", "")
            spec_counts = spec_counts[spec_counts != ""].value_counts()
            builder_counts = drill_df["成型主手"].astype(str).replace("nan", "").replace("None", "")
            builder_counts = builder_counts[builder_counts != ""].value_counts()
            cure_counts = drill_df["硫化主手"].astype(str).replace("nan", "").replace("None", "")
            cure_counts = cure_counts[cure_counts != ""].value_counts()

            cause_name = cause_counts.index[0] if len(cause_counts) else "-"
            cause_ratio = cause_counts.iloc[0] / total_count if len(cause_counts) else 0
            spec_name = spec_counts.index[0] if len(spec_counts) else "-"
            spec_ratio = spec_counts.iloc[0] / total_count if len(spec_counts) else 0
            builder_name = builder_counts.index[0] if len(builder_counts) else "-"
            builder_ratio = builder_counts.iloc[0] / total_count if len(builder_counts) else 0
            cure_name = cure_counts.index[0] if len(cure_counts) else "-"
            cure_ratio = cure_counts.iloc[0] / total_count if len(cure_counts) else 0

            c1, c2, c3, c4, c5 = st.columns(5)
            with c1:
                st.metric("废次品总数", total_count)
            with c2:
                st.metric("主要病象", cause_name, f"{cause_ratio:.0%}")
            with c3:
                st.metric("主要规格", spec_name, f"{spec_ratio:.0%}")
            with c4:
                st.metric("成型主手", builder_name, f"{builder_ratio:.0%}")
            with c5:
                st.metric("硫化主手", cure_name, f"{cure_ratio:.0%}")

            analysis = []
            if cause_ratio > 0.5:
                analysis.append(f"病象高度集中在【{cause_name}】（{cause_ratio:.0%}）")
            if spec_ratio > 0.5:
                analysis.append(f"规格高度集中在【{spec_name}】（{spec_ratio:.0%}）")
            if builder_ratio > 0.4:
                analysis.append(f"成型主手【{builder_name}】占比偏高（{builder_ratio:.0%}）")
            if cure_ratio > 0.4:
                analysis.append(f"硫化主手【{cure_name}】占比偏高（{cure_ratio:.0%}）")
            if analysis:
                for item in analysis:
                    st.warning(item)
            else:
                st.success("未发现明显集中趋势")

            # ----- TOP5 四宫格（纯黑、窄柱、无纵轴标题） -----
            # 注意：此处已删除 "### 📊 TOP5 贡献分析" 标题

            def safe_top5(series, name):
                ser = series.astype(str).replace("nan", "").replace("None", "")
                ser = ser[ser != ""]
                if ser.empty:
                    return pd.DataFrame({name: ["-"], "数量": [0]})
                top = ser.value_counts().head(5).reset_index()
                top.columns = [name, "数量"]
                return top

            top_cause = safe_top5(drill_df["病象"], "病象")
            top_spec = safe_top5(drill_df["规格"], "规格")
            top_builder = safe_top5(drill_df["成型主手"], "成型主手")
            top_cure = safe_top5(drill_df["硫化主手"], "硫化主手")

            text_color = "black"
            font_size = 16
            title_font = 20
            label_font = 16

            row1 = st.columns(2)
            row2 = st.columns(2)

            with row1[0]:
                if len(top_cause) > 1 or top_cause.iloc[0]["数量"] > 0:
                    fig_cause = px.bar(
                        top_cause,
                        x="数量",
                        y="病象",
                        orientation="h",
                        title="病象 TOP5",
                        text="数量",
                        color="数量",
                        color_continuous_scale="Blues"
                    )
                    fig_cause.update_traces(
                        textposition="outside",
                        textfont=dict(size=font_size, color=text_color, family="Microsoft YaHei"),
                        marker=dict(line=dict(color='black', width=0.5))
                    )
                    fig_cause.update_layout(
                        height=300,
                        bargap=0.4,
                        margin=dict(l=0, r=0, t=40, b=0),
                        title=dict(font=dict(size=title_font, color=text_color, family="Microsoft YaHei")),
                        xaxis=dict(
                            tickfont=dict(size=label_font, color=text_color, family="Microsoft YaHei"),
                            title=None,
                            showgrid=False
                        ),
                        yaxis=dict(
                            tickfont=dict(size=label_font, color=text_color, family="Microsoft YaHei"),
                            title=None,
                            showgrid=False
                        ),
                        legend=dict(font=dict(size=font_size, color=text_color, family="Microsoft YaHei")),
                        coloraxis_showscale=False,
                        font=dict(color=text_color)
                    )
                    st.plotly_chart(fig_cause, use_container_width=True)
                else:
                    st.caption("无病象数据")

            with row1[1]:
                if len(top_spec) > 1 or top_spec.iloc[0]["数量"] > 0:
                    fig_spec = px.bar(
                        top_spec,
                        x="数量",
                        y="规格",
                        orientation="h",
                        title="规格 TOP5",
                        text="数量",
                        color="数量",
                        color_continuous_scale="Greens"
                    )
                    fig_spec.update_traces(
                        textposition="outside",
                        textfont=dict(size=font_size, color=text_color, family="Microsoft YaHei"),
                        marker=dict(line=dict(color='black', width=0.5))
                    )
                    fig_spec.update_layout(
                        height=300,
                        bargap=0.4,
                        margin=dict(l=0, r=0, t=40, b=0),
                        title=dict(font=dict(size=title_font, color=text_color, family="Microsoft YaHei")),
                        xaxis=dict(
                            tickfont=dict(size=label_font, color=text_color, family="Microsoft YaHei"),
                            title=None,
                            showgrid=False
                        ),
                        yaxis=dict(
                            tickfont=dict(size=label_font, color=text_color, family="Microsoft YaHei"),
                            title=None,
                            showgrid=False
                        ),
                        legend=dict(font=dict(size=font_size, color=text_color, family="Microsoft YaHei")),
                        coloraxis_showscale=False,
                        font=dict(color=text_color)
                    )
                    st.plotly_chart(fig_spec, use_container_width=True)
                else:
                    st.caption("无规格数据")

            with row2[0]:
                if len(top_builder) > 1 or top_builder.iloc[0]["数量"] > 0:
                    fig_builder = px.bar(
                        top_builder,
                        x="数量",
                        y="成型主手",
                        orientation="h",
                        title="成型主手 TOP5",
                        text="数量",
                        color="数量",
                        color_continuous_scale="Oranges"
                    )
                    fig_builder.update_traces(
                        textposition="outside",
                        textfont=dict(size=font_size, color=text_color, family="Microsoft YaHei"),
                        marker=dict(line=dict(color='black', width=0.5))
                    )
                    fig_builder.update_layout(
                        height=300,
                        bargap=0.4,
                        margin=dict(l=0, r=0, t=40, b=0),
                        title=dict(font=dict(size=title_font, color=text_color, family="Microsoft YaHei")),
                        xaxis=dict(
                            tickfont=dict(size=label_font, color=text_color, family="Microsoft YaHei"),
                            title=None,
                            showgrid=False
                        ),
                        yaxis=dict(
                            tickfont=dict(size=label_font, color=text_color, family="Microsoft YaHei"),
                            title=None,
                            showgrid=False
                        ),
                        legend=dict(font=dict(size=font_size, color=text_color, family="Microsoft YaHei")),
                        coloraxis_showscale=False,
                        font=dict(color=text_color)
                    )
                    st.plotly_chart(fig_builder, use_container_width=True)
                else:
                    st.caption("无成型主手数据")

            with row2[1]:
                if len(top_cure) > 1 or top_cure.iloc[0]["数量"] > 0:
                    fig_cure = px.bar(
                        top_cure,
                        x="数量",
                        y="硫化主手",
                        orientation="h",
                        title="硫化主手 TOP5",
                        text="数量",
                        color="数量",
                        color_continuous_scale="Purples"
                    )
                    fig_cure.update_traces(
                        textposition="outside",
                        textfont=dict(size=font_size, color=text_color, family="Microsoft YaHei"),
                        marker=dict(line=dict(color='black', width=0.5))
                    )
                    fig_cure.update_layout(
                        height=300,
                        bargap=0.4,
                        margin=dict(l=0, r=0, t=40, b=0),
                        title=dict(font=dict(size=title_font, color=text_color, family="Microsoft YaHei")),
                        xaxis=dict(
                            tickfont=dict(size=label_font, color=text_color, family="Microsoft YaHei"),
                            title=None,
                            showgrid=False
                        ),
                        yaxis=dict(
                            tickfont=dict(size=label_font, color=text_color, family="Microsoft YaHei"),
                            title=None,
                            showgrid=False
                        ),
                        legend=dict(font=dict(size=font_size, color=text_color, family="Microsoft YaHei")),
                        coloraxis_showscale=False,
                        font=dict(color=text_color)
                    )
                    st.plotly_chart(fig_cure, use_container_width=True)
                else:
                    st.caption("无硫化主手数据")

            # ----- 风险组合 -----
            st.markdown("### ⚠️ 风险组合分析")
            if "规格" in drill_df.columns and "病象" in drill_df.columns:
                combo = drill_df.groupby(["规格", "病象"]).size().reset_index(name="数量")
                combo = combo.sort_values("数量", ascending=False).head(10)
                if not combo.empty:
                    st.dataframe(
                        combo,
                        width='stretch',
                        height=400,
                        hide_index=True,
                        key="combo_table"
                    )
                    top_combo = combo.iloc[0]
                    top_combo_ratio = top_combo["数量"] / total_count
                    st.warning(
                        f"🔴 最高风险组合：**【{top_combo['规格']}】 + 【{top_combo['病象']}】** "
                        f"共 {top_combo['数量']} 条，占当前维度的 {top_combo_ratio:.0%}"
                    )
                else:
                    st.info("无有效组合数据")
            else:
                st.info("缺少规格或病象字段，无法进行组合分析")

            # ----- 明细表 -----
            st.markdown("### 📋 明细数据")
            cols_list = [
                dim_col,
                "病象",
                "硫化",
                "硫化主手",
                "硫化日期",
                "成型",
                "成型时间",
                "成型主手",
                "规格",
                "花纹",
                "车间"
            ]
            display_cols = list(dict.fromkeys([c for c in cols_list if c in drill_df.columns]))
            st.dataframe(
                drill_df[display_cols],
                width='stretch',
                height='content',
                hide_index=True,
                key="drill_down_table"
            )
        else:
            st.info("该维度无明细数据")
    else:
        st.info("请点击柱状图中的柱子查看深入归因分析")

    # ---------- 3. 机台统计 ----------
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

    # ---------- 4. 原明细数据 ----------
    st.divider()
    waste_type = st.radio("选择明细类型", ["全选", "废品", "外观次品"], horizontal=True)
    if waste_type == "全选":
        render_detail_table(combined, "all_detail", height='content', enable_click=False, photo_index=None)
    elif waste_type == "废品":
        render_detail_table(waste_df, "waste_detail", height='content', enable_click=True, photo_index=photo_index)
    else:
        render_detail_table(app_df, "app_detail", height='content', enable_click=True, photo_index=photo_index)