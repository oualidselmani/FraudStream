"""Fonctions et constantes partagees entre les pages du dashboard."""
import os
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from pymongo import MongoClient

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://mongodb:27017")
REFRESH_SECONDS = 3
SCORE_LIMIT = 1000
FRAUD_SCATTER_LIMIT = None
TABLE_LIMIT = 10
MOROCCO_TZ = ZoneInfo("Africa/Casablanca")

COLORS = {
    "normal": "#059669",
    "suspect": "#D97706",
    "fraud": "#DC2626",
    "text": "#0F172A",
    "muted": "#64748B",
    "grid": "#E2E8F0",
    "threshold_suspect": "#D97706",
    "threshold_fraud": "#DC2626",
}

LABELS = ["Normales", "Suspectes", "Fraudes"]
COLOR_LIST = [COLORS["normal"], COLORS["suspect"], COLORS["fraud"]]
MIN_PERCENT = 0.015
CHART_HEIGHT = 400

PLOTLY_CHART_CONFIG = {"displayModeBar": False, "responsive": True}

HOVERLABEL = dict(
    bgcolor="rgba(255, 255, 255, 0.96)",
    bordercolor="rgba(226, 232, 240, 0.95)",
    font=dict(family="Inter, Segoe UI, Roboto, sans-serif", size=12, color=COLORS["text"]),
    align="left",
)

KPI_VARIANTS = {
    "normal": {"accent": COLORS["normal"], "soft": "rgba(5, 150, 105, 0.12)"},
    "suspect": {"accent": COLORS["suspect"], "soft": "rgba(217, 119, 6, 0.12)"},
    "fraud": {"accent": COLORS["fraud"], "soft": "rgba(220, 38, 38, 0.12)"},
    "total": {"accent": "#6366F1", "soft": "rgba(99, 102, 241, 0.12)"},
    "amount": {"accent": "#0EA5E9", "soft": "rgba(14, 165, 233, 0.12)"},
    "neutral": {"accent": COLORS["muted"], "soft": "rgba(100, 116, 139, 0.10)"},
}

KPI_ICONS = {
    "normal": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M20 6 9 17l-5-5"/></svg>'
    ),
    "suspect": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round">'
        '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/>'
        '<path d="M12 9v4"/><path d="M12 17h.01"/></svg>'
    ),
    "fraud": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round">'
        '<circle cx="12" cy="12" r="10"/><path d="m15 9-6 6"/><path d="m9 9 6 6"/></svg>'
    ),
    "total": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round">'
        '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/>'
        '<rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>'
        '</svg>'
    ),
    "amount": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round">'
        '<circle cx="12" cy="12" r="10"/><path d="M16 8h-6a2 2 0 1 0 0 4h4a2 2 0 0 1 0 4H8"/>'
        '<path d="M12 18V6"/></svg>'
    ),
    "neutral": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
        'stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M3 3v18h18"/><path d="m7 16 4-4 4 4 5-6"/></svg>'
    ),
}


def clamp_score(value):
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def base_layout(title, height=CHART_HEIGHT):
    return dict(
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=height,
        margin=dict(l=20, r=20, t=30, b=20),
        font=dict(family="Inter, Segoe UI, Roboto, sans-serif", size=12, color=COLORS["text"]),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor="rgba(255,255,255,0.72)",
            bordercolor="rgba(226,232,240,0.8)",
            borderwidth=1,
            font=dict(size=11, color=COLORS["text"]),
        ),
        hoverlabel=HOVERLABEL,
        hovermode="closest",
    )


def axis_style(fig, *, y_grid=True):
    axis_font = dict(size=11, color=COLORS["muted"])
    fig.update_xaxes(
        showgrid=True,
        gridcolor="rgba(226, 232, 240, 0.55)",
        gridwidth=1,
        zeroline=False,
        linecolor="rgba(226, 232, 240, 0.85)",
        tickfont=axis_font,
        title_font=axis_font,
    )
    fig.update_yaxes(
        showgrid=y_grid,
        gridcolor="rgba(226, 232, 240, 0.55)",
        gridwidth=1,
        zeroline=False,
        linecolor="rgba(226, 232, 240, 0.85)",
        tickfont=axis_font,
        title_font=axis_font,
    )
    return fig


def _score_histogram_bins(scores, bin_size=0.05):
    """Retourne (centres, comptes, intervalles [debut, fin]) pour l'histogramme."""
    if not scores:
        return [], [], []

    n_bins = int(round(1 / bin_size))
    edges = [i * bin_size for i in range(n_bins + 1)]
    counts = [0] * n_bins
    for score in scores:
        idx = min(int(score / bin_size), n_bins - 1)
        counts[idx] += 1
    centers = [(edges[i] + edges[i + 1]) / 2 for i in range(n_bins)]
    bin_ranges = list(zip(edges[:-1], edges[1:]))
    return centers, counts, bin_ranges


def _composition_bar_segments(segments):
    if not segments:
        return ""

    total = sum(value for _, value in segments)
    if total <= 0:
        return ""

    parts = []
    offset = 0.0
    for color, value in segments:
        width = (value / total) * 100
        parts.append(
            f'<span class="kpi-stack-segment" style="left:{offset:.4f}%;width:{width:.4f}%;'
            f'background:{color};"></span>'
        )
        offset += width
    return "".join(parts)


def render_kpi_card(column, label, value, *, context=None, variant="neutral", share_pct=None, composition=None):
    """Carte KPI glassmorphism avec accent, icone et indicateur de part."""
    style = KPI_VARIANTS.get(variant, KPI_VARIANTS["neutral"])
    icon = KPI_ICONS.get(variant, KPI_ICONS["neutral"])
    context_html = f'<div class="kpi-context">{context}</div>' if context else ""
    share_html = ""
    if share_pct is not None:
        clamped = max(0.0, min(100.0, float(share_pct)))
        share_html = (
            f'<div class="kpi-share-track" aria-hidden="true">'
            f'<div class="kpi-share-fill" style="width:{clamped:.2f}%;background:{style["accent"]};"></div>'
            f"</div>"
        )
    elif composition:
        share_html = f'<div class="kpi-stack-track">{_composition_bar_segments(composition)}</div>'

    column.markdown(
        f"""
        <div class="kpi-card" style="--kpi-accent:{style['accent']};--kpi-soft:{style['soft']};">
            <div class="kpi-accent-bar"></div>
            <div class="kpi-card-top">
                <div class="kpi-label">{label}</div>
                <div class="kpi-icon">{icon}</div>
            </div>
            <div class="kpi-value">{value}</div>
            {context_html}
            {share_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def fetch_scores(collection, limit=SCORE_LIMIT):
    return [
        clamp_score(doc["score"])
        for doc in collection.find({}, {"score": 1, "_id": 0}).limit(limit)
        if "score" in doc
    ]


def apply_min_slice(counts, min_frac=MIN_PERCENT):
    total = sum(counts)
    if total == 0:
        return counts
    fracs = [c / total for c in counts]
    display = [max(f, min_frac) if f > 0 else 0 for f in fracs]
    display_total = sum(display)
    display = [d / display_total for d in display]
    return [d * total for d in display]


def build_distribution_chart(counts):
    total = sum(counts)
    if total == 0:
        return None

    display_counts = apply_min_slice(counts)
    fracs = [c / total for c in counts]

    pull = []
    for f in fracs:
        if f == 0:
            pull.append(0)
        elif f < 0.005:
            pull.append(0.10)
        elif f < 0.01:
            pull.append(0.07)
        else:
            pull.append(0)

    text_labels = []
    for c, f in zip(counts, fracs):
        if c == 0:
            text_labels.append("")
        elif f < 0.01:
            text_labels.append(f"{f:.2%}")
        else:
            text_labels.append(f"{f:.1%}")

    short_labels = [
        f"{label}  {f*100:.2f}%  ({c:,})"
        for label, f, c in zip(LABELS, fracs, counts)
    ]

    fig = go.Figure(
        go.Pie(
            labels=short_labels,
            values=display_counts,
            hole=0.64,
            marker=dict(
                colors=COLOR_LIST,
                line=dict(color="rgba(255,255,255,0.92)", width=2.5),
            ),
            textinfo="text",
            textposition="outside",
            text=text_labels,
            customdata=[[c, f"{f:.2%}"] for c, f in zip(counts, fracs)],
            hovertemplate=(
                "<b>%{label}</b><br>"
                "Volume : <b>%{customdata[0]:,}</b><br>"
                "Part : %{customdata[1]}<extra></extra>"
            ),
            pull=pull,
            outsidetextfont=dict(size=11, color=COLORS["muted"]),
            rotation=18,
            sort=False,
        )
    )

    layout = base_layout("Repartition des transactions", height=CHART_HEIGHT)
    # Legende ancree en haut a droite (au lieu d'un centrage vertical qui la
    # faisait flotter, deconnectee visuellement du donut).
    layout["legend"] = dict(
        orientation="v",
        yanchor="top",
        y=0.97,
        xanchor="left",
        x=1.04,
        font=dict(size=11, color=COLORS["text"]),
        bgcolor="rgba(255,255,255,0.72)",
        bordercolor="rgba(226,232,240,0.85)",
        borderwidth=1,
    )
    layout["margin"] = dict(t=20, b=30, l=20, r=150)

    fig.update_layout(
        **layout,
        showlegend=True,
        annotations=[
            dict(
                text=(
                    f"<span style='font-size:24px;font-weight:700;color:{COLORS['text']}'>"
                    f"{total:,}</span><br>"
                    f"<span style='font-size:11px;color:{COLORS['muted']}'>transactions</span>"
                ),
                x=0.5,
                y=0.5,
                font=dict(family="Inter, Segoe UI, Roboto, sans-serif"),
                showarrow=False,
            )
        ],
    )
    fig.update_traces(
        hoverlabel=HOVERLABEL,
        marker=dict(line=dict(width=2.5, color="rgba(255,255,255,0.92)")),
    )
    return fig


def build_score_chart(scores_fraudes, scores_suspectes):
    """Histogramme des scores : au survol affiche 'De X a Y : N fraudes/suspectes'.
    Couleurs volontairement foncees (rouge/orange soutenus). La courbe de lissage
    utilise une interpolation lineaire (pas spline) pour eviter tout effet de
    depassement visuel sur la derniere tranche, tres majoritaire, qui donnait
    l'impression que la barre etait coupee en deux."""
    if not scores_fraudes and not scores_suspectes:
        return None

    fig = go.Figure()
    series = []
    if scores_suspectes:
        series.append(("Suspectes", scores_suspectes, "#B45309", "rgba(180, 83, 9, 0.32)"))
    if scores_fraudes:
        series.append(("Fraudes", scores_fraudes, "#991B1B", "rgba(153, 27, 27, 0.32)"))

    for name, scores, color, fill_color in series:
        centers, counts, bin_ranges = _score_histogram_bins(scores)
        if not centers:
            continue

        label = name.lower()
        customdata = [(start, end, count) for (start, end), count in zip(bin_ranges, counts)]
        hovertemplate = (
            f"De %{{customdata[0]:.2f}} a %{{customdata[1]:.2f}}<br>"
            f"<b>%{{customdata[2]}}</b> {label}"
            "<extra></extra>"
        )

        fig.add_trace(
            go.Bar(
                x=centers,
                y=counts,
                name=name,
                marker=dict(color=color, opacity=0.55, line=dict(width=0)),
                width=0.045,
                customdata=customdata,
                hovertemplate=hovertemplate,
                showlegend=True,
            )
        )
        fig.add_trace(
            go.Scatter(
                x=centers,
                y=counts,
                name=name,
                mode="lines",
                line=dict(color=color, width=2.4, shape="linear"),
                fill="tozeroy",
                fillcolor=fill_color,
                customdata=customdata,
                hovertemplate=hovertemplate,
                showlegend=False,
            )
        )

    fig.add_vline(
        x=0.3,
        line_width=1.5,
        line_dash="dot",
        line_color=COLORS["threshold_suspect"],
        annotation_text="Seuil suspect (0.30)",
        annotation_position="top left",
        annotation_font=dict(size=10, color=COLORS["muted"]),
    )
    fig.add_vline(
        x=0.7,
        line_width=1.5,
        line_dash="dot",
        line_color=COLORS["threshold_fraud"],
        annotation_text="Seuil fraude (0.70)",
        annotation_position="top right",
        annotation_font=dict(size=10, color=COLORS["muted"]),
    )

    layout = base_layout("Distribution des transactions a risque", height=CHART_HEIGHT)
    layout.update(
        barmode="overlay",
        xaxis_title="Intervalle de score de risque",
        yaxis_title="Nombre de transactions",
        xaxis=dict(range=[0, 1], dtick=0.1, tickformat=".1f"),
        yaxis=dict(tickformat=",d"),
    )
    fig.update_layout(**layout)
    return axis_style(fig)


def build_fraud_global_stats(records):
    if not records:
        return None

    df = pd.DataFrame(records)
    if "Amount" not in df.columns:
        return None

    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0).abs()

    n_total = len(df)
    n_nonzero = int((df["Amount"] > 0).sum())
    n_zero = int((df["Amount"] == 0).sum())
    total_amount = df["Amount"].sum()

    return {
        "n_total": n_total,
        "n_nonzero": n_nonzero,
        "n_zero": n_zero,
        "total_amount": total_amount,
    }


def build_top_fraud_chart(records):
    if not records:
        return None, None

    df = pd.DataFrame(records)
    for col in ["Amount", "score"]:
        if col not in df.columns:
            return None, None

    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0).abs()
    df["score"] = df["score"].map(clamp_score)

    df_nonzero = df[df["Amount"] > 0].copy()
    if df_nonzero.empty:
        return None, {"count": 0, "total_amount": 0.0}

    df_top = df_nonzero.sort_values("Amount", ascending=False).head(15).copy()

    top15_count = len(df_top)
    top15_total_amount = df_top["Amount"].sum()

    df_top = df_top.iloc[::-1]

    def risk_label(s):
        if s >= 0.95:
            return "Critique"
        elif s >= 0.85:
            return "Eleve"
        else:
            return "Modere"

    df_top["risk"] = df_top["score"].map(risk_label)

    ranks = list(range(top15_count, 0, -1))
    df_top["rank"] = ranks

    colors = [
        "#7F1D1D" if s >= 0.95
        else "#DC2626" if s >= 0.85
        else "#F87171"
        for s in df_top["score"].tolist()
    ]

    labels = [f"Fraude #{r}" for r in df_top["rank"].tolist()]
    amounts = df_top["Amount"].tolist()

    text_positions = ["outside" if a < 50 else "inside" for a in amounts]
    text_colors = [COLORS["text"] if a < 50 else "white" for a in amounts]

    fig = go.Figure(
        go.Bar(
            x=amounts,
            y=labels,
            orientation="h",
            marker=dict(
                color=colors,
                line=dict(color="rgba(255,255,255,0.65)", width=1),
                opacity=0.92,
            ),
            customdata=list(zip(
                df_top["score"].tolist(),
                df_top["risk"].tolist(),
                df_top["rank"].tolist()
            )),
            hovertemplate=(
                "<b>Fraude #%{customdata[2]}</b><br>"
                "Montant : <b>%{x:,.2f} €</b><br>"
                "Score : %{customdata[0]:.4f}<br>"
                "Risque : %{customdata[1]}"
                "<extra></extra>"
            ),
            text=[f"{a:,.2f} €" for a in amounts],
            textposition=text_positions,
            textfont=dict(size=11, color=text_colors),
            cliponaxis=False,
        )
    )

    layout = base_layout("Top 15 des fraudes par montant", height=max(CHART_HEIGHT, len(df_top) * 28 + 80))
    layout["margin"] = dict(t=25, b=40, l=80, r=70)

    fig.update_layout(
        **layout,
        xaxis=dict(
            title="Montant (€)",
            rangemode="tozero",
            tickformat=",.2f",
            gridcolor="rgba(226, 232, 240, 0.55)",
        ),
        yaxis=dict(title="", showgrid=False),
        bargap=0.22,
    )
    fig.update_traces(hoverlabel=HOVERLABEL)

    return axis_style(fig, y_grid=False), {"count": top15_count, "total_amount": top15_total_amount}


def render_table(title, records, empty_message):
    st.markdown(f"**{title}**")
    if not records:
        st.caption(empty_message)
        return

    df = pd.DataFrame(records)
    df["score"] = df["score"].map(clamp_score)
    df["Heure"] = df["_id"].apply(
        lambda oid: (oid.generation_time + pd.Timedelta(hours=1)).strftime("%H:%M:%S")
    )
    df = df[["Amount", "score", "Heure"]]
    df = df.rename(columns={"Amount": "Montant", "score": "Score"})

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Montant": st.column_config.NumberColumn(format="%.2f"),
            "Score": st.column_config.NumberColumn(format="%.4f", min_value=0, max_value=1),
            "Heure": st.column_config.TextColumn(),
        },
    )


def render_navbar(title, subtitle):
    """Barre superieure : titre a gauche, infos contextuelles a droite (pilule sombre)."""
    st.markdown(
        f"""
        <div class="app-navbar">
            <div class="app-navbar-left">
                <div class="app-navbar-title">{title}</div>
                <div class="app-navbar-subtitle">{subtitle}</div>
            </div>
            <div class="app-navbar-right">
                <span class="navbar-pill">{now_morocco_str()}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def chart_key(prefix):
    """Cle Streamlit unique par rafraichissement (evite DuplicateElementId en boucle)."""
    state_key = f"_chart_key_{prefix}"
    if state_key not in st.session_state:
        st.session_state[state_key] = 0
    st.session_state[state_key] += 1
    return f"{prefix}_{st.session_state[state_key]}"


def section_title(text):
    """En-tete de section : bandeau glass avec accent lateral (pas de fond sombre)."""
    st.markdown(
        f"""
        <div class="section-heading">
            <span class="section-heading-accent"></span>
            <span class="section-heading-text">{text}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def chart_title(title, subtitle=None, accent="#6366F1"):
    """Titre au-dessus d'un graphique, integre au theme glass."""
    subtitle_html = f'<div class="chart-heading-sub">{subtitle}</div>' if subtitle else ""
    st.markdown(
        f"""
        <div class="chart-heading" style="--chart-accent:{accent};">
            <div class="chart-heading-title">{title}</div>
            {subtitle_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def inject_global_style():
    st.markdown("""
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@600;700;800&display=swap" rel="stylesheet">
    <style>
        html, body, [class*="css"] {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
        }

        h1, h2, h3, .section-heading, .section-heading-text, .chart-heading-title, .sidebar-brand-text {
            font-family: 'Plus Jakarta Sans', 'Inter', sans-serif !important;
        }

        .stApp {
            background: linear-gradient(135deg, #EEF2FF 0%, #F8FAFC 45%, #ECFDF5 100%);
        }

        .block-container { padding-top: 1.75rem; padding-bottom: 2rem; max-width: 1200px; }

        h1 {
            font-size: 2rem !important;
            font-weight: 800 !important;
            letter-spacing: -0.03em;
            color: #0F172A;
        }

        .kpi-card {
            position: relative;
            overflow: hidden;
            background: rgba(255, 255, 255, 0.55);
            backdrop-filter: blur(14px);
            -webkit-backdrop-filter: blur(14px);
            border: 1px solid rgba(255, 255, 255, 0.62);
            border-radius: 16px;
            padding: 1rem 1.15rem 1.05rem 1.15rem;
            box-shadow: 0 4px 24px rgba(15, 23, 42, 0.06);
            transition: transform 0.22s ease, box-shadow 0.22s ease, border-color 0.22s ease;
        }
        .kpi-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 28px rgba(15, 23, 42, 0.10);
            border-color: rgba(255, 255, 255, 0.82);
        }
        .kpi-accent-bar {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 3px;
            background: linear-gradient(90deg, var(--kpi-accent), rgba(255,255,255,0));
            opacity: 0.95;
        }
        .kpi-card-top {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.75rem;
            margin-bottom: 0.55rem;
        }
        .kpi-label {
            color: #64748B;
            font-size: 0.72rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            line-height: 1.2;
        }
        .kpi-icon {
            width: 28px;
            height: 28px;
            border-radius: 9px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            color: var(--kpi-accent);
            background: var(--kpi-soft);
            flex-shrink: 0;
        }
        .kpi-icon svg {
            width: 15px;
            height: 15px;
        }
        .kpi-value {
            color: #0F172A;
            font-family: 'Plus Jakarta Sans', 'Inter', sans-serif;
            font-size: 1.85rem;
            font-weight: 800;
            letter-spacing: -0.03em;
            line-height: 1.05;
            animation: kpiValueIn 0.55s ease both;
        }
        .kpi-context {
            margin-top: 0.35rem;
            color: #64748B;
            font-size: 0.82rem;
            font-weight: 500;
            line-height: 1.35;
        }
        .kpi-share-track,
        .kpi-stack-track {
            position: relative;
            margin-top: 0.75rem;
            height: 5px;
            border-radius: 999px;
            background: rgba(226, 232, 240, 0.75);
            overflow: hidden;
        }
        .kpi-share-fill {
            height: 100%;
            border-radius: 999px;
            transition: width 0.45s ease;
        }
        .kpi-stack-segment {
            position: absolute;
            top: 0;
            height: 100%;
            border-radius: 999px;
        }
        @keyframes kpiValueIn {
            from { opacity: 0; transform: translateY(6px); }
            to { opacity: 1; transform: translateY(0); }
        }

        div[data-testid="stPlotlyChart"], div[data-testid="stDataFrame"] {
            background: rgba(255, 255, 255, 0.5);
            backdrop-filter: blur(14px);
            -webkit-backdrop-filter: blur(14px);
            border: 1px solid rgba(255, 255, 255, 0.6);
            border-radius: 16px;
            padding: 1.1rem 1.2rem;
            box-shadow: 0 4px 24px rgba(15, 23, 42, 0.06);
        }

        section[data-testid="stSidebar"] {
            background: #0B0F1A;
            border-right: none;
        }
        section[data-testid="stSidebar"] * {
            color: #E2E8F0 !important;
        }
        section[data-testid="stSidebar"] hr {
            border-color: rgba(255,255,255,0.08) !important;
        }
        section[data-testid="stSidebar"] .stCaption, section[data-testid="stSidebar"] small {
            color: #94A3B8 !important;
        }

        .sidebar-brand {
            display: flex;
            align-items: center;
            gap: 0.6rem;
            margin: 0.25rem 0 1.1rem 0;
        }
        .sidebar-brand-mark {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 32px;
            height: 32px;
            border-radius: 9px;
            background: linear-gradient(135deg, #6366F1, #EC4899);
            color: white !important;
            font-weight: 800;
            font-family: 'Plus Jakarta Sans', sans-serif;
            font-size: 1rem;
        }
        .sidebar-brand-text {
            font-size: 1.05rem;
            font-weight: 700;
            letter-spacing: -0.01em;
            color: #F8FAFC !important;
        }

        section[data-testid="stSidebarNav"] a,
        div[data-testid="stSidebarNav"] a {
            border-radius: 10px;
            font-weight: 500;
            margin: 2px 0;
            color: #CBD5E1 !important;
        }
        section[data-testid="stSidebarNav"] a:hover,
        div[data-testid="stSidebarNav"] a:hover {
            background: rgba(255,255,255,0.06) !important;
        }
        section[data-testid="stSidebarNav"] a[aria-current="page"],
        div[data-testid="stSidebarNav"] a[aria-current="page"] {
            background: rgba(255,255,255,0.12) !important;
            color: #FFFFFF !important;
        }
        section[data-testid="stSidebarNav"] a svg,
        div[data-testid="stSidebarNav"] a svg {
            fill: #CBD5E1 !important;
        }
        section[data-testid="stSidebarNav"] a[aria-current="page"] svg,
        div[data-testid="stSidebarNav"] a[aria-current="page"] svg {
            fill: #FFFFFF !important;
        }

        section[data-testid="stSidebar"] label { color: #E2E8F0 !important; }

        div[data-testid="stDecoration"] {
            background: linear-gradient(90deg, #059669, #10B981) !important;
            height: 4px !important;
        }
        header[data-testid="stHeader"] {
            background: rgba(0,0,0,0) !important;
        }

        #MainMenu { visibility: hidden; }
        div[data-testid="stToolbar"] { visibility: hidden; height: 0; position: fixed; }
        div[data-testid="stAppDeployButton"] { display: none; }
        footer { visibility: hidden; height: 0; }

        .app-navbar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: rgba(15, 23, 42, 0.95);
            border-radius: 18px;
            padding: 1.1rem 1.4rem;
            margin-bottom: 1.75rem;
            box-shadow: 0 8px 28px rgba(15, 23, 42, 0.15);
        }
        .app-navbar-title {
            font-family: 'Plus Jakarta Sans', sans-serif;
            font-size: 1.4rem;
            font-weight: 800;
            color: #FFFFFF;
            letter-spacing: -0.02em;
            line-height: 1.15;
        }
        .app-navbar-subtitle {
            font-size: 0.85rem;
            color: #94A3B8;
            margin-top: 0.15rem;
        }
        .navbar-pill {
            display: inline-flex;
            align-items: center;
            background: rgba(255,255,255,0.08);
            color: #E2E8F0;
            font-size: 0.8rem;
            font-weight: 500;
            padding: 0.45rem 0.9rem;
            border-radius: 999px;
        }

        .section-heading {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            width: 100%;
            background: rgba(255, 255, 255, 0.62);
            backdrop-filter: blur(14px);
            -webkit-backdrop-filter: blur(14px);
            border: 1px solid rgba(255, 255, 255, 0.75);
            border-radius: 14px;
            padding: 0.75rem 1.15rem;
            margin-top: 1.75rem;
            margin-bottom: 1.1rem;
            box-shadow: 0 4px 20px rgba(15, 23, 42, 0.06);
        }
        .section-heading-accent {
            width: 4px;
            height: 1.35rem;
            border-radius: 999px;
            background: linear-gradient(180deg, #6366F1, #059669);
            flex-shrink: 0;
        }
        .section-heading-text {
            font-size: 1.02rem;
            font-weight: 700;
            letter-spacing: -0.02em;
            color: #0F172A !important;
            line-height: 1.2;
        }

        .chart-heading {
            padding: 0.65rem 0.95rem 0.75rem;
            margin-bottom: 0.45rem;
            border-left: 3px solid var(--chart-accent, #6366F1);
            background: rgba(255, 255, 255, 0.42);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border-radius: 0 12px 12px 0;
            box-shadow: 0 2px 12px rgba(15, 23, 42, 0.04);
        }
        .chart-heading-title {
            font-size: 0.95rem;
            font-weight: 700;
            letter-spacing: -0.02em;
            color: #0F172A;
            line-height: 1.25;
        }
        .chart-heading-sub {
            margin-top: 0.18rem;
            font-size: 0.78rem;
            font-weight: 500;
            color: #64748B;
            line-height: 1.35;
        }

        .sidebar-spacer { height: 3.5rem; }
        .sidebar-status-card {
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 14px;
            padding: 0.9rem 1rem;
        }
        .sidebar-status-row {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            margin-bottom: 0.35rem;
        }
        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #10B981;
            box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.2);
            flex-shrink: 0;
        }
        .status-label {
            font-size: 0.85rem;
            font-weight: 600;
            color: #F1F5F9 !important;
        }
        .sidebar-status-sub {
            font-size: 0.75rem;
            color: #94A3B8 !important;
            line-height: 1.5;
        }

        hr { border-color: rgba(15, 23, 42, 0.08); }
    </style>
    """, unsafe_allow_html=True)


@st.cache_resource
def get_db():
    return MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)["fraud_db"]


def connect_or_stop():
    try:
        return get_db()
    except Exception as exc:
        st.error(f"Connexion MongoDB impossible : {exc}")
        st.stop()


def now_morocco_str():
    return datetime.now(MOROCCO_TZ).strftime("%d/%m/%Y %H:%M:%S")