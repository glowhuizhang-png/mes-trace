import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ---------- 辅助函数 ----------
def format_rate(value):
    if value < 0.01:
        return f"{value:.3%}"
    return f"{value:.2%}"

def format_change_percent(value, is_good_metric):
    if value is None or pd.isna(value):
        return '<span style="color:#A0AEC0;">—</span>'
    arrow = "↑" if value > 0 else "↓"
    abs_val = abs(value)
    if is_good_metric:
        css_class = "change-up-good" if value > 0 else "change-down-good"
    else:
        css_class = "change-up-bad" if value > 0 else "change-down-bad"
    return f'<span class="{css_class}">{arrow} {abs_val:.2%}</span>'

def format_abs_change(value):
    if value is None or pd.isna(value):
        return ''
    arrow = "↑" if value > 0 else "↓"
    color = "#16a34a" if value > 0 else "#dc2626"
    return f'<span style="font-weight:700; color:{color};">{arrow} {abs(value)}条</span>'

# ---------- 主渲染函数 ----------
def render_dashboard(
    waste_df, app_df, uf_df,
    waste_shop, app_shop, uf_mac,
    daily_stats,
    total_production, qual_rate,
    waste_rate, app_rate, uf_rate,
    prod_change,
    waste_rate_change,
    app_rate_change,
    uf_rate_change,
    qual_rate_change,
    waste_cnt, app_cnt, uf_cnt,
    waste_cnt_change=None,
    app_cnt_change=None,
    uf_cnt_change=None,
    waste_cnt_abs_change=None,
    app_cnt_abs_change=None,
    uf_cnt_abs_change=None,
    prod_abs_change=None,
    is_multi_day=False,          # 新增：是否选择多天
):
    # 开启白色大面板
    st.markdown('<div class="dashboard-white-box">', unsafe_allow_html=True)

    # 根据单天/多天切换标签
    if is_multi_day:
        change_label = "合计"
    else:
        change_label = "较昨日"

    cols = st.columns(5, gap="small")

    # 1. 硫化产量卡片
    with cols[0]:
        st.markdown(f"""
        <div class="kpi-card production-card">
            <div class="kpi-top-row">
                <span class="kpi-label">📦 硫化产量</span>
                <span class="kpi-main-value">{total_production:,}</span>
            </div>
            <div class="kpi-bottom-row">
                <span class="kpi-sub-label">{change_label}</span>
                <span>{format_abs_change(prod_abs_change) if not is_multi_day and prod_abs_change is not None else '—'}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # 2. 废品卡片
    with cols[1]:
        st.markdown(f"""
        <div class="kpi-card waste-card">
            <div class="kpi-top-row">
                <span class="kpi-label">🗑️ 废品</span>
                <span class="kpi-main-value">{waste_cnt}</span>
            </div>
            <div class="kpi-bottom-row">
                <span class="kpi-sub-label">废品 {format_rate(waste_rate)}</span>
                <span>{format_abs_change(waste_cnt_abs_change) if not is_multi_day else ''}</span>
            </div>
            <div class="kpi-bottom-row">
                <span class="kpi-sub-label">{change_label}</span>
                <span>{format_change_percent(waste_rate_change, False) if not is_multi_day else '—'}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # 3. 外观次品卡片
    with cols[2]:
        st.markdown(f"""
        <div class="kpi-card app-card">
            <div class="kpi-top-row">
                <span class="kpi-label">🎨 外观次品</span>
                <span class="kpi-main-value">{app_cnt}</span>
            </div>
            <div class="kpi-bottom-row">
                <span class="kpi-sub-label">次品 {format_rate(app_rate)}</span>
                <span>{format_abs_change(app_cnt_abs_change) if not is_multi_day else ''}</span>
            </div>
            <div class="kpi-bottom-row">
                <span class="kpi-sub-label">{change_label}</span>
                <span>{format_change_percent(app_rate_change, False) if not is_multi_day else '—'}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # 4. UF次品卡片
    with cols[3]:
        st.markdown(f"""
        <div class="kpi-card uf-card">
            <div class="kpi-top-row">
                <span class="kpi-label">🔍 UF次品</span>
                <span class="kpi-main-value">{uf_cnt}</span>
            </div>
            <div class="kpi-bottom-row">
                <span class="kpi-sub-label">次品 {format_rate(uf_rate)}</span>
                <span>{format_abs_change(uf_cnt_abs_change) if not is_multi_day else ''}</span>
            </div>
            <div class="kpi-bottom-row">
                <span class="kpi-sub-label">{change_label}</span>
                <span>{format_change_percent(uf_rate_change, False) if not is_multi_day else '—'}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # 5. 综合合格卡片
    with cols[4]:
        st.markdown(f"""
        <div class="kpi-card qual-card">
            <div class="kpi-top-row">
                <span class="kpi-label">✅ 综合合格</span>
                <span class="kpi-main-value">{format_rate(qual_rate)}</span>
            </div>
            <div class="kpi-bottom-row">
                <span class="kpi-sub-label">{change_label}</span>
                <span>{format_change_percent(qual_rate_change, True) if not is_multi_day else '—'}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<hr style="border: 0.5px solid #e2e8f0; margin: 0.8rem 0;">', unsafe_allow_html=True)

    # ========== 图表部分 ==========
    col_left, col_right = st.columns(2, gap="medium")

    # 废品车间分布（改为按数量降序，取消固定顺序）
    with col_left:
        if not waste_shop.empty:
            waste_shop_sorted = waste_shop.sort_values("数量", ascending=False)  # 降序
            max_val = waste_shop_sorted["数量"].max()
            fig = px.bar(waste_shop_sorted, x="车间", y="数量", text="数量", color_discrete_sequence=["#3B82F6"])
            fig.update_traces(textposition='outside', textfont=dict(size=16, color='#0f172a', weight='bold'), marker_line_width=0, width=0.6)
            fig.update_layout(
                title={'text': '🏭 废品车间分布', 'x': 0.5, 'xanchor': 'center',
                       'font': dict(size=20, color='#0f172a', family='Arial, sans-serif')},
                template='plotly_white', showlegend=False, xaxis_title=None, yaxis_title="数量",
                height=280, margin=dict(l=10, r=10, t=75, b=45),
                paper_bgcolor='white', plot_bgcolor='white', font=dict(color='#334155'),
                autosize=True, bargap=0.22)
            fig.update_xaxes(tickfont=dict(size=13, color='#334155'), automargin=True)
            fig.update_yaxes(range=[0, max_val * 1.18 if max_val > 0 else 1], tickfont=dict(size=12, color='#334155'))
            st.plotly_chart(fig, use_container_width=True, config={'responsive': True})
        else:
            st.info("暂无废品数据")

    # 外观次品车间分布（改为按数量降序）
    with col_right:
        if not app_shop.empty:
            app_shop_sorted = app_shop.sort_values("数量", ascending=False)  # 降序
            max_val = app_shop_sorted["数量"].max()
            fig = px.bar(app_shop_sorted, x="车间", y="数量", text="数量", color_discrete_sequence=["#F59E0B"])
            fig.update_traces(textposition='outside', textfont=dict(size=16, color='#334155', weight='bold'), marker_line_width=0, width=0.6)
            fig.update_layout(
                title={'text': '🎨 外观次品车间分布', 'x': 0.5, 'xanchor': 'center',
                       'font': dict(size=20, color='#0f172a', family='Arial, sans-serif')},
                template='plotly_white', showlegend=False, xaxis_title=None, yaxis_title="数量",
                height=280, margin=dict(l=10, r=10, t=75, b=45),
                paper_bgcolor='white', plot_bgcolor='white', font=dict(color='#334155'),
                autosize=True, bargap=0.22)
            fig.update_xaxes(tickfont=dict(size=13, color='#334155'), automargin=True)
            fig.update_yaxes(range=[0, max_val * 1.18 if max_val > 0 else 1], tickfont=dict(size=12, color='#334155'))
            st.plotly_chart(fig, use_container_width=True, config={'responsive': True})
        else:
            st.info("暂无外观次品数据")

    # UF次品成型机分布（修正标题为UF分布，非趋势图）
    if not uf_mac.empty:
        uf_mac_sorted = uf_mac.sort_values("数量", ascending=False)
        max_val = uf_mac_sorted["数量"].max()
        fig = px.bar(uf_mac_sorted, x="成型", y="数量", text="数量", color_discrete_sequence=["#14B8A6"])
        fig.update_traces(textposition='outside', textfont=dict(size=16, color='#334155', weight='bold'), marker_line_width=0, width=0.6)
        fig.update_layout(
            title={'text': '🔧 UF次品成型机分布', 'x': 0.5, 'xanchor': 'center',
                   'font': dict(size=20, color='#0f172a', family='Arial, sans-serif')},
            template='plotly_white', height=300, showlegend=False, xaxis_title=None, yaxis_title="数量",
            margin=dict(l=10, r=10, t=70, b=60),
            paper_bgcolor='white', plot_bgcolor='white', font=dict(color='#334155'),
            autosize=True, bargap=0.25)
        fig.update_xaxes(tickangle=-25, tickfont=dict(size=13, color='#334155'), automargin=True)
        fig.update_yaxes(range=[0, max_val * 1.18 if max_val > 0 else 1], tickfont=dict(size=12, color='#334155'))
        st.plotly_chart(fig, use_container_width=True, config={'responsive': True})
    else:
        st.info("暂无UF次品数据")

    # ========== 日趋势图（拆分为两个图） ==========
    if daily_stats is not None and not daily_stats.empty:
        st.markdown('<hr style="border: 0.5px solid #e2e8f0; margin: 0.5rem 0;">', unsafe_allow_html=True)

        # 图1：废品率、外观次品率、UF次品率
        fig1 = go.Figure()
        fig1.add_trace(go.Scatter(
            x=daily_stats["日期"], y=daily_stats["废品率"], mode='lines+markers+text', name='废品率',
            line=dict(color='#EF4444', width=2), marker=dict(size=8),
            text=[f"{v:.2%}" for v in daily_stats["废品率"]], textposition='top center', textfont=dict(size=12, color='#0f172a')
        ))
        fig1.add_trace(go.Scatter(
            x=daily_stats["日期"], y=daily_stats["外观次品率"], mode='lines+markers+text', name='外观次品率',
            line=dict(color='#F59E0B', width=2), marker=dict(size=8),
            text=[f"{v:.2%}" for v in daily_stats["外观次品率"]], textposition='top center', textfont=dict(size=12, color='#0f172a')
        ))
        fig1.add_trace(go.Scatter(
            x=daily_stats["日期"], y=daily_stats["UF次品率"], mode='lines+markers+text', name='UF次品率',
            line=dict(color='#14B8A6', width=2), marker=dict(size=8),
            text=[f"{v:.2%}" for v in daily_stats["UF次品率"]], textposition='top center', textfont=dict(size=12, color='#0f172a')
        ))
        max_rate = max(daily_stats["废品率"].max(), daily_stats["外观次品率"].max(), daily_stats["UF次品率"].max())
        upper_rate = max(0.002, max_rate * 1.3)
        fig1.update_layout(
            title={'text': '📈 日趋势 — 次品率', 'x': 0.02, 'xanchor': 'left', 'y': 0.95, 'yanchor': 'top',
                   'font': dict(size=18, color='#0f172a', family='Arial, sans-serif')},
            template='plotly_white', height=340,
            margin=dict(l=30, r=30, t=60, b=30),
            yaxis=dict(title='次品率', tickformat='.2%', range=[0, upper_rate], gridcolor='#e2e8f0'),
            legend=dict(orientation='h', yanchor='bottom', y=1.18, xanchor='right', x=1, font=dict(color='#334155')),
            hovermode='x unified', paper_bgcolor='white', plot_bgcolor='white', font=dict(color='#334155')
        )
        fig1.update_xaxes(tickfont=dict(size=13, color='#334155'), automargin=True)
        fig1.update_yaxes(tickfont=dict(size=13, color='#334155'))
        st.plotly_chart(fig1, use_container_width=True, config={'responsive': True})

        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=daily_stats["日期"], y=daily_stats["综合合格率"], mode='lines+markers+text', name='综合合格率',
            line=dict(color='#10B981', width=2, dash='dot'), marker=dict(size=8),
            text=[f"{v:.2%}" for v in daily_stats["综合合格率"]], textposition='top center', textfont=dict(size=12, color='#0f172a')
        ))
        min_qual = daily_stats["综合合格率"].min()
        lower_qual = min(0.99, min_qual * 0.998) if min_qual > 0 else 0.99
        fig2.update_layout(
            title={'text': '📈 日趋势 — 综合合格率', 'x': 0.02, 'xanchor': 'left', 'y': 0.95, 'yanchor': 'top',
                   'font': dict(size=18, color='#0f172a', family='Arial, sans-serif')},
            template='plotly_white', height=340,
            margin=dict(l=30, r=30, t=60, b=30),
            yaxis=dict(title='合格率', tickformat='.2%', range=[lower_qual, 1], gridcolor='#e2e8f0'),
            legend=dict(orientation='h', yanchor='bottom', y=1.18, xanchor='right', x=1, font=dict(color='#334155')),
            hovermode='x unified', paper_bgcolor='white', plot_bgcolor='white', font=dict(color='#334155')
        )
        fig2.update_xaxes(tickfont=dict(size=13, color='#334155'), automargin=True)
        fig2.update_yaxes(tickfont=dict(size=13, color='#334155'))
        st.plotly_chart(fig2, use_container_width=True, config={'responsive': True})

    st.markdown('</div>', unsafe_allow_html=True)   # 关闭白色大面板