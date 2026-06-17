import plotly.graph_objects as go

def style_bar_chart(fig, title):
    max_y = 0
    for trace in fig.data:
        if hasattr(trace, 'y') and len(trace.y) > 0:
            max_y = max(max_y, max(trace.y))
    fig.update_traces(
        textfont=dict(size=20, color="black", family="Microsoft YaHei"),
        textposition="outside",
        marker=dict(line=dict(width=1, color="#333333"))
    )
    y_max = max_y * 1.15 if max_y > 0 else 1
    fig.update_layout(
        template="plotly_white",
        title=dict(text=title, font=dict(size=26, family="Microsoft YaHei")),
        xaxis=dict(title=None, tickfont=dict(size=18, family="Microsoft YaHei")),
        yaxis=dict(title=None, tickfont=dict(size=18, family="Microsoft YaHei"), range=[0, y_max]),
        hoverlabel=dict(font_size=16),
        margin=dict(t=80, b=40, l=60, r=20)
    )
    return fig