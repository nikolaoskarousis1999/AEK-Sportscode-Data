from pathlib import Path

import streamlit as st


BASE_DIR = Path(
    __file__
).resolve().parents[2]

LOGO_PATH = (
    BASE_DIR
    / "images"
    / "aek-logo.png"
)


def render_header():
    logo_col, text_col = st.columns(
        [1.4, 4.6],
        vertical_alignment="center",
    )

    with logo_col:
        if LOGO_PATH.exists():
            st.image(
                str(LOGO_PATH),
                width=230,
            )

    with text_col:
        st.title(
            "AEK Sportscode Data"
        )

        st.subheader(
            "Match analysis database for AEK's technical staff"
        )

        st.write(
            "Explore match-level Sportscode data across "
            "Super League, Greek Cup, and Champions League."
        )