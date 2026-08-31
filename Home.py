import streamlit as st

from src.data.data_loader import load_competitions


st.set_page_config(
    page_title="AEK Sportscode Data",
    page_icon="⚽",
    layout="wide",
)


# ============================================================
# HEADER
# ============================================================

logo_col, text_col = st.columns(
    [1, 3],
    vertical_alignment="center",
)

with logo_col:
    st.image(
        "images/aek-logo.png",
        width=260,
    )

with text_col:
    st.title(
        "AEK Sportscode Data"
    )

    st.subheader(
        "Match analysis database for AEK's technical staff"
    )

    st.write(
        """
        Explore match-level Sportscode data across
        Super League, Greek Cup, and Champions League.
        """
    )


st.divider()


# ============================================================
# FILTERS
# ============================================================

competitions = load_competitions()

competition_names = [
    competition["name"]
    for competition in competitions
]


selected_competition = st.selectbox(
    "Competition",
    options=competition_names,
    index=None,
    placeholder="Select competition",
)


if selected_competition:
    st.write(
        "Selected competition:",
        selected_competition,
    )