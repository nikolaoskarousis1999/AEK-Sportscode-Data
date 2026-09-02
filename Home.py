import streamlit as st

from src.analysis.sportscode_analysis import (
    load_selected_analysis,
)

from src.filters.sportscode_filters import (
    render_sportscode_filters,
)

from src.ui.header import (
    render_header,
)


st.set_page_config(
    page_title="AEK Sportscode Data",
    layout="wide",
)


render_header()


filters = (
    render_sportscode_filters()
)


analysis = (
    load_selected_analysis(
        match_id=filters[
            "match"
        ]["id"],
        event_family=filters[
            "event_family"
        ],
        phase=filters[
            "phase"
        ],
    )
)


st.subheader(
    (
        f"{filters['analysis_name']} "
        f"— "
        f"{filters['phase'].title()}"
    )
)


st.metric(
    "Events",
    analysis[
        "event_count"
    ],
)