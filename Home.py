import streamlit as st

from src.analysis.common import (
    load_analysis_scope,
)

from src.analysis.corner_kicks import (
    render_corner_kick_analysis,
)

from src.analysis.free_kicks import (
    render_free_kick_analysis,
)

from src.analysis.throw_ins import (
    render_throw_in_analysis,
)

from src.analysis import final_attempts

from src.data.data_loader import (
    load_competitions,
    load_matches,
    load_matches_all,
)

from src.filters.sportscode_filters import (
    filter_records,
    get_filter_options,
)

from src.ui.header import (
    render_header,
)

from src.reports.report_context import (
    build_report_context,
)

from src.reports.report_state import (
    clear_all_reports,
)


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="AEK Sportscode Data",
    layout="wide",
)


# ============================================================
# HEADER
# ============================================================

render_header()


# ============================================================
# CONSTANTS
# ============================================================

ANALYSIS_TYPES = {
    "Corner Kicks": "corner_kick",
    "Free Kicks": "free_kick",
    "Throw Ins": "throw_in",
    "Final Attempts": "final_attempt",
}

ANALYSIS_SCOPES = [
    "Match Analysis",
    "Competition Analysis",
    "All Matches Analysis",
]

FINAL_ATTEMPT_TIME_PERIODS = [
    "1-15",
    "16-30",
    "31-45+",
    "46-60",
    "61-75",
    "76-90+",
]


# ============================================================
# HELPERS
# ============================================================

def format_match(
    match: dict,
) -> str:
    venue = str(
        match.get(
            "venue",
            "",
        )
    ).upper()

    opponent = (
        match.get(
            "opponent"
        )
        or "Unknown Opponent"
    )

    if venue == "HOME":
        match_name = (
            f"AEK - {opponent}"
        )

    elif venue == "AWAY":
        match_name = (
            f"{opponent} - AEK"
        )

    else:
        match_name = opponent

    match_date = match.get(
        "match_date"
    )

    if match_date:
        return (
            f"{match_name} | "
            f"{match_date}"
        )

    return match_name


def sidebar_single_filter(
    label: str,
    records: list[dict],
    record_key: str,
    widget_key: str,
):
    options = get_filter_options(
        records,
        record_key,
    )

    selected = (
        st.sidebar.selectbox(
            label,
            [
                "All",
                *options,
            ],
            key=widget_key,
        )
    )

    if selected == "All":
        return None

    return selected


def sidebar_multi_filter(
    label: str,
    records: list[dict],
    record_key: str,
    widget_key: str,
):
    options = get_filter_options(
        records,
        record_key,
    )

    return (
        st.sidebar.multiselect(
            label,
            options,
            key=widget_key,
        )
    )


def render_final_attempt_module(
    analysis: dict,
    phase: str,
    analysis_scope: str | None = None,
    report_context: dict | None = None,
):
    if hasattr(
        final_attempts,
        "render_final_attempt_analysis",
    ):
        renderer = (
            final_attempts
            .render_final_attempt_analysis
        )

    elif hasattr(
        final_attempts,
        "render_final_attempts_analysis",
    ):
        renderer = (
            final_attempts
            .render_final_attempts_analysis
        )

    else:
        st.error(
            "No supported Final Attempts renderer "
            "was found in src/analysis/final_attempts.py."
        )
        return

    try:
        renderer(
            analysis,
            phase,
            analysis_scope,
            report_context=report_context,
        )

    except TypeError:
        renderer(
            analysis
        )


# ============================================================
# SIDEBAR - ANALYSIS SCOPE
# ============================================================

selected_scope = (
    st.sidebar.selectbox(
        "Analysis Scope",
        ANALYSIS_SCOPES,
        key="analysis_scope",
    )
)


# ============================================================
# SIDEBAR - COMPETITION
# ============================================================

selected_competition_id = None
selected_match_id = None
selected_match_ids = None
selected_competition_name = None
selected_match_name = None
selected_match_names = []


if selected_scope == "All Matches Analysis":
    all_matches = (
        load_matches_all()
    )

    if not all_matches:
        st.warning(
            "No matches found."
        )
        st.stop()

    all_match_options = {
        format_match(match):
            match["id"]
        for match
        in all_matches
        if match.get(
            "id"
        ) is not None
    }

    all_matches_label = "ALL MATCHES"

    # Keep ALL MATCHES mutually exclusive with specific matches.
    #
    # Behaviour:
    # - default = ALL MATCHES
    # - selecting a specific match removes ALL MATCHES
    # - selecting ALL MATCHES after specific matches clears them
    if "all_matches_selected" not in st.session_state:
        st.session_state[
            "all_matches_selected"
        ] = [
            all_matches_label
        ]

    if "_all_matches_previous" not in st.session_state:
        st.session_state[
            "_all_matches_previous"
        ] = list(
            st.session_state[
                "all_matches_selected"
            ]
        )

    def sync_all_matches_selection():
        current = list(
            st.session_state.get(
                "all_matches_selected",
                [],
            )
        )

        previous = list(
            st.session_state.get(
                "_all_matches_previous",
                [],
            )
        )

        if (
            all_matches_label in current
            and len(current) > 1
        ):
            # If ALL MATCHES was newly selected,
            # clear every specific match.
            if (
                all_matches_label
                not in previous
            ):
                current = [
                    all_matches_label
                ]

            # If a specific match was newly selected while
            # ALL MATCHES was active, remove ALL MATCHES.
            else:
                current = [
                    match_name
                    for match_name in current
                    if match_name
                    != all_matches_label
                ]

        st.session_state[
            "all_matches_selected"
        ] = current

        st.session_state[
            "_all_matches_previous"
        ] = list(
            current
        )

    selected_match_names = (
        st.sidebar.multiselect(
            "Select Matches",
            [
                all_matches_label,
                *list(
                    all_match_options.keys()
                ),
            ],
            key="all_matches_selected",
            on_change=sync_all_matches_selection,
        )
    )

    # ALL MATCHES keeps the original All Matches Analysis behaviour.
    if selected_match_names == [
        all_matches_label
    ]:
        selected_match_ids = None

    # If ALL MATCHES is removed and no specific match is selected,
    # analyse nothing. Do not fall back to the previous/all-matches data.
    elif not selected_match_names:
        selected_match_ids = []

    else:
        # Any combination of specific matches is allowed.
        selected_match_ids = [
            all_match_options[
                match_name
            ]
            for match_name
            in selected_match_names
            if match_name
            in all_match_options
        ]


if selected_scope in [
    "Match Analysis",
    "Competition Analysis",
]:
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
            competition["id"]
        for competition
        in competitions
    }

    selected_competition_name = (
        st.sidebar.selectbox(
            "Competition",
            list(
                competition_options.keys()
            ),
            key="competition",
        )
    )

    selected_competition_id = (
        competition_options[
            selected_competition_name
        ]
    )


# ============================================================
# SIDEBAR - MATCH
# ============================================================

if selected_scope == "Match Analysis":
    matches = load_matches(
        selected_competition_id
    )

    if not matches:
        st.info(
            "No matches found for this competition."
        )
        st.stop()

    match_options = {
        format_match(match):
            match["id"]
        for match
        in matches
    }

    selected_match_name = (
        st.sidebar.selectbox(
            "Match",
            list(
                match_options.keys()
            ),
            key="match",
        )
    )

    selected_match_id = (
        match_options[
            selected_match_name
        ]
    )


if (
    selected_scope == "All Matches Analysis"
    and selected_match_ids == []
):
    st.stop()


# ============================================================
# SIDEBAR - ANALYSIS TYPE
# ============================================================

selected_analysis_name = (
    st.sidebar.selectbox(
        "Analysis",
        list(
            ANALYSIS_TYPES.keys()
        ),
        key="analysis_type",
    )
)

selected_event_family = (
    ANALYSIS_TYPES[
        selected_analysis_name
    ]
)


# ============================================================
# REPORT RESET WHEN ANALYSIS CATEGORY CHANGES
# ============================================================

previous_report_family = (
    st.session_state.get(
        "_previous_report_event_family"
    )
)

if previous_report_family is None:
    st.session_state[
        "_previous_report_event_family"
    ] = selected_event_family

elif (
    previous_report_family
    != selected_event_family
):
    # Reports are intentionally temporary per analysis category.
    # Switching Corner Kicks -> Free Kicks, Throw-Ins, etc.
    # clears every report basket so returning to the old category
    # always starts clean.
    clear_all_reports()

    st.session_state[
        "_previous_report_event_family"
    ] = selected_event_family


# ============================================================
# SIDEBAR - PHASE
# ============================================================

if selected_event_family == "throw_in":
    selected_phase = "offensive"

    st.sidebar.caption(
        "Phase: Offensive"
    )

else:
    phase_name = (
        st.sidebar.radio(
            "Phase",
            [
                "Offensive",
                "Defensive",
            ],
            horizontal=True,
            key="phase",
        )
    )

    selected_phase = (
        phase_name.lower()
    )


# ============================================================
# REPORT RESET WHEN PHASE CHANGES
# ============================================================

previous_report_phase = (
    st.session_state.get(
        "_previous_report_phase"
    )
)

if previous_report_phase is None:
    st.session_state[
        "_previous_report_phase"
    ] = selected_phase

elif (
    previous_report_phase
    != selected_phase
):
    clear_all_reports()

    st.session_state[
        "_previous_report_phase"
    ] = selected_phase


# ============================================================
# LOAD BASE ANALYSIS
# ============================================================

analysis = (
    load_analysis_scope(
        scope=selected_scope,
        event_family=(
            selected_event_family
        ),
        phase=selected_phase,
        match_id=(
            selected_match_id
        ),
        competition_id=(
            selected_competition_id
        ),
        match_ids=(
            selected_match_ids
        ),
    )
)

base_records = analysis[
    "records"
]


# ============================================================
# NO BASE EVENTS
# ============================================================

if not base_records:
    st.info(
        "No events found for the selected "
        "scope, analysis and phase."
    )
    st.stop()


# ============================================================
# SIDEBAR - FILTERS
# ============================================================

st.sidebar.divider()

st.sidebar.subheader(
    "Filters"
)

active_filters = {}


# ============================================================
# CORNER KICK FILTERS
# ============================================================

if (
    selected_event_family
    == "corner_kick"
):
    active_filters[
        "half"
    ] = sidebar_single_filter(
        "Half",
        base_records,
        "half",
        "corner_half",
    )

    active_filters[
        "side"
    ] = sidebar_multi_filter(
        "Side",
        base_records,
        "side",
        "corner_side",
    )

    if selected_phase == "offensive":
        active_filters[
            "taker"
        ] = sidebar_multi_filter(
            "Taker",
            base_records,
            "taker",
            "corner_taker",
        )

    active_filters[
        "delivery_type"
    ] = sidebar_multi_filter(
        "Delivery Type",
        base_records,
        "delivery_type",
        "corner_delivery_type",
    )

    active_filters[
        "delivery_zone"
    ] = sidebar_multi_filter(
        "Delivery Zone",
        base_records,
        "delivery_zone",
        "corner_delivery_zone",
    )

    active_filters[
        "first_contact"
    ] = sidebar_multi_filter(
        "First Contact",
        base_records,
        "first_contact",
        "corner_first_contact",
    )

    active_filters[
        "outcome"
    ] = sidebar_multi_filter(
        "Outcome",
        base_records,
        "outcome",
        "corner_outcome",
    )

    if selected_phase == "offensive":
        active_filters[
            "opponent_organization"
        ] = sidebar_multi_filter(
            "Opponent Organization",
            base_records,
            "opponent_organization",
            "corner_opponent_organization",
        )

    else:
        active_filters[
            "opponent_players"
        ] = sidebar_multi_filter(
            "Opponent Players in Box",
            base_records,
            "opponent_players",
            "corner_opponent_players",
        )


# ============================================================
# FREE KICK FILTERS
# ============================================================

elif (
    selected_event_family
    == "free_kick"
):
    active_filters[
        "half"
    ] = sidebar_single_filter(
        "Half",
        base_records,
        "half",
        "free_kick_half",
    )

    active_filters[
        "side"
    ] = sidebar_multi_filter(
        "Side",
        base_records,
        "side",
        "free_kick_side",
    )

    if selected_phase == "offensive":
        active_filters[
            "taker"
        ] = sidebar_multi_filter(
            "Taker",
            base_records,
            "taker",
            "free_kick_taker",
        )

    active_filters[
        "delivery_type"
    ] = sidebar_multi_filter(
        "Delivery Type",
        base_records,
        "delivery_type",
        "free_kick_delivery_type",
    )

    active_filters[
        "drop_zone"
    ] = sidebar_multi_filter(
        "Drop Zone",
        base_records,
        "drop_zone",
        "free_kick_drop_zone",
    )

    active_filters[
        "first_contact"
    ] = sidebar_multi_filter(
        "First Contact",
        base_records,
        "first_contact",
        "free_kick_first_contact",
    )

    active_filters[
        "outcome"
    ] = sidebar_multi_filter(
        "Outcome",
        base_records,
        "outcome",
        "free_kick_outcome",
    )

    active_filters[
        "origin_zone"
    ] = sidebar_multi_filter(
        "Origin Zone",
        base_records,
        "origin_zone",
        "free_kick_origin_zone",
    )

    active_filters[
        "delivery_zone"
    ] = sidebar_multi_filter(
        "Delivery Zone",
        base_records,
        "delivery_zone",
        "free_kick_delivery_zone",
    )

    if selected_phase == "offensive":
        active_filters[
            "opponent_organization"
        ] = sidebar_multi_filter(
            "Opponent Organization",
            base_records,
            "opponent_organization",
            "free_kick_opponent_organization",
        )

    else:
        active_filters[
            "opponent_players"
        ] = sidebar_multi_filter(
            "Opponent Players in Box",
            base_records,
            "opponent_players",
            "free_kick_opponent_players",
        )


# ============================================================
# THROW-IN FILTERS
# ============================================================

elif (
    selected_event_family
    == "throw_in"
):
    active_filters[
        "half"
    ] = sidebar_single_filter(
        "Half",
        base_records,
        "half",
        "throw_in_half",
    )

    active_filters[
        "taker"
    ] = sidebar_single_filter(
        "Taker",
        base_records,
        "taker",
        "throw_in_taker",
    )

    active_filters[
        "throw_in_zone"
    ] = sidebar_multi_filter(
        "Zone",
        base_records,
        "throw_in_zone",
        "throw_in_zone",
    )

    active_filters[
        "direction"
    ] = sidebar_multi_filter(
        "Direction",
        base_records,
        "direction",
        "throw_in_direction",
    )

    active_filters[
        "speed"
    ] = sidebar_multi_filter(
        "Speed",
        base_records,
        "speed",
        "throw_in_speed",
    )

    active_filters[
        "length"
    ] = sidebar_multi_filter(
        "Length",
        base_records,
        "length",
        "throw_in_length",
    )

    active_filters[
        "result"
    ] = sidebar_multi_filter(
        "Result",
        base_records,
        "result",
        "throw_in_result",
    )

    active_filters[
        "retention"
    ] = sidebar_multi_filter(
        "Retention",
        base_records,
        "retention",
        "throw_in_retention",
    )


# ============================================================
# FINAL ATTEMPT FILTERS
# ============================================================

elif (
    selected_event_family
    == "final_attempt"
):
    available_periods = (
        get_filter_options(
            base_records,
            "time_period",
        )
    )

    unexpected_periods = [
        period
        for period
        in available_periods
        if period
        not in FINAL_ATTEMPT_TIME_PERIODS
    ]

    active_filters[
        "time_period"
    ] = st.sidebar.multiselect(
        "Time Period",
        [
            *FINAL_ATTEMPT_TIME_PERIODS,
            *unexpected_periods,
        ],
        key="final_attempt_time_period",
    )

    active_filters[
        "outcome"
    ] = sidebar_multi_filter(
        "Outcome",
        base_records,
        "outcome",
        "final_attempt_outcome",
    )

    active_filters[
        "attack_type"
    ] = sidebar_multi_filter(
        "Attack Type",
        base_records,
        "attack_type",
        "final_attempt_attack_type",
    )

    active_filters[
        "organized_attack_type"
    ] = sidebar_multi_filter(
        "Org. Attack Type",
        base_records,
        "organized_attack_type",
        "final_attempt_org_attack_type",
    )

    active_filters[
        "block_context"
    ] = sidebar_multi_filter(
        "Block / Press Context",
        base_records,
        "block_context",
        "final_attempt_block_context",
    )

    active_filters[
        "passes"
    ] = sidebar_multi_filter(
        "Passes",
        base_records,
        "passes",
        "final_attempt_passes",
    )

    active_filters[
        "pass_type"
    ] = sidebar_multi_filter(
        "Assist / Pass Type",
        base_records,
        "pass_type",
        "final_attempt_pass_type",
    )

    active_filters[
        "touches"
    ] = sidebar_multi_filter(
        "Touches",
        base_records,
        "touches",
        "final_attempt_touches",
    )

    with st.sidebar.expander(
        "Set Play Filters"
    ):
        active_filters[
            "set_play_type"
        ] = st.multiselect(
            "Set Play Type",
            get_filter_options(
                base_records,
                "set_play_type",
            ),
            key="final_attempt_set_play_type",
        )

        active_filters[
            "corner_kick_type"
        ] = st.multiselect(
            "Corner Type",
            get_filter_options(
                base_records,
                "corner_kick_type",
            ),
            key="final_attempt_corner_type",
        )

        active_filters[
            "free_kick_type"
        ] = st.multiselect(
            "Free Kick Type",
            get_filter_options(
                base_records,
                "free_kick_type",
            ),
            key="final_attempt_free_kick_type",
        )

    with st.sidebar.expander(
        "Zone Filters"
    ):
        active_filters[
            "recovery_zone"
        ] = st.multiselect(
            "Recovery Zone",
            get_filter_options(
                base_records,
                "recovery_zone",
            ),
            key="final_attempt_recovery_zone",
        )

        active_filters[
            "assist_zone"
        ] = st.multiselect(
            "Assist Zone",
            get_filter_options(
                base_records,
                "assist_zone",
            ),
            key="final_attempt_assist_zone",
        )

        active_filters[
            "final_attempt_zone"
        ] = st.multiselect(
            "Final Attempt Zone",
            get_filter_options(
                base_records,
                "final_attempt_zone",
            ),
            key="final_attempt_final_zone",
        )

    with st.sidebar.expander(
        "Player Filters"
    ):
        active_filters[
            "shooter"
        ] = st.multiselect(
            "Final Attempt Player",
            get_filter_options(
                base_records,
                "shooter",
            ),
            key="final_attempt_shooter",
        )

        active_filters[
            "assist"
        ] = st.multiselect(
            "Assist Player",
            get_filter_options(
                base_records,
                "assist",
            ),
            key="final_attempt_assist",
        )

        active_filters[
            "second_assist"
        ] = st.multiselect(
            "Pre-Assist / 2nd Assist",
            get_filter_options(
                base_records,
                "second_assist",
            ),
            key="final_attempt_second_assist",
        )

        active_filters[
            "recovery_player"
        ] = st.multiselect(
            "Recovery Player",
            get_filter_options(
                base_records,
                "recovery_player",
            ),
            key="final_attempt_recovery_player",
        )


# ============================================================
# APPLY FILTERS
# ============================================================

filtered_records = (
    filter_records(
        base_records,
        active_filters,
    )
)

filtered_analysis = {
    **analysis,
    "records":
        filtered_records,
}

# ============================================================
# REPORT RESET WHEN ANALYSIS CONTEXT / FILTERS CHANGE
# ============================================================

current_report_context_signature = (
    selected_scope,
    selected_event_family,
    selected_phase,
    selected_competition_id,
    selected_match_id,
    tuple(
        sorted(
            selected_match_ids
        )
    )
    if isinstance(
        selected_match_ids,
        list,
    )
    else selected_match_ids,
    tuple(
        sorted(
            (
                key,
                tuple(value)
                if isinstance(
                    value,
                    list,
                )
                else value,
            )
            for key, value
            in active_filters.items()
        )
    ),
)

previous_report_context_signature = (
    st.session_state.get(
        "_previous_report_context_signature"
    )
)

if previous_report_context_signature is None:
    st.session_state[
        "_previous_report_context_signature"
    ] = current_report_context_signature

elif (
    previous_report_context_signature
    != current_report_context_signature
):
    clear_all_reports()

    st.session_state[
        "_previous_report_context_signature"
    ] = current_report_context_signature


report_context = build_report_context(
    event_family=selected_event_family,
    analysis_name=selected_analysis_name,
    scope=selected_scope,
    phase=selected_phase,
    competition=selected_competition_name,
    match=selected_match_name,
    matches=selected_match_names,
    filters=active_filters,
)


# ============================================================
# SIDEBAR SUMMARY
# ============================================================

st.sidebar.divider()

st.sidebar.caption(
    f"Showing "
    f"{len(filtered_records)} "
    f"of "
    f"{len(base_records)} "
    f"events"
)


# ============================================================
# EMPTY FILTER RESULT
# ============================================================

if not filtered_records:
    st.warning(
        "No events match the selected filters."
    )
    st.stop()


# ============================================================
# RENDER ANALYSIS
# ============================================================

if (
    selected_event_family
    == "corner_kick"
):
    render_corner_kick_analysis(
        filtered_analysis,
        selected_phase,
        selected_scope,
        report_context=report_context,
    )

elif (
    selected_event_family
    == "free_kick"
):
    render_free_kick_analysis(
        filtered_analysis,
        selected_phase,
        selected_scope,
        report_context=report_context,
    )

elif (
    selected_event_family
    == "throw_in"
):
    render_throw_in_analysis(
        filtered_analysis,
        report_context=report_context,
    )

elif (
    selected_event_family
    == "final_attempt"
):
    render_final_attempt_module(
        filtered_analysis,
        selected_phase,
        selected_scope,
        report_context=report_context,
    )