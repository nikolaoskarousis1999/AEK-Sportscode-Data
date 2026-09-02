import streamlit as st

from src.data.data_loader import (
    load_competitions,
    load_matches,
)


ANALYSIS_TYPES = {
    "Corner Kicks":
        "corner_kick",

    "Free Kicks":
        "free_kick",

    "Throw Ins":
        "throw_in",

    "Final Attempts":
        "final_attempt",
}


def format_match(
    match: dict,
) -> str:
    opponent = match[
        "opponent"
    ]

    venue = match[
        "venue"
    ]

    if venue == "HOME":
        return (
            f"AEK - {opponent}"
        )

    if venue == "AWAY":
        return (
            f"{opponent} - AEK"
        )

    return opponent


def render_sportscode_filters() -> dict:
    with st.sidebar:
        st.header(
            "Filters"
        )

        competitions = (
            load_competitions()
        )

        if not competitions:
            st.warning(
                "No competitions found."
            )
            st.stop()

        competition_options = {
            competition["name"]:
                competition
            for competition
            in competitions
        }

        competition_name = (
            st.selectbox(
                "Competition",
                list(
                    competition_options
                    .keys()
                ),
            )
        )

        competition = (
            competition_options[
                competition_name
            ]
        )

        matches = load_matches(
            competition["id"]
        )

        if not matches:
            st.info(
                "No matches found."
            )
            st.stop()

        match_options = {
            format_match(match):
                match
            for match in matches
        }

        match_name = (
            st.selectbox(
                "Match",
                list(
                    match_options
                    .keys()
                ),
            )
        )

        match = (
            match_options[
                match_name
            ]
        )

        analysis_name = (
            st.selectbox(
                "Analysis",
                list(
                    ANALYSIS_TYPES
                    .keys()
                ),
            )
        )

        event_family = (
            ANALYSIS_TYPES[
                analysis_name
            ]
        )

        if (
            event_family
            == "throw_in"
        ):
            phase = "offensive"

            st.caption(
                "Phase: Offensive"
            )

        else:
            phase_label = (
                st.radio(
                    "Phase",
                    [
                        "Offensive",
                        "Defensive",
                    ],
                    horizontal=True,
                )
            )

            phase = (
                phase_label.lower()
            )

    return {
        "competition":
            competition,

        "match":
            match,

        "analysis_name":
            analysis_name,

        "event_family":
            event_family,

        "phase":
            phase,
    }