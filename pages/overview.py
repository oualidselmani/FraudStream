import time

import streamlit as st

from common import (
    COLORS,
    PLOTLY_CHART_CONFIG,
    build_distribution_chart,
    build_score_chart,
    chart_key,
    chart_title,
    connect_or_stop,
    fetch_scores,
    now_morocco_str,
    render_kpi_card,
    section_title,
    REFRESH_SECONDS,
)

st.title("Detection de fraude en temps reel")
st.caption("Vue d'ensemble")

db = connect_or_stop()
placeholder = st.empty()
auto_refresh = st.session_state.get("auto_refresh", True)

while True:
    with placeholder.container():
        counts = [
            db["normales"].count_documents({}),
            db["suspectes"].count_documents({}),
            db["fraudes"].count_documents({}),
        ]
        total = sum(counts)
        percentages = [(c / total * 100) if total else 0.0 for c in counts]

        section_title("Statistiques globales des transactions")
        m1, m2, m3, m4 = st.columns(4)
        composition = [
            (COLORS["normal"], counts[0]),
            (COLORS["suspect"], counts[1]),
            (COLORS["fraud"], counts[2]),
        ]
        render_kpi_card(
            m1,
            "Normales",
            f"{counts[0]:,}",
            context=f"{percentages[0]:.1f} % du total",
            variant="normal",
            share_pct=percentages[0],
        )
        render_kpi_card(
            m2,
            "Suspectes",
            f"{counts[1]:,}",
            context=f"{percentages[1]:.2f} % du total",
            variant="suspect",
            share_pct=percentages[1],
        )
        render_kpi_card(
            m3,
            "Fraudes",
            f"{counts[2]:,}",
            context=f"{percentages[2]:.2f} % du total",
            variant="fraud",
            share_pct=percentages[2],
        )
        render_kpi_card(
            m4,
            "Total analyse",
            f"{total:,}",
            context="Volume cumule en temps reel",
            variant="total",
            composition=composition,
        )

        section_title("Representation graphique des transactions")
        chart_left, chart_right = st.columns(2, gap="large")

        with chart_left:
            chart_title(
                "Repartition des transactions",
                "Parts normales, suspectes et fraudes",
                accent=COLORS["normal"],
            )
            distribution_fig = build_distribution_chart(counts)
            if distribution_fig:
                st.plotly_chart(
                    distribution_fig,
                    use_container_width=True,
                    config=PLOTLY_CHART_CONFIG,
                    key=chart_key("overview_distribution"),
                )
            else:
                st.caption("Aucune transaction analysee pour le moment.")

        with chart_right:
            chart_title(
                "Distribution des scores a risque",
                "Transactions suspectes et fraudes par intervalle de score",
                accent=COLORS["suspect"],
            )
            scores_fraudes = fetch_scores(db["fraudes"])
            scores_suspectes = fetch_scores(db["suspectes"])
            score_fig = build_score_chart(scores_fraudes, scores_suspectes)
            if score_fig:
                st.plotly_chart(
                    score_fig,
                    use_container_width=True,
                    config=PLOTLY_CHART_CONFIG,
                    key=chart_key("overview_score"),
                )
            else:
                st.caption("Les scores apparaitront apres classification des transactions.")

        st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)
        st.caption(f"Derniere mise a jour : {now_morocco_str()}")

    if not auto_refresh:
        break
    time.sleep(REFRESH_SECONDS)
    placeholder.empty()