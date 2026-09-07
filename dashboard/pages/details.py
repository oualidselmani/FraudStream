import time

import streamlit as st

from common import (
    connect_or_stop,
    now_morocco_str,
    render_navbar,
    render_table,
    section_title,
    TABLE_LIMIT,
    REFRESH_SECONDS,
)

render_navbar("Detail des transactions", "Dernieres transactions signalees")

db = connect_or_stop()
placeholder = st.empty()
auto_refresh = st.session_state.get("auto_refresh", True)

while True:
    with placeholder.container():
        section_title("Transactions a risque")

        table_left, table_right = st.columns(2, gap="large")
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

        st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)
        st.caption(f"Derniere mise a jour : {now_morocco_str()}")

    if not auto_refresh:
        break
    time.sleep(REFRESH_SECONDS)
    placeholder.empty()