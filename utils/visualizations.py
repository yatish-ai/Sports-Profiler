"""
Visualizations - All Plotly chart generation for the dashboard.
Uses the England/Shoty image color palette:
  - Background: #1A1F8C (deep royal blue)
  - Accent 1:  #E8293A (bold red)
  - Accent 2:  #FFFFFF (white)
  - Surface:   #0F1566 (darker navy)
  - Highlight: #FFD700 (gold)
"""
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np


# ── Brand palette ──────────────────────────────────────────────────────────
BG       = "#0F1566"
SURFACE  = "#1A1F8C"
RED      = "#E8293A"
WHITE    = "#FFFFFF"
GOLD     = "#FFD700"
BLUE_LT  = "#4A5FE8"
PAPER    = "#0A0F4A"

CHART_LAYOUT = dict(
    paper_bgcolor=PAPER,
    plot_bgcolor=BG,
    font=dict(family="'Barlow Condensed', 'Arial Narrow', sans-serif",
              color=WHITE, size=13),
    margin=dict(l=30, r=30, t=50, b=30),
)


def radar_chart(axes: list, values: list, player_name: str) -> go.Figure:
    """Draw a radar/spider chart for player attributes."""
    axes_closed = axes + [axes[0]]
    values_closed = values + [values[0]]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values_closed,
        theta=axes_closed,
        fill="toself",
        fillcolor=f"rgba(232, 41, 58, 0.25)",
        line=dict(color=RED, width=2.5),
        name=player_name,
        marker=dict(color=WHITE, size=6),
    ))
    fig.update_layout(
        **CHART_LAYOUT,
        polar=dict(
            bgcolor=SURFACE,
            radialaxis=dict(
                visible=True, range=[0, 100],
                gridcolor="rgba(255,255,255,0.15)",
                tickfont=dict(color="rgba(255,255,255,0.6)", size=10),
                tickvals=[20, 40, 60, 80, 100],
            ),
            angularaxis=dict(
                gridcolor="rgba(255,255,255,0.2)",
                tickfont=dict(color=WHITE, size=12, family="'Barlow Condensed', sans-serif"),
            ),
        ),
        title=dict(text=f"<b>{player_name}</b> — Skills Profile",
                   font=dict(color=WHITE, size=16), x=0.5),
        showlegend=False,
        height=380,
    )
    return fig


def line_chart(labels: list, values: list, player_name: str, metric: str) -> go.Figure:
    """Draw a performance-over-time line chart."""
    fig = go.Figure()

    # Area fill
    fig.add_trace(go.Scatter(
        x=labels, y=values,
        fill="tozeroy",
        fillcolor="rgba(232, 41, 58, 0.18)",
        line=dict(color=RED, width=3),
        mode="lines+markers+text",
        marker=dict(color=WHITE, size=9, line=dict(color=RED, width=2)),
        text=[str(v) if v > 0 else "" for v in values],
        textposition="top center",
        textfont=dict(color=GOLD, size=11, family="'Barlow Condensed', sans-serif"),
        name=metric,
    ))

    fig.update_layout(
        **CHART_LAYOUT,
        xaxis=dict(
            gridcolor="rgba(255,255,255,0.08)",
            tickfont=dict(color=WHITE, size=12),
            title=dict(text="Season", font=dict(color=WHITE)),
        ),
        yaxis=dict(
            gridcolor="rgba(255,255,255,0.08)",
            tickfont=dict(color=WHITE, size=12),
            title=dict(text=metric, font=dict(color=WHITE)),
            zeroline=False,
        ),
        title=dict(text=f"<b>{player_name}</b> — {metric} by Season",
                   font=dict(color=WHITE, size=16), x=0.5),
        height=340,
    )
    return fig


def comparison_bar_chart(labels: list, p1_vals: list, p2_vals: list,
                          p1_name: str, p2_name: str,
                          winner_flags: list) -> go.Figure:
    """Side-by-side bar comparison of two players."""
    fig = go.Figure()

    # Bar colors: highlight winner per metric
    p1_colors = [GOLD if w == 1 else RED for w in winner_flags]
    p2_colors = [GOLD if w == 2 else BLUE_LT for w in winner_flags]

    fig.add_trace(go.Bar(
        name=p1_name,
        x=labels,
        y=p1_vals,
        marker=dict(color=p1_colors, line=dict(color=WHITE, width=0.5)),
        text=[f"{v:.1f}" if isinstance(v, float) else str(v) for v in p1_vals],
        textposition="outside",
        textfont=dict(color=WHITE, size=10),
    ))

    fig.add_trace(go.Bar(
        name=p2_name,
        x=labels,
        y=p2_vals,
        marker=dict(color=p2_colors, line=dict(color=WHITE, width=0.5)),
        text=[f"{v:.1f}" if isinstance(v, float) else str(v) for v in p2_vals],
        textposition="outside",
        textfont=dict(color=WHITE, size=10),
    ))

    fig.update_layout(
        **CHART_LAYOUT,
        barmode="group",
        bargap=0.2,
        bargroupgap=0.05,
        xaxis=dict(
            tickfont=dict(color=WHITE, size=11),
            gridcolor="rgba(255,255,255,0.05)",
        ),
        yaxis=dict(
            gridcolor="rgba(255,255,255,0.08)",
            tickfont=dict(color=WHITE, size=11),
            zeroline=False,
        ),
        legend=dict(
            font=dict(color=WHITE, size=12),
            bgcolor="rgba(0,0,0,0.3)",
            bordercolor=RED,
            borderwidth=1,
        ),
        title=dict(text=f"<b>{p1_name}</b> vs <b>{p2_name}</b> — Head-to-Head",
                   font=dict(color=WHITE, size=16), x=0.5),
        height=400,
    )
    return fig


def dual_radar_chart(axes: list, p1_vals: list, p2_vals: list,
                     p1_name: str, p2_name: str) -> go.Figure:
    """Overlay radar chart for two-player comparison."""
    axes_closed = axes + [axes[0]]
    p1_closed = p1_vals + [p1_vals[0]]
    p2_closed = p2_vals + [p2_vals[0]]

    fig = go.Figure()

    fig.add_trace(go.Scatterpolar(
        r=p1_closed, theta=axes_closed,
        fill="toself",
        fillcolor="rgba(232, 41, 58, 0.20)",
        line=dict(color=RED, width=2.5),
        name=p1_name,
        marker=dict(color=RED, size=5),
    ))
    fig.add_trace(go.Scatterpolar(
        r=p2_closed, theta=axes_closed,
        fill="toself",
        fillcolor="rgba(74, 95, 232, 0.20)",
        line=dict(color=BLUE_LT, width=2.5),
        name=p2_name,
        marker=dict(color=BLUE_LT, size=5),
    ))

    fig.update_layout(
        **CHART_LAYOUT,
        polar=dict(
            bgcolor=SURFACE,
            radialaxis=dict(
                visible=True, range=[0, 100],
                gridcolor="rgba(255,255,255,0.12)",
                tickfont=dict(color="rgba(255,255,255,0.5)", size=9),
                tickvals=[20, 40, 60, 80, 100],
            ),
            angularaxis=dict(
                gridcolor="rgba(255,255,255,0.18)",
                tickfont=dict(color=WHITE, size=11),
            ),
        ),
        legend=dict(font=dict(color=WHITE, size=12), bgcolor="rgba(0,0,0,0.3)"),
        title=dict(text="<b>Skills Overlap</b>",
                   font=dict(color=WHITE, size=16), x=0.5),
        height=380,
    )
    return fig


def form_gauge(score: float, player_name: str) -> go.Figure:
    """Circular gauge for form/performance score."""
    color = "#00FF88" if score >= 88 else GOLD if score >= 75 else RED

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        domain=dict(x=[0, 1], y=[0, 1]),
        title=dict(text=f"<b>Performance Score</b>",
                   font=dict(color=WHITE, size=14)),
        number=dict(font=dict(color=color, size=38, family="'Barlow Condensed', sans-serif")),
        gauge=dict(
            axis=dict(
                range=[50, 100],
                tickwidth=1,
                tickcolor=WHITE,
                tickfont=dict(color=WHITE, size=10),
            ),
            bar=dict(color=color, thickness=0.25),
            bgcolor=SURFACE,
            borderwidth=2,
            bordercolor=WHITE,
            steps=[
                dict(range=[50, 68], color="rgba(232,41,58,0.3)"),
                dict(range=[68, 80], color="rgba(255,215,0,0.2)"),
                dict(range=[80, 100], color="rgba(0,255,136,0.15)"),
            ],
            threshold=dict(
                line=dict(color=WHITE, width=3),
                thickness=0.85,
                value=score,
            ),
        ),
    ))

    fig.update_layout(
        paper_bgcolor=PAPER,
        font=dict(color=WHITE),
        margin=dict(l=20, r=20, t=60, b=20),
        height=240,
    )
    return fig


def mini_sparkline(labels: list, values: list) -> go.Figure:
    """Tiny sparkline for embedding in stat cards."""
    fig = go.Figure()
    non_zero = [(l, v) for l, v in zip(labels, values) if v > 0]
    if not non_zero:
        return fig

    lx, lv = zip(*non_zero)
    fig.add_trace(go.Scatter(
        x=list(lx), y=list(lv),
        mode="lines",
        line=dict(color=GOLD, width=2),
        fill="tozeroy",
        fillcolor="rgba(255,215,0,0.12)",
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=0, b=0),
        height=60,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        showlegend=False,
    )
    return fig
