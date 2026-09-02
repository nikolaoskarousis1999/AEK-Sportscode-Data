import streamlit as st

from src.analysis.common import (
    load_selected_analysis,
)
from src.analysis.corner_kicks import (
    render_corner_kick_analysis,
)
from src.analysis.final_attempts import (
    render_final_attempt_analysis,
)
from src.analysis.free_kicks import (
    render_free_kick_analysis,
)
from src.analysis.throw_ins import (
    render_throw_in_analysis,
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

filters = render_sportscode_filters()

analysis = load_selected_analysis(
    match_id=filters["match"]["id"],
    event_family=filters["event_family"],
    phase=filters["phase"],
)


st.subheader(
    f"{filters['analysis_name']} "
    f"— {filters['phase'].title()}"
)


event_family = filters[
    "event_family"
]

phase = filters[
    "phase"
]


if event_family == "corner_kick":
    render_corner_kick_analysis(
        analysis=analysis,
        phase=phase,
    )

elif event_family == "free_kick":
    render_free_kick_analysis(
        analysis=analysis,
        phase=phase,
    )

elif event_family == "throw_in":
    render_throw_in_analysis(
        analysis=analysis,
    )

elif event_family == "final_attempt":
    render_final_attempt_analysis(
        analysis=analysis,
    )