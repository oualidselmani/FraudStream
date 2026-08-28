import os
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from pymongo import MongoClient

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://mongodb:27017")
REFRESH_SECONDS = 3
SCORE_LIMIT = 1000
# Toutes les fraudes sont utilisées pour les statistiques globales.
FRAUD_SCATTER_LIMIT = None
TABLE_LIMIT = 10

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
MIN_PERCENT = 0.015  # taille minimale visuelle : 1.5%


def clamp_score(value):
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def base_layout(title, height=360):
    return dict(
        title=dict(text=title, x=0, xanchor="left", font=dict(size=15, color=COLORS["text"])),
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=height,
        margin=dict(l=20, r=20, t=60, b=20),
        font=dict(family="Segoe UI, Roboto, sans-serif", size=12, color=COLORS["text"]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )


def axis_style(fig):
    fig.update_xaxes(showgrid=True, gridcolor=COLORS["grid"], zeroline=False, linecolor=COLORS["grid"])
    fig.update_yaxes(showgrid=True, gridcolor=COLORS["grid"], zeroline=False, linecolor=COLORS["grid"])
    return fig


def fetch_scores(collection, limit=SCORE_LIMIT):
    return [
        clamp_score(doc["score"])
        for doc in collection.find({}, {"score": 1, "_id": 0}).limit(limit)
        if "score" in doc
    ]


def apply_min_slice(counts, min_frac=MIN_PERCENT):
    """Boost tiny slices visually while keeping real values for hover."""
    total = sum(counts)
    if total == 0:
        return counts
    fracs = [c / total for c in counts]
    display = [max(f, min_frac) if f > 0 else 0 for f in fracs]
    display_total = sum(display)
    display = [d / display_total for d in display]
    return [d * total for d in display]


# ============================================================
# GRAPHE 1 — Répartition des transactions
# ============================================================
def build_distribution_chart(counts):
    # Préparation des données pour le graphique circulaire
    total = sum(counts)
    if total == 0:
        return None

    display_counts = apply_min_slice(counts)
    fracs = [c / total for c in counts]

    # Pull différencié : sépare visuellement les petites slices entre elles
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

    # Texte affiché sur chaque slice (toujours visible, même petites)
    text_labels = []
    for c, f in zip(counts, fracs):
        if c == 0:
            text_labels.append("")
        elif f < 0.01:
            text_labels.append(f"{f:.2%}")
        else:
            text_labels.append(f"{f:.1%}")

    # Labels courts pour la légende : "Normales  99.86%  (30,034)"
    short_labels = [
        f"{label}  {f*100:.2f}%  ({c:,})"
        for label, f, c in zip(LABELS, fracs, counts)
    ]

    fig = go.Figure(
        go.Pie(
            labels=short_labels,
            values=display_counts,
            hole=0.62,
            marker=dict(colors=COLOR_LIST, line=dict(color="white", width=2)),
            textinfo="text",
            textposition="outside",
            text=text_labels,
            customdata=[[c, f"{f:.2%}"] for c, f in zip(counts, fracs)],
            hovertemplate=(
                "<b>%{customdata[0]:,}</b> transactions<br>"
                "Part : %{customdata[1]}<extra></extra>"
            ),
            pull=pull,
            outsidetextfont=dict(size=11, color=COLORS["text"]),
        )
    )

    layout = base_layout("Repartition des transactions", height=420)
    layout["legend"] = dict(
        orientation="v",
        yanchor="middle",
        y=0.5,
        xanchor="left",
        x=1.02,
        font=dict(size=11),
        bgcolor="rgba(255,255,255,0.8)",
        bordercolor=COLORS["grid"],
        borderwidth=1,
    )
    layout["margin"] = dict(t=50, b=30, l=20, r=160)

    fig.update_layout(
        **layout,
        showlegend=True,
        annotations=[
            dict(
                text=f"<b>{total:,}</b><br><span style='font-size:11px;color:{COLORS['muted']}'>transactions</span>",
                x=0.5,
                y=0.5,
                font=dict(size=18, color=COLORS["text"]),
                showarrow=False,
            )
        ],
    )
    return fig


# ============================================================
# GRAPHE 2 — Distribution des scores de risque
# ============================================================
def build_score_chart(scores_fraudes, scores_suspectes):
    if not scores_fraudes and not scores_suspectes:
        return None

    # Création de l'histogramme des scores de risque
    fig = go.Figure()
    bins = dict(start=0, end=1, size=0.05)

    if scores_suspectes:
        fig.add_trace(go.Histogram(
            x=scores_suspectes,
            name="Suspectes",
            marker_color=COLORS["suspect"],
            opacity=0.55,
            xbins=bins,
        ))
    if scores_fraudes:
        fig.add_trace(go.Histogram(
            x=scores_fraudes,
            name="Fraudes",
            marker_color=COLORS["fraud"],
            opacity=0.55,
            xbins=bins,
        ))

    fig.add_vline(
        x=0.3, line_width=1.5, line_dash="dash", line_color=COLORS["threshold_suspect"],
        annotation_text="Seuil suspect (0.30)", annotation_position="top left",
    )
    fig.add_vline(
        x=0.7, line_width=1.5, line_dash="dash", line_color=COLORS["threshold_fraud"],
        annotation_text="Seuil fraude (0.70)", annotation_position="top right",
    )

    fig.update_layout(
        **base_layout("Distribution des transactions à risque", height=380),
        barmode="overlay",
        xaxis_title="Intervalle de score de risque",
        yaxis_title="Nombre de transactions",
        xaxis=dict(range=[0, 1], dtick=0.1),
    )
    return axis_style(fig)


# ============================================================
# GRAPHE 3 — Fraudes par montant / score
# ============================================================
def build_fraud_global_stats(records):
    """Calcule les statistiques globales sur toutes les fraudes."""
    if not records:
        return None

    df = pd.DataFrame(records)

    if "Amount" not in df.columns:
        return None

    df["Amount"] = pd.to_numeric(
        df["Amount"], errors="coerce"
    ).fillna(0).abs()

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
    """Construit le Top 15 et calcule son montant total."""
    if not records:
        return None, None

    df = pd.DataFrame(records)

    for col in ["Amount", "score"]:
        if col not in df.columns:
            return None, None

    df["Amount"] = pd.to_numeric(
        df["Amount"], errors="coerce"
    ).fillna(0).abs()

    df["score"] = df["score"].map(clamp_score)

    # Seulement les fraudes avec un montant positif.
    df_nonzero = df[df["Amount"] > 0].copy()

    if df_nonzero.empty:
        return None, {"count": 0, "total_amount": 0.0}

    # Le Top 15 est uniquement utilisé pour l'affichage.
    df_top = (
        df_nonzero
        .sort_values("Amount", ascending=False)
        .head(15)
        .copy()
    )

    # Statistiques propres au Top 15.
    top15_count = len(df_top)
    top15_total_amount = df_top["Amount"].sum()

    # Inverser pour placer la plus grosse fraude en haut.
    df_top = df_top.iloc[::-1]

    def risk_label(s):
        if s >= 0.95:
            return "Critique"
        elif s >= 0.85:
            return "Élevé"
        else:
            return "Modéré"

    df_top["risk"] = df_top["score"].map(risk_label)

    # Rang : Fraude #1 = plus grand montant.
    ranks = list(range(top15_count, 0, -1))
    df_top["rank"] = ranks

    colors = [
        "#7F1D1D" if s >= 0.95
        else "#DC2626" if s >= 0.85
        else "#F87171"
        for s in df_top["score"].tolist()
    ]

    labels = [
        f"Fraude #{r}"
        for r in df_top["rank"].tolist()
    ]

    amounts = df_top["Amount"].tolist()

    text_positions = [
        "outside" if a < 50 else "inside"
        for a in amounts
    ]

    text_colors = [
        COLORS["text"] if a < 50 else "white"
        for a in amounts
    ]

    fig = go.Figure(
        go.Bar(
            x=amounts,
            y=labels,
            orientation="h",
            marker=dict(
                color=colors,
                line=dict(width=0)
            ),
            customdata=list(
                zip(
                    df_top["score"].tolist(),
                    df_top["risk"].tolist(),
                    df_top["rank"].tolist()
                )
            ),
            hovertemplate=(
                "<b>Fraude #%{customdata[2]}</b><br>"
                "Montant : <b>%{x:.2f} €</b><br>"
                "Score : %{customdata[0]:.4f}<br>"
                "Risque : %{customdata[1]}"
                "<extra></extra>"
            ),
            text=[f"{a:.2f} €" for a in amounts],
            textposition=text_positions,
            textfont=dict(size=11, color=text_colors),
            cliponaxis=False,
        )
    )

    layout = base_layout(
        "Top 15 des fraudes par montant",
        height=max(320, len(df_top) * 28 + 80)
    )

    layout["margin"] = dict(t=60, b=40, l=80, r=70)

    fig.update_layout(
        **layout,
        xaxis=dict(
            title="Montant (€)",
            rangemode="tozero"
        ),
        yaxis=dict(title=""),
    )

    return axis_style(fig), {
        "count": top15_count,
        "total_amount": top15_total_amount,
    }


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


st.set_page_config(
    page_title="Detection de fraude",
    page_icon="shield",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
    .block-container { padding-top: 1.25rem; padding-bottom: 1rem; max-width: 1200px; }
    div[data-testid="stMetric"] {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 0.75rem 1rem;
    }
    div[data-testid="stMetricLabel"] { color: #64748B; font-size: 0.85rem; }
    div[data-testid="stMetricValue"] { color: #0F172A; }
    h1 { font-size: 1.75rem !important; font-weight: 600 !important; color: #0F172A; }
    hr { margin: 1.25rem 0; border-color: #E2E8F0; }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_db():
    return MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)["fraud_db"]


try:
    db = get_db()
except Exception as exc:
    st.error(f"Connexion MongoDB impossible : {exc}")
    st.stop()

header, refresh_col = st.columns([4, 1])
with header:
    st.title("Detection de fraude en temps reel")
    st.caption("Kafka · Spark Streaming · MongoDB · XGBoost")
with refresh_col:
    st.markdown("<div style='height:1.6rem'></div>", unsafe_allow_html=True)
    auto_refresh = st.toggle("Actualisation auto", value=True)

placeholder = st.empty()

while True:
    with placeholder.container():
        counts = [
            db["normales"].count_documents({}),
            db["suspectes"].count_documents({}),
            db["fraudes"].count_documents({}),
        ]
        total = sum(counts)
        percentages = [(count / total * 100) if total else 0.0 for count in counts]

        # ========================================================
        # INDICATEURS — Résumé des transactions
        # ========================================================
        st.markdown("""
<style>
    .section-space {
        height: 80px;
    }

</style>
""", unsafe_allow_html=True)

        st.markdown("<div class='section-space'></div>", unsafe_allow_html=True)
        st.markdown("### Statistiques globales des transactions")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Normales", f"{counts[0]:,}", f"{percentages[0]:.1f} %")
        m2.metric("Suspectes", f"{counts[1]:,}", f"{percentages[1]:.2f} %")
        m3.metric("Fraudes", f"{counts[2]:,}", f"{percentages[2]:.2f} %")
        m4.metric("Total analyse", f"{total:,}")

        # ========================================================
        # STATISTIQUES GLOBALES — TOUTES LES FRAUDES
        # ========================================================

        fraud_query = (
            db["fraudes"]
            .find(
                {},
                {"Amount": 1, "score": 1}
            )
            .sort("_id", -1)
        )

        if FRAUD_SCATTER_LIMIT is not None:
            fraud_query = fraud_query.limit(FRAUD_SCATTER_LIMIT)

        fraud_records = list(fraud_query)

        global_stats = build_fraud_global_stats(fraud_records)



        st.markdown("### Statistiques globales des fraudes")

        if global_stats:
            total_fraudes = global_stats["n_total"]

            pct_avec_montant = (
                global_stats["n_nonzero"] / total_fraudes * 100
                if total_fraudes else 0
            )


            pct_zero = (
                global_stats["n_zero"] / total_fraudes * 100
                if total_fraudes else 0
            )



            g1, g2, g3, g4 = st.columns(4)

            g1.metric(
                "Fraudes au total",
                f"{global_stats['n_total']:,}",
            )

            g2.metric(
                "Avec montant",
                f"{global_stats['n_nonzero']:,}",
                f"{pct_avec_montant:.2f} %"
            )

            g3.metric(
                "À 0 €",
                f"{global_stats['n_zero']:,}",
                f"{pct_zero:.2f} %"
            )

            g4.metric(
                "Montant total",
                f"{global_stats['total_amount']:,.2f} €"
            )
        else:
            st.caption(
                "Aucune fraude détectée pour l'instant."
            )



            
        


        # ========================================================
        st.markdown( "<div class='section-space'></div>", unsafe_allow_html=True)
        # GRAPHIQUES 1 ET 2 — Répartition + scores de risque
        # ========================================================
        

        st.markdown("### La representation graphique des transactions")

        chart_left, chart_right = st.columns(2)

        with chart_left:
            distribution_fig = build_distribution_chart(counts)
            if distribution_fig:
                st.plotly_chart(distribution_fig, use_container_width=True, config={"displayModeBar": False})
            else:
                st.markdown("**Repartition des transactions**")
                st.caption("Aucune transaction analysee pour le moment.")

        with chart_right:
            scores_fraudes = fetch_scores(db["fraudes"])
            scores_suspectes = fetch_scores(db["suspectes"])
            score_fig = build_score_chart(scores_fraudes, scores_suspectes)
            if score_fig:
                st.plotly_chart(score_fig, use_container_width=True, config={"displayModeBar": False})
            else:
                st.markdown("**Distribution des scores**")
                st.caption("Les scores apparaitront apres classification des transactions.")

        # ========================================================
        # GRAPHIQUE 3 — Analyse des fraudes
        # ========================================================


        # ========================================================
        # TOP 15 — STATISTIQUES + GRAPHE
        # ========================================================


        scatter_fig, top15_stats = build_top_fraud_chart(
            fraud_records
        )

        if top15_stats and top15_stats["count"] > 0:

            

            if scatter_fig:
                st.plotly_chart(
                    scatter_fig,
                    use_container_width=True,
                    config={"displayModeBar": False}
                )

            
            t1, t2 = st.columns(2)
            t1.metric(
                "Fraudes affichées",
                f"{top15_stats['count']:,}"
            )

            t2.metric(
                "Montant total du Top 15",
                f"{top15_stats['total_amount']:,.2f} €"
            )


        else:
            st.caption(
                "Aucune fraude avec montant disponible pour le Top 15."
            )




        st.markdown("<div class='section-space'></div>", unsafe_allow_html=True)
       
        
        # ========================================================

        st.markdown("### La visualisation tabulaire des transactions à risque")

        table_left, table_right = st.columns(2)
        with table_left:
            recent_frauds = list(
                db["fraudes"]
                .find({}, {"Amount": 1, "score": 1})
                .sort("_id", -1)
                .limit(TABLE_LIMIT)
            )
            render_table("Dernieres fraudes", recent_frauds, "Aucune fraude enregistree.")

        with table_right:
            recent_suspects = list(
                db["suspectes"]
                .find({}, {"Amount": 1, "score": 1})
                .sort("_id", -1)
                .limit(TABLE_LIMIT)
            )
            render_table("Dernieres transactions suspectes", recent_suspects, "Aucune alerte suspecte.")
        
        # ========================================================
        # INFORMATIONS — Heure de la dernière mise à jour
        # ========================================================
        morocco_tz = ZoneInfo("Africa/Casablanca")
        now_morocco = datetime.now(morocco_tz)

        st.caption(
        f"Dernière mise à jour : {now_morocco.strftime('%d/%m/%Y %H:%M:%S')}"
        )
       

    if not auto_refresh:
        break
    time.sleep(REFRESH_SECONDS)
    placeholder.empty()