import time

import streamlit as st

from common import (
    COLORS,
    PLOTLY_CHART_CONFIG,
    build_fraud_global_stats,
    build_top_fraud_chart,
    chart_key,
    chart_title,
    connect_or_stop,
    now_morocco_str,
    render_kpi_card,
    section_title,
    FRAUD_SCATTER_LIMIT,
    REFRESH_SECONDS,
)

st.title("Fraudes")
st.caption("Analyse detaillee des transactions frauduleuses")

db = connect_or_stop()
placeholder = st.empty()
auto_refresh = st.session_state.get("auto_refresh", True)

while True:
    with placeholder.container():
        fraud_query = (
            db["fraudes"]
            .find({}, {"Amount": 1, "score": 1})
            .sort("_id", -1)
        )
        if FRAUD_SCATTER_LIMIT is not None:
            fraud_query = fraud_query.limit(FRAUD_SCATTER_LIMIT)
        fraud_records = list(fraud_query)

        section_title("Statistiques globales des fraudes")
        global_stats = build_fraud_global_stats(fraud_records)

        if global_stats:
            total_fraudes = global_stats["n_total"]
            pct_avec_montant = (
                global_stats["n_nonzero"] / total_fraudes * 100 if total_fraudes else 0
            )
            pct_zero = (
                global_stats["n_zero"] / total_fraudes * 100 if total_fraudes else 0
            )

            g1, g2, g3, g4 = st.columns(4)
            render_kpi_card(
                g1,
                "Fraudes au total",
                f"{global_stats['n_total']:,}",
                context="Transactions classees fraude",
                variant="fraud",
            )
            render_kpi_card(
                g2,
                "Avec montant",
                f"{global_stats['n_nonzero']:,}",
                context=f"{pct_avec_montant:.2f} % du total",
                variant="suspect",
                share_pct=pct_avec_montant,
            )
            render_kpi_card(
                g3,
                "A 0 €",
                f"{global_stats['n_zero']:,}",
                context=f"{pct_zero:.2f} % du total",
                variant="neutral",
                share_pct=pct_zero,
            )
            render_kpi_card(
                g4,
                "Montant total",
                f"{global_stats['total_amount']:,.2f} €",
                context="Somme des montants absolus",
                variant="amount",
            )
        else:
            st.caption("Aucune fraude detectee pour l'instant.")

        section_title("Analyse des montants")
        scatter_fig, top15_stats = build_top_fraud_chart(fraud_records)

        if top15_stats and top15_stats["count"] > 0:
            chart_title(
                "Top 15 des fraudes par montant",
                "Classement des transactions frauduleuses les plus couteuses",
                accent=COLORS["fraud"],
            )
            if scatter_fig:
                st.plotly_chart(
                    scatter_fig,
                    use_container_width=True,
                    config=PLOTLY_CHART_CONFIG,
                    key=chart_key("fraudes_top15"),
                )

            t1, t2 = st.columns(2)
            render_kpi_card(
                t1,
                "Fraudes affichees",
                f"{top15_stats['count']:,}",
                context="Classement par montant decroissant",
                variant="neutral",
            )
            render_kpi_card(
                t2,
                "Montant total du Top 15",
                f"{top15_stats['total_amount']:,.2f} €",
                context="Somme des 15 montants les plus eleves",
                variant="amount",
            )
        else:
            st.caption("Aucune fraude avec montant disponible pour le Top 15.")

        st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)
        st.caption(f"Derniere mise a jour : {now_morocco_str()}")

    if not auto_refresh:
        break
    time.sleep(REFRESH_SECONDS)
    placeholder.empty()
