import streamlit as st

from common import inject_global_style, now_morocco_str

st.set_page_config(
    page_title="Detection de fraude",
    layout="wide",
)

inject_global_style()

pg = st.navigation(
    [
        st.Page(
            "pages/overview.py",
            title="Vue d'ensemble",
            icon=":material/dashboard:",
            default=True,
        ),
        st.Page(
            "pages/fraudes.py",
            title="Fraudes",
            icon=":material/warning:",
        ),
        st.Page(
            "pages/details.py",
            title="Detail des transactions",
            icon=":material/list_alt:",
        ),
    ]
)

pg.run()

with st.sidebar:
    st.markdown(
        """
        <div class="sidebar-brand">
            <span class="sidebar-brand-mark">F</span>
            <span class="sidebar-brand-text">FraudWatch</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption("Kafka · Spark Streaming · MongoDB · XGBoost")

    st.divider()
    auto_refresh = st.toggle("Actualisation auto", value=True, key="auto_refresh")
    st.caption("Rafraichissement toutes les 3 s")

    st.divider()
    st.caption("Suspect ≥ 0.30 · Fraude ≥ 0.70")

    st.divider()
    st.caption(now_morocco_str())