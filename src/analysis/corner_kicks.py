from collections import Counter

import pandas as pd
import plotly.express as px
import streamlit as st

from src.reports.report_items import (
    create_image_report_item,
    create_kpi_report_item,
    create_plotly_report_item,
    create_table_report_item,
)

from src.reports.report_ui import (
    render_add_to_report_button,
    render_create_report_button,
)


# ============================================================
# CONSTANTS
# ============================================================

FC_WON = "1ST CONTACT WON"
FC_LOST = "1ST CONTACT LOST"

SHOT = "SHOT"
GOAL = "GOAL"
SHOT_CONCEDED = "SHOT CONCEDED"
GOAL_CONCEDED = "GOAL CONCEDED"

SECOND_PHASE_ATTACK = "2ND PHASE ATTACK"
SECOND_PHASE = "2ND PHASE"

COUNTER_ALLOWED = "COUNTER ALLOWED"
COUNTER_LAUNCHED = "COUNTER LAUNCHED"

CLEARANCE = "CLEARANCE"


# ============================================================
# CHART COLOURS — GRAYSCALE
# ============================================================

CORNER_GRAYSCALE = {
    # Dark -> light hierarchy for the analytical series.
    "Attempt": "#555555",
    "Attempt Conceded": "#555555",
    "2nd Phase": "#8F8F8F",
    "FC Won": "#C8C8C8",
    "Counter Allowed": "#E8E8E8",
    "Counter Launched": "#E8E8E8",
    "Goal": "#F5F5F5",
    "Goal Conceded": "#F5F5F5",
}

# Used when a chart has categorical bars/points rather than named metrics.
# Ordered from dark to light so every Plotly chart stays grayscale.
CORNER_GRAYSCALE_SEQUENCE = [
    "#4A4A4A",
    "#666666",
    "#828282",
    "#9E9E9E",
    "#BABABA",
    "#D6D6D6",
    "#EEEEEE",
]

# Single neutral gray for categorical charts requested to use one color.
CORNER_SINGLE_GRAY = "#8F8F8F"


# ============================================================
# CORNER ZONE ALIASES
# ============================================================

ZONE_ALIAS_TO_SLOT = {
    "NEAR ZONE": "near_zone",

    "SIDE ZONE/NEAR": "side_zone_near",
    "SIDE ZONE / NEAR": "side_zone_near",
    "SIDE ZONE/ NEAR": "side_zone_near",

    "NEAR POST": "near_post",

    "CENTRAL": "central",

    "FAR POST": "far_post",

    "SIDE ZONE/FAR": "side_zone_far",
    "SIDE ZONE / FAR": "side_zone_far",
    "SIDE ZONE/ FAR": "side_zone_far",

    "FAR ZONE": "far_zone",

    "BACK ZONE": "back_zone",

    "EDGE OF BOX": "edge_of_box",
}


ZONE_DISPLAY_NAMES = {
    "near_zone": "Near Zone",
    "side_zone_near": "Side Zone / Near",
    "near_post": "Near Post",
    "central": "Central",
    "far_post": "Far Post",
    "side_zone_far": "Side Zone / Far",
    "far_zone": "Far Zone",
    "back_zone": "Back Zone",
    "edge_of_box": "Edge of Box",
}


# ============================================================
# BASIC HELPERS
# ============================================================

def _as_list(value):
    if value is None:
        return []

    if isinstance(value, list):
        return value

    return [value]


def _normalize(value):
    if value is None:
        return ""

    return " ".join(
        str(value)
        .strip()
        .upper()
        .split()
    )


def event_has_value(
    record: dict,
    key: str,
    target: str,
) -> bool:
    target_normalized = _normalize(
        target
    )

    return any(
        _normalize(value)
        == target_normalized
        for value in _as_list(
            record.get(key)
        )
    )


def count_events_with_value(
    records: list[dict],
    key: str,
    target: str,
) -> int:
    return sum(
        1
        for record in records
        if event_has_value(
            record,
            key,
            target,
        )
    )


def event_has_any_value(
    record: dict,
    key: str,
    targets: list[str],
) -> bool:
    return any(
        event_has_value(
            record,
            key,
            target,
        )
        for target in targets
    )


def count_events_with_any_value(
    records: list[dict],
    key: str,
    targets: list[str],
) -> int:
    return sum(
        1
        for record in records
        if event_has_any_value(
            record,
            key,
            targets,
        )
    )


def calculate_rate(
    numerator: int,
    denominator: int,
) -> float:
    if denominator == 0:
        return 0.0

    return (
        numerator
        / denominator
        * 100
    )


def format_rate(
    numerator: int,
    denominator: int,
) -> str:
    if denominator == 0:
        return "—"

    return (
        f"{calculate_rate(numerator, denominator):.0f}% "
        f"({numerator}/{denominator})"
    )


def get_record_values(
    record: dict,
    key: str,
    include_unknown: bool = False,
) -> list[str]:
    values = []
    seen = set()

    for raw_value in _as_list(
        record.get(key)
    ):
        if raw_value is None:
            continue

        value = str(
            raw_value
        ).strip()

        if not value:
            continue

        normalized = _normalize(
            value
        )

        if normalized in seen:
            continue

        seen.add(
            normalized
        )

        values.append(
            value
        )

    if (
        not values
        and include_unknown
    ):
        return ["UNKNOWN"]

    return values


def category_counts(
    records: list[dict],
    key: str,
    include_unknown: bool = False,
) -> Counter:
    counts = Counter()

    for record in records:
        values = get_record_values(
            record,
            key,
            include_unknown,
        )

        for value in values:
            counts[value] += 1

    return counts


def records_with_category(
    records: list[dict],
    key: str,
    category: str,
) -> list[dict]:
    if category == "UNKNOWN":
        return [
            record
            for record in records
            if not get_record_values(
                record,
                key,
            )
        ]

    return [
        record
        for record in records
        if event_has_value(
            record,
            key,
            category,
        )
    ]


def most_common(
    records: list[dict],
    key: str,
    include_unknown: bool = False,
) -> tuple[str, int]:
    counts = category_counts(
        records,
        key,
        include_unknown,
    )

    if not counts:
        return "-", 0

    return counts.most_common(1)[0]


# ============================================================
# PHASE
# ============================================================

def resolve_phase(
    analysis: dict,
    phase: str | None,
) -> str:
    if phase:
        return str(
            phase
        ).lower()

    analysis_phase = analysis.get(
        "phase"
    )

    if analysis_phase:
        return str(
            analysis_phase
        ).lower()

    return "offensive"


# ============================================================
# CORNER METRICS
# ============================================================

def get_corner_metrics(
    records: list[dict],
    phase: str,
) -> dict:
    total = len(
        records
    )

    fc_won = count_events_with_value(
        records,
        "first_contact",
        FC_WON,
    )

    clearance = count_events_with_value(
        records,
        "outcome",
        CLEARANCE,
    )

    if phase == "defensive":
        attempt_labels = [
            SHOT_CONCEDED,
            GOAL_CONCEDED,
        ]
        goal_label = GOAL_CONCEDED
        second_phase_label = SECOND_PHASE
        counter_label = COUNTER_LAUNCHED

    else:
        # GOAL may be a terminal outcome without SHOT.
        # Therefore Attempt = SHOT OR GOAL.
        attempt_labels = [
            SHOT,
            GOAL,
        ]
        goal_label = GOAL
        second_phase_label = SECOND_PHASE_ATTACK
        counter_label = COUNTER_ALLOWED

    attempt = count_events_with_any_value(
        records,
        "outcome",
        attempt_labels,
    )

    goal = count_events_with_value(
        records,
        "outcome",
        goal_label,
    )

    second_phase = count_events_with_value(
        records,
        "outcome",
        second_phase_label,
    )

    counter = count_events_with_value(
        records,
        "outcome",
        counter_label,
    )

    second_phase_records = [
        record
        for record in records
        if event_has_value(
            record,
            "outcome",
            second_phase_label,
        )
    ]

    second_phase_attempt = (
        count_events_with_any_value(
            second_phase_records,
            "outcome",
            attempt_labels,
        )
    )

    return {
        "total":
            total,

        "fc_won":
            fc_won,

        "attempt":
            attempt,

        "goal":
            goal,

        "second_phase":
            second_phase,

        "counter":
            counter,

        "clearance":
            clearance,

        "second_phase_count":
            len(
                second_phase_records
            ),

        "second_phase_attempt":
            second_phase_attempt,
    }


# ============================================================
# KPIs
# ============================================================

def render_kpis(
    records: list[dict],
    phase: str,
    report_context: dict | None = None,
):
    metrics = get_corner_metrics(
        records,
        phase,
    )

    total = metrics[
        "total"
    ]

    (
        delivery_type,
        delivery_count,
    ) = most_common(
        records,
        "delivery_type",
    )

    st.markdown(
        "### KPIs Overview"
    )

    if phase == "defensive":
        (
            opponent_players,
            opponent_players_count,
        ) = most_common(
            records,
            "opponent_players",
            include_unknown=True,
        )

        rows = [
            [
                (
                    "Corners Faced",
                    str(total),
                    None,
                ),
                (
                    "First Contact Won",
                    format_rate(
                        metrics["fc_won"],
                        total,
                    ),
                    None,
                ),
                (
                    "Attempt Conceded",
                    format_rate(
                        metrics["attempt"],
                        total,
                    ),
                    "Attempt Conceded = SHOT CONCEDED or GOAL CONCEDED.",
                ),
                (
                    "Goal Conceded",
                    format_rate(
                        metrics["goal"],
                        total,
                    ),
                    None,
                ),
            ],
            [
                (
                    "Goal Conceded Conversion",
                    format_rate(
                        metrics["goal"],
                        metrics["attempt"],
                    ),
                    "GOAL CONCEDED / Attempt Conceded.",
                ),
                (
                    "2nd Phase",
                    format_rate(
                        metrics["second_phase"],
                        total,
                    ),
                    None,
                ),
                (
                    "Counter Launched",
                    format_rate(
                        metrics["counter"],
                        total,
                    ),
                    None,
                ),
                (
                    "Clearance",
                    format_rate(
                        metrics["clearance"],
                        total,
                    ),
                    None,
                ),
            ],
            [
                (
                    "Most Common Delivery Type",
                    delivery_type,
                    (
                        f"{delivery_count}/"
                        f"{total} corners"
                    ),
                ),
                (
                    "Most Common Opponent Players",
                    opponent_players,
                    (
                        f"{opponent_players_count}/"
                        f"{total} corners"
                    ),
                ),
            ],
        ]

    else:
        (
            taker,
            taker_count,
        ) = most_common(
            records,
            "taker",
            include_unknown=True,
        )

        rows = [
            [
                (
                    "Total Corners",
                    str(total),
                    None,
                ),
                (
                    "First Contact Won",
                    format_rate(
                        metrics["fc_won"],
                        total,
                    ),
                    None,
                ),
                (
                    "Attempt",
                    format_rate(
                        metrics["attempt"],
                        total,
                    ),
                    "Attempt = SHOT or GOAL.",
                ),
                (
                    "Goal",
                    format_rate(
                        metrics["goal"],
                        total,
                    ),
                    None,
                ),
            ],
            [
                (
                    "Goal Conversion",
                    format_rate(
                        metrics["goal"],
                        metrics["attempt"],
                    ),
                    "GOAL / Attempt.",
                ),
                (
                    "2nd Phase Attack",
                    format_rate(
                        metrics["second_phase"],
                        total,
                    ),
                    None,
                ),
                (
                    "Counter Allowed",
                    format_rate(
                        metrics["counter"],
                        total,
                    ),
                    None,
                ),
                (
                    "Most Common Delivery Type",
                    delivery_type,
                    (
                        f"{delivery_count}/"
                        f"{total} corners"
                    ),
                ),
            ],
            [
                (
                    "Most Common Taker",
                    taker,
                    (
                        f"{taker_count}/"
                        f"{total} corners"
                    ),
                ),
            ],
        ]

    for row in rows:
        columns = st.columns(
            len(row)
        )

        for column, (
            label,
            value,
            help_text,
        ) in zip(
            columns,
            row,
        ):
            with column:
                st.metric(
                    label,
                    value,
                    help=help_text,
                )

    if report_context is not None:
        kpi_items = []
        notes = []

        for row in rows:
            for (
                label,
                value,
                help_text,
            ) in row:
                kpi_items.append(
                    {
                        "label": label,
                        "value": value,
                    }
                )

                if help_text:
                    notes.append(
                        f"{label}: {help_text}"
                    )

        report_item = create_kpi_report_item(
            module="corner_kick",
            section_title="KPIs Overview",
            kpis=kpi_items,
            context=report_context,
        )

        render_add_to_report_button(
            report_item,
            key=(
                "report_corner_kpis_"
                f"{report_item['id']}"
            ),
        )


# ============================================================
# ZONE VISUALISATION
# ============================================================

def build_zone_slot_counts(
    records: list[dict],
    key: str,
) -> dict:
    counts = {
        slot: 0
        for slot
        in ZONE_DISPLAY_NAMES
    }

    for record in records:
        seen_slots = set()

        for value in get_record_values(
            record,
            key,
        ):
            slot = ZONE_ALIAS_TO_SLOT.get(
                _normalize(
                    value
                )
            )

            if (
                slot
                and slot not in seen_slots
            ):
                counts[
                    slot
                ] += 1

                seen_slots.add(
                    slot
                )

    return counts


def _zone_bg(
    count: int,
    max_count: int,
    palette: str,
) -> str:
    ratio = (
        0
        if max_count <= 0
        else count / max_count
    )

    if palette == "delivery":
        if count == 0:
            return (
                "rgba(0, 65, 72, 0.34)"
            )

        if ratio >= 0.75:
            return (
                "rgba(0, 112, 124, 0.72)"
            )

        if ratio >= 0.50:
            return (
                "rgba(0, 95, 107, 0.60)"
            )

        return (
            "rgba(0, 80, 92, 0.48)"
        )

    if count == 0:
        return (
            "rgba(78, 10, 31, 0.30)"
        )

    if ratio >= 0.75:
        return (
            "rgba(155, 16, 61, 0.74)"
        )

    if ratio >= 0.50:
        return (
            "rgba(130, 13, 51, 0.62)"
        )

    return (
        "rgba(107, 11, 43, 0.50)"
    )


def _zone_card(
    slot: str,
    count: int,
    max_count: int,
    palette: str,
) -> str:
    bg = _zone_bg(
        count,
        max_count,
        palette,
    )

    label = (
        ZONE_DISPLAY_NAMES[
            slot
        ].upper()
    )

    return f"""
    <div
        class="zone-card {slot}"
        style="background:{bg};"
    >
        <div class="zone-name">
            {label}
        </div>

        <div class="zone-count">
            {count}
        </div>
    </div>
    """


def _zone_panel(
    title: str,
    counts: dict,
    palette: str,
) -> str:
    max_count = max(
        counts.values(),
        default=0,
    )

    return f"""
    <div class="pitch-panel">

        <div class="pitch-title">
            {title}
        </div>

        <div class="pitch-bg">

            <div class="pitch-lines">
                <div class="penalty-box-line"></div>
                <div class="goal-box-line"></div>
                <div class="penalty-arc"></div>
                <div class="halfway-line"></div>
                <div class="mid-circle"></div>
                <div class="centre-dot"></div>
            </div>

            {_zone_card(
                "near_zone",
                counts["near_zone"],
                max_count,
                palette,
            )}

            {_zone_card(
                "side_zone_near",
                counts["side_zone_near"],
                max_count,
                palette,
            )}

            {_zone_card(
                "near_post",
                counts["near_post"],
                max_count,
                palette,
            )}

            {_zone_card(
                "central",
                counts["central"],
                max_count,
                palette,
            )}

            {_zone_card(
                "far_post",
                counts["far_post"],
                max_count,
                palette,
            )}

            {_zone_card(
                "side_zone_far",
                counts["side_zone_far"],
                max_count,
                palette,
            )}

            {_zone_card(
                "far_zone",
                counts["far_zone"],
                max_count,
                palette,
            )}

            {_zone_card(
                "back_zone",
                counts["back_zone"],
                max_count,
                palette,
            )}

            {_zone_card(
                "edge_of_box",
                counts["edge_of_box"],
                max_count,
                palette,
            )}

        </div>

    </div>
    """


def render_zone_visualisation(
    records: list[dict],
    phase: str,
    report_context: dict | None = None,
    show_delivery: bool = True,
    show_finishing: bool = True,
    show_heading: bool = True,
):
    if show_heading:
        st.markdown(
            "### Zone Visualisation"
        )

    delivery_counts = (
        build_zone_slot_counts(
            records,
            "delivery_zone",
        )
    )

    finishing_counts = (
        build_zone_slot_counts(
            records,
            "finishing_zone",
        )
    )

    total = len(
        records
    )

    delivery_mapped = sum(
        delivery_counts.values()
    )

    finishing_mapped = sum(
        finishing_counts.values()
    )

    panels = []
    captions = []

    if show_delivery:
        panels.append(
            _zone_panel(
                "Delivery Zones",
                delivery_counts,
                "delivery",
            )
        )
        captions.append(
            f"""
            <div>
                Delivery-zone labels available:
                <strong>{delivery_mapped}/{total}</strong>
            </div>
            """
        )

    if show_finishing:
        panels.append(
            _zone_panel(
                "Finishing Zones",
                finishing_counts,
                "finishing",
            )
        )
        captions.append(
            f"""
            <div>
                Finishing-zone labels available:
                <strong>{finishing_mapped}/{total}</strong>
            </div>
            """
        )

    grid_columns = max(1, len(panels))
    panels_html = "".join(panels)
    captions_html = "".join(captions)

    html = f"""
<!doctype html>
<html>
<head>

<meta charset="UTF-8">

<style>

* {{
    box-sizing: border-box;
}}

html,
body {{
    margin: 0;
    padding: 0;

    background:
        #0d1117;

    color:
        #ffffff;

    font-family:
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        sans-serif;
}}


.zone-shell {{
    width: 100%;
}}


.zone-grid {{
    display: grid;

    grid-template-columns:
        repeat({grid_columns}, 1fr);

    gap: 14px;
}}


.pitch-panel {{
    min-width: 0;
}}


.pitch-title {{
    height: 31px;

    display: flex;

    align-items: center;

    justify-content: center;

    color:
        #c7f000;

    font-size: 13px;

    font-weight: 800;

    letter-spacing:
        .3px;

    text-transform:
        uppercase;
}}


.pitch-bg {{
    position: relative;

    height: 390px;

    overflow: hidden;

    border:
        2px solid
        rgba(
            255,
            255,
            255,
            .90
        );

    background:
        repeating-linear-gradient(
            75deg,
            rgba(
                255,
                255,
                255,
                .035
            ) 0px,
            rgba(
                255,
                255,
                255,
                .035
            ) 5px,
            transparent 5px,
            transparent 25px
        ),
        linear-gradient(
            180deg,
            #14202a 0%,
            #101922 60%,
            #0d151c 60%,
            #0b1218 100%
        );
}}


/* =========================================================
   FIELD LINES
   ========================================================= */

.pitch-lines {{
    position: absolute;

    inset: 0;

    pointer-events:
        none;

    z-index: 10;
}}


.penalty-box-line {{
    position: absolute;

    top: 0;

    left: 20%;

    width: 60%;

    height: 30%;

    border-left:
        2px solid
        rgba(
            255,
            255,
            255,
            .92
        );

    border-right:
        2px solid
        rgba(
            255,
            255,
            255,
            .92
        );

    border-bottom:
        2px solid
        rgba(
            255,
            255,
            255,
            .92
        );
}}


.goal-box-line {{
    position: absolute;

    top: 0;

    /*
    Central zone is centred at 50%.

    Near Post:
        34% → 42%

    Central:
        42% → 58%

    Far Post:
        58% → 66%

    So the goal-area visual is centred
    on exactly the same 50% line.
    */

    left: 34%;

    width: 32%;

    height: 13%;

    border-left:
        2px solid
        rgba(
            255,
            255,
            255,
            .90
        );

    border-right:
        2px solid
        rgba(
            255,
            255,
            255,
            .90
        );

    border-bottom:
        2px solid
        rgba(
            255,
            255,
            255,
            .90
        );
}}


.penalty-arc {{
    position: absolute;

    /*
    Arc centred exactly at 50%.
    */

    top: 29%;

    left: 39%;

    width: 22%;

    height: 13%;

    border-bottom:
        2px solid
        rgba(
            255,
            255,
            255,
            .90
        );

    border-radius:
        0 0
        100px
        100px;
}}


.halfway-line {{
    position: absolute;

    left: 0;

    right: 0;

    top: 72%;

    border-top:
        2px solid
        rgba(
            255,
            255,
            255,
            .92
        );
}}


.mid-circle {{
    position: absolute;

    /*
    Also centred at 50%.
    */

    left: 38.5%;

    top:
        calc(
            72% - 47px
        );

    width: 23%;

    height: 94px;

    border:
        2px solid
        rgba(
            255,
            255,
            255,
            .92
        );

    border-radius:
        50%;
}}


.centre-dot {{
    position: absolute;

    width: 5px;

    height: 5px;

    left:
        calc(
            50% - 2.5px
        );

    top:
        calc(
            72% - 2.5px
        );

    background:
        rgba(
            255,
            255,
            255,
            .95
        );

    border-radius:
        50%;
}}


/* =========================================================
   ZONE STYLE
   ========================================================= */

.zone-card {{
    position: absolute;

    z-index: 2;

    border:
        1px solid
        rgba(
            255,
            255,
            255,
            .11
        );

    display: flex;

    flex-direction:
        column;

    align-items:
        center;

    justify-content:
        center;

    text-align:
        center;

    padding:
        6px 4px;

    overflow:
        hidden;
}}


.zone-name {{
    width: 100%;

    font-size:
        10px;

    font-weight:
        700;

    line-height:
        1.05;

    color:
        rgba(
            255,
            255,
            255,
            .74
        );

    text-align:
        center;

    overflow-wrap:
        break-word;
}}


.zone-count {{
    margin-top:
        5px;

    font-size:
        19px;

    font-weight:
        800;

    line-height:
        1;

    color:
        #ffffff;

    text-align:
        center;
}}


/* =========================================================
   SYMMETRICAL ZONE GEOMETRY

   Centre line = 50%

   SIDE NEAR: 20 → 34
   NEAR POST: 34 → 42
   CENTRAL:   42 → 58
   FAR POST:  58 → 66
   SIDE FAR:  66 → 80

   SIDE NEAR and SIDE FAR are exact mirrors.
   ========================================================= */


.near_zone {{
    left: 1.2%;

    top: 0;

    width: 18%;

    height: 39%;
}}


.side_zone_near {{
    left: 20%;

    top: 0;

    width: 14%;

    height: 30%;
}}


.near_post {{
    left: 34%;

    top: 0;

    width: 8%;

    height: 13%;
}}


.central {{
    left: 42%;

    top: 0;

    width: 16%;

    height: 13%;
}}


.far_post {{
    left: 58%;

    top: 0;

    width: 8%;

    height: 13%;
}}


.side_zone_far {{
    left: 66%;

    top: 0;

    width: 14%;

    height: 30%;
}}


.far_zone {{
    right: 1.2%;

    top: 0;

    width: 18%;

    height: 39%;
}}


.back_zone {{
    /*
    Same centre as CENTRAL.

    34 → 66 = centered at 50%.
    */

    left: 34%;

    top: 13%;

    width: 32%;

    height: 17%;
}}


.edge_of_box {{
    /*
    Centre = 50%.
    */

    left: 31%;

    top: 30%;

    width: 38%;

    height: 11%;

    background:
        transparent !important;

    border-color:
        transparent;

    z-index: 11;
}}


.zone-caption {{
    margin-top:
        8px;

    display: grid;

    grid-template-columns:
        1fr 1fr;

    gap:
        14px;

    color:
        rgba(
            255,
            255,
            255,
            .58
        );

    font-size:
        11px;
}}


.zone-caption > div {{
    text-align:
        center;
}}


@media (
    max-width: 900px
) {{

    .zone-grid,
    .zone-caption {{
        grid-template-columns:
            1fr;
    }}

}}

</style>

</head>


<body>

<div class="zone-shell">

    <div class="zone-grid">
        {panels_html}
    </div>

    <div class="zone-caption">
        {captions_html}
    </div>

</div>

</body>
</html>
"""

    st.iframe(
        html,
        width="stretch",
        height=455,
    )

    if report_context is not None:
        if show_delivery and show_finishing:
            section_title = "Zone Visualisation"
        elif show_delivery:
            section_title = "Delivery Zone Visualisation"
        else:
            section_title = "Finishing Zone Visualisation"

        report_item = create_image_report_item(
            module="corner_kick",
            section_title=section_title,
            html=html,
            context=report_context,
            width_px=1400,
            height_px=455,
        )

        render_add_to_report_button(
            report_item,
            key=(
                "report_corner_zone_visualisation_"
                f"{'delivery' if show_delivery and not show_finishing else 'finishing' if show_finishing and not show_delivery else 'both'}_"
                f"{report_item['id']}"
            ),
        )


# ============================================================
# OUTCOME BREAKDOWN
# ============================================================

def build_outcome_dataframe(
    records: list[dict],
) -> pd.DataFrame:
    total = len(
        records
    )

    counts = category_counts(
        records,
        "outcome",
    )

    rows = []

    for outcome, count in counts.items():
        rows.append(
            {
                "Outcome":
                    outcome,

                "Count":
                    count,

                "Percentage":
                    calculate_rate(
                        count,
                        total,
                    ),

                "Display":
                    format_rate(
                        count,
                        total,
                    ),
            }
        )

    df = pd.DataFrame(
        rows
    )

    if df.empty:
        return df

    return (
        df
        .sort_values(
            "Percentage",
            ascending=True,
        )
        .reset_index(
            drop=True
        )
    )


def render_outcome_breakdown(
    records: list[dict],
    report_context: dict | None = None,
):
    st.markdown(
        "### Outcome Breakdown"
    )

    df = build_outcome_dataframe(
        records
    )

    if df.empty:
        st.info(
            "No OUTCOME data available."
        )
        return

    total = len(
        records
    )

    fig = px.bar(
        df,
        x="Percentage",
        y="Outcome",
        orientation="h",
        text="Display",
        custom_data=[
            "Count",
        ],
    )

    fig.update_traces(
        textposition="outside",
        cliponaxis=False,
        marker_color=CORNER_SINGLE_GRAY,
        hovertemplate=(
            "<b>%{y}</b><br>"
            "%{x:.0f}% "
            "(%{customdata[0]}/"
            f"{total})"
            "<extra></extra>"
        ),
    )

    fig.update_layout(
        height=max(
            280,
            52 * len(df),
        ),

        margin=dict(
            l=20,
            r=130,
            t=10,
            b=20,
        ),

        xaxis_title=(
            "Corner Rate (%)"
        ),

        yaxis_title="",

        xaxis=dict(
            range=[
                0,
                110,
            ]
        ),

        showlegend=False,
    )

    st.plotly_chart(
        fig,
        width="stretch",
    )

    st.caption(
        "OUTCOME labels are not mutually exclusive. "
        "One corner can contain more than one outcome."
    )

    if report_context is not None:
        report_item = create_plotly_report_item(
            module="corner_kick",
            section_title="Outcome Breakdown",
            figure=fig,
            context=report_context,
            notes=[
                "OUTCOME labels are not mutually exclusive. "
                "One corner can contain more than one outcome."
            ],
        )

        render_add_to_report_button(
            report_item,
            key=(
                "report_corner_outcome_"
                f"{report_item['id']}"
            ),
        )


# ============================================================
# EFFECTIVENESS DATA
# ============================================================

def build_effectiveness_dataframe(
    records: list[dict],
    group_key: str,
    phase: str,
    include_unknown: bool = False,
    first_contact_table: bool = False,
) -> pd.DataFrame:
    categories = category_counts(
        records,
        group_key,
        include_unknown,
    )

    rows = []

    for category in categories:
        category_records = (
            records_with_category(
                records,
                group_key,
                category,
            )
        )

        metrics = get_corner_metrics(
            category_records,
            phase,
        )

        total = metrics[
            "total"
        ]

        row = {
            "Category":
                category,

            "Corners":
                total,

            "FC Won %":
                calculate_rate(
                    metrics["fc_won"],
                    total,
                ),

            "Attempt %":
                calculate_rate(
                    metrics["attempt"],
                    total,
                ),

            "2nd Phase %":
                calculate_rate(
                    metrics["second_phase"],
                    total,
                ),

            "Counter %":
                calculate_rate(
                    metrics["counter"],
                    total,
                ),
        }

        if not first_contact_table:
            row[
                "FC Won"
            ] = format_rate(
                metrics["fc_won"],
                total,
            )

        if phase == "defensive":
            row.update(
                {
                    "Attempt Conceded":
                        format_rate(
                            metrics["attempt"],
                            total,
                        ),

                    "Goal Conceded":
                        format_rate(
                            metrics["goal"],
                            total,
                        ),

                    "Goal Conceded Conversion":
                        format_rate(
                            metrics["goal"],
                            metrics["attempt"],
                        ),

                    "2nd Phase":
                        format_rate(
                            metrics["second_phase"],
                            total,
                        ),

                    "Counter Launched":
                        format_rate(
                            metrics["counter"],
                            total,
                        ),
                }
            )

        else:
            row.update(
                {
                    "Attempt":
                        format_rate(
                            metrics["attempt"],
                            total,
                        ),

                    "Goal":
                        format_rate(
                            metrics["goal"],
                            total,
                        ),

                    "Goal Conversion":
                        format_rate(
                            metrics["goal"],
                            metrics["attempt"],
                        ),

                    "2nd Phase Attack":
                        format_rate(
                            metrics["second_phase"],
                            total,
                        ),

                    "Counter Allowed":
                        format_rate(
                            metrics["counter"],
                            total,
                        ),
                }
            )

        rows.append(
            row
        )

    df = pd.DataFrame(
        rows
    )

    if df.empty:
        return df

    return (
        df
        .sort_values(
            "Corners",
            ascending=False,
        )
        .reset_index(
            drop=True
        )
    )


# ============================================================
# FIRST CONTACT CHART
# ============================================================

def render_first_contact_chart(
    records: list[dict],
    phase: str,
    report_context: dict | None = None,
):
    rows = []

    for category in [
        FC_LOST,
        FC_WON,
    ]:
        category_records = (
            records_with_category(
                records,
                "first_contact",
                category,
            )
        )

        if not category_records:
            continue

        metrics = get_corner_metrics(
            category_records,
            phase,
        )

        total = metrics[
            "total"
        ]

        if phase == "defensive":
            chart_metrics = [
                (
                    "Attempt Conceded",
                    metrics["attempt"],
                ),
                (
                    "2nd Phase",
                    metrics["second_phase"],
                ),
                (
                    "Counter Launched",
                    metrics["counter"],
                ),
            ]

        else:
            chart_metrics = [
                (
                    "Attempt",
                    metrics["attempt"],
                ),
                (
                    "2nd Phase",
                    metrics["second_phase"],
                ),
                (
                    "Counter Allowed",
                    metrics["counter"],
                ),
            ]

        for metric_name, count in chart_metrics:
            rows.append(
                {
                    "First Contact":
                        category,

                    "Metric":
                        metric_name,

                    "Rate":
                        calculate_rate(
                            count,
                            total,
                        ),

                    "Count":
                        count,

                    "Total":
                        total,

                    "Display":
                        format_rate(
                            count,
                            total,
                        ),
                }
            )

    df = pd.DataFrame(
        rows
    )

    if df.empty:
        return

    fig = px.bar(
        df,
        x="First Contact",
        y="Rate",
        color="Metric",
        barmode="group",
        text="Display",
        custom_data=[
            "Count",
            "Total",
        ],
        color_discrete_map=CORNER_GRAYSCALE,
    )

    fig.update_traces(
        textposition="outside",
        cliponaxis=False,

        hovertemplate=(
            "<b>%{x}</b><br>"
            "%{fullData.name}: "
            "%{y:.0f}% "
            "(%{customdata[0]}/"
            "%{customdata[1]})"
            "<extra></extra>"
        ),
    )

    fig.update_layout(
        height=360,

        margin=dict(
            l=20,
            r=20,
            t=10,
            b=20,
        ),

        xaxis_title="",

        yaxis_title=(
            "Rate (%)"
        ),

        yaxis=dict(
            range=[
                0,
                118,
            ]
        ),

        legend_title="",
    )

    st.plotly_chart(
        fig,
        width="stretch",
    )

    if report_context is not None:
        report_item = create_plotly_report_item(
            module="corner_kick",
            section_title="First Contact → Outcome",
            figure=fig,
            context=report_context,
        )

        render_add_to_report_button(
            report_item,
            key=(
                "report_corner_first_contact_chart_"
                f"{report_item['id']}"
            ),
        )


# ============================================================
# DELIVERY TYPE EFFECTIVENESS
# ============================================================

def render_delivery_type_scatter(
    records: list[dict],
    phase: str,
    report_context: dict | None = None,
):
    rows = []

    for category in category_counts(
        records,
        "delivery_type",
    ):
        category_records = (
            records_with_category(
                records,
                "delivery_type",
                category,
            )
        )

        metrics = get_corner_metrics(
            category_records,
            phase,
        )

        total = metrics[
            "total"
        ]

        if total == 0:
            continue

        rows.append(
            {
                "Delivery Type":
                    category,

                "Corners":
                    total,

                "FC Won Rate":
                    calculate_rate(
                        metrics["fc_won"],
                        total,
                    ),

                "Attempt Rate":
                    calculate_rate(
                        metrics["attempt"],
                        total,
                    ),

                "FC Won Display":
                    format_rate(
                        metrics["fc_won"],
                        total,
                    ),

                "Attempt Display":
                    format_rate(
                        metrics["attempt"],
                        total,
                    ),

                "2nd Phase Display":
                    format_rate(
                        metrics["second_phase"],
                        total,
                    ),

                "Counter Display":
                    format_rate(
                        metrics["counter"],
                        total,
                    ),
            }
        )

    df = pd.DataFrame(
        rows
    )

    if df.empty:
        st.info(
            "No delivery-type data available."
        )
        return

    if phase == "defensive":
        attempt_label = (
            "Attempt Conceded"
        )

        counter_label = (
            "Counter Launched"
        )

        y_title = (
            "Attempt Conceded Rate (%)"
        )

    else:
        attempt_label = "Attempt"

        counter_label = (
            "Counter Allowed"
        )

        y_title = (
            "Attempt Rate (%)"
        )

    x_min = max(
        0.0,
        float(
            df["FC Won Rate"].min()
        ) - 8.0,
    )

    x_max = min(
        100.0,
        float(
            df["FC Won Rate"].max()
        ) + 8.0,
    )

    if (
        x_max - x_min
    ) < 28:
        x_center = (
            x_min + x_max
        ) / 2

        x_min = max(
            0.0,
            x_center - 14,
        )

        x_max = min(
            100.0,
            x_center + 14,
        )

    text_positions = [
        (
            "bottom center"
            if attempt_rate >= 94
            else "top center"
        )
        for attempt_rate
        in df["Attempt Rate"]
    ]

    delivery_types = [
        str(value)
        for value in df["Delivery Type"].tolist()
    ]
    delivery_color_map = {
        delivery_type: CORNER_SINGLE_GRAY
        for delivery_type in delivery_types
    }

    fig = px.scatter(
        df,

        x="FC Won Rate",

        y="Attempt Rate",

        color="Delivery Type",

        text="Delivery Type",

        custom_data=[
            "Corners",
            "FC Won Display",
            "Attempt Display",
            "2nd Phase Display",
            "Counter Display",
        ],
        color_discrete_map=delivery_color_map,
    )

    fig.update_traces(
        mode="markers+text",

        textposition=
            text_positions,

        textfont=dict(
            size=10,
        ),

        cliponaxis=False,

        marker=dict(
            size=7,

            opacity=0.92,

            line=dict(
                width=1,

                color=(
                    "rgba(255,255,255,0.55)"
                ),
            ),
        ),

        hovertemplate=(
            "<b>%{text}</b><br>"
            "Corners: "
            "%{customdata[0]}<br>"
            "FC Won: "
            "%{customdata[1]}<br>"
            f"{attempt_label}: "
            "%{customdata[2]}<br>"
            "2nd Phase: "
            "%{customdata[3]}<br>"
            f"{counter_label}: "
            "%{customdata[4]}"
            "<extra></extra>"
        ),
    )

    fig.add_vline(
        x=50,

        line_width=1,

        line_dash="dot",

        opacity=0.20,
    )

    fig.add_hline(
        y=50,

        line_width=1,

        line_dash="dot",

        opacity=0.20,
    )

    fig.update_layout(
        height=205,

        margin=dict(
            l=20,
            r=15,
            t=12,
            b=15,
        ),

        xaxis_title=(
            "First Contact Won (%)"
        ),

        yaxis_title=
            y_title,

        xaxis=dict(
            range=[
                x_min,
                x_max,
            ],

            dtick=10,

            zeroline=False,

            fixedrange=True,
        ),

        yaxis=dict(
            range=[
                -4,
                108,
            ],

            dtick=25,

            zeroline=False,

            fixedrange=True,
        ),

        showlegend=False,
    )

    chart_col, spacer_col = st.columns(
        [
            1.25,
            1.0,
        ]
    )

    with chart_col:
        st.plotly_chart(
            fig,

            width="stretch",

            config={
                "displayModeBar":
                    False,

                "displaylogo":
                    False,

                "scrollZoom":
                    False,
            },
        )

        if report_context is not None:
            report_item = create_plotly_report_item(
                module="corner_kick",
                section_title=(
                    "Delivery Type Effectiveness — Scatter"
                ),
                figure=fig,
                context=report_context,
            )

            render_add_to_report_button(
                report_item,
                key=(
                    "report_corner_delivery_scatter_"
                    f"{report_item['id']}"
                ),
            )


def render_effectiveness_table(
    title: str,
    records: list[dict],
    group_key: str,
    phase: str,
    category_name: str,
    include_unknown: bool = False,
    first_contact_table: bool = False,
    show_title: bool = True,
    report_context: dict | None = None,
    report_section_title: str | None = None,
):
    if show_title:
        st.markdown(
            f"#### {title}"
        )

    df = build_effectiveness_dataframe(
        records=records,
        group_key=group_key,
        phase=phase,
        include_unknown=include_unknown,
        first_contact_table=(
            first_contact_table
        ),
    )

    if df.empty:
        st.info(
            "No data available."
        )
        return

    df = df.rename(
        columns={
            "Category":
                category_name,
        }
    )

    if phase == "defensive":
        if first_contact_table:
            display_columns = [
                category_name,
                "Corners",
                "Attempt Conceded",
                "Goal Conceded",
                "Goal Conceded Conversion",
                "2nd Phase",
                "Counter Launched",
            ]

        else:
            display_columns = [
                category_name,
                "Corners",
                "FC Won",
                "Attempt Conceded",
                "Goal Conceded",
                "Goal Conceded Conversion",
                "2nd Phase",
                "Counter Launched",
            ]

    else:
        if first_contact_table:
            display_columns = [
                category_name,
                "Corners",
                "Attempt",
                "Goal",
                "Goal Conversion",
                "2nd Phase Attack",
                "Counter Allowed",
            ]

        else:
            display_columns = [
                category_name,
                "Corners",
                "FC Won",
                "Attempt",
                "Goal",
                "Goal Conversion",
                "2nd Phase Attack",
                "Counter Allowed",
            ]

    display_df = df[
        display_columns
    ].copy()

    display_df = display_df.rename(
        columns={
            "2nd Phase Attack":
                "2nd Phase",
        }
    )

    st.dataframe(
        display_df,
        hide_index=True,
        width="stretch",

        column_config={
            category_name:
                st.column_config.TextColumn(
                    category_name,
                    width="large",
                ),

            "Corners":
                st.column_config.NumberColumn(
                    "Corners",
                    width="small",
                ),
        },
    )

    if report_context is not None:
        section_title = (
            report_section_title
            or title
            or f"{category_name} Effectiveness"
        )

        report_item = create_table_report_item(
            module="corner_kick",
            section_title=section_title,
            dataframe=display_df,
            context=report_context,
        )

        render_add_to_report_button(
            report_item,
            key=(
                "report_corner_effectiveness_table_"
                f"{group_key}_"
                f"{report_item['id']}"
            ),
        )


# ============================================================
# EFFECTIVENESS SECTION
# ============================================================

def render_effectiveness(
    records: list[dict],
    phase: str,
    analysis_scope: str | None = None,
    report_context: dict | None = None,
):
    st.markdown(
        "### Effectiveness"
    )

    # --------------------------------------------------------
    # FIRST CONTACT
    # --------------------------------------------------------

    st.markdown(
        "#### First Contact → Outcome"
    )

    render_first_contact_chart(
        records,
        phase,
        report_context=report_context,
    )

    render_effectiveness_table(
        title="",
        records=records,
        group_key="first_contact",
        phase=phase,
        category_name=(
            "First Contact"
        ),
        first_contact_table=True,
        show_title=False,
        report_context=report_context,
        report_section_title=(
            "First Contact Effectiveness — Table"
        ),
    )

    st.write("")

    # --------------------------------------------------------
    # DELIVERY TYPE
    # --------------------------------------------------------

    st.markdown(
        "#### Delivery Type Effectiveness"
    )

    if analysis_scope in {
        "Competition Analysis",
        "All Matches Analysis",
    }:
        render_delivery_type_scatter(
            records,
            phase,
            report_context=report_context,
        )

    render_effectiveness_table(
        title="",
        records=records,
        group_key="delivery_type",
        phase=phase,
        category_name=(
            "Delivery Type"
        ),
        show_title=False,
        report_context=report_context,
        report_section_title=(
            "Delivery Type Effectiveness — Table"
        ),
    )

    st.write("")

    # --------------------------------------------------------
    # TAKER / OPPONENT PLAYERS
    # --------------------------------------------------------

    if phase == "offensive":
        render_effectiveness_table(
            title=(
                "Taker Effectiveness"
            ),
            records=records,
            group_key="taker",
            phase=phase,
            category_name="Taker",
            include_unknown=True,
            report_context=report_context,
        )

    else:
        render_effectiveness_table(
            title=(
                "Opponent Players Effectiveness"
            ),
            records=records,
            group_key=(
                "opponent_players"
            ),
            phase=phase,
            category_name=(
                "Opponent Players"
            ),
            include_unknown=True,
            report_context=report_context,
        )

    st.write("")

    # --------------------------------------------------------
    # SIDE
    # --------------------------------------------------------

    render_effectiveness_table(
        title=(
            "Side Effectiveness"
        ),
        records=records,
        group_key="side",
        phase=phase,
        category_name="Side",
        report_context=report_context,
    )

    # --------------------------------------------------------
    # OPPONENT CONTEXT
    # --------------------------------------------------------

    if phase == "offensive":
        st.write("")

        st.markdown(
            "#### Opponent Context"
        )

        render_effectiveness_table(
            title=(
                "Opponent Organization"
            ),
            records=records,
            group_key=(
                "opponent_organization"
            ),
            phase=phase,
            category_name=(
                "Opponent Organization"
            ),
            report_context=report_context,
        )


# ============================================================
# ZONE EFFECTIVENESS DATA
# ============================================================

def build_zone_dataframe(
    records: list[dict],
    zone_key: str,
    phase: str,
) -> pd.DataFrame:
    zones = category_counts(
        records,
        zone_key,
    )

    rows = []

    for zone in zones:
        zone_records = (
            records_with_category(
                records,
                zone_key,
                zone,
            )
        )

        metrics = get_corner_metrics(
            zone_records,
            phase,
        )

        total = metrics[
            "total"
        ]

        row = {
            "Zone":
                zone,

            "Corners":
                total,

            "FC Won %":
                calculate_rate(
                    metrics["fc_won"],
                    total,
                ),

            "Attempt %":
                calculate_rate(
                    metrics["attempt"],
                    total,
                ),

            "2nd Phase %":
                calculate_rate(
                    metrics["second_phase"],
                    total,
                ),

            "FC Won":
                format_rate(
                    metrics["fc_won"],
                    total,
                ),
        }

        if phase == "defensive":
            row.update(
                {
                    "Attempt Conceded":
                        format_rate(
                            metrics["attempt"],
                            total,
                        ),

                    "Goal Conceded":
                        format_rate(
                            metrics["goal"],
                            total,
                        ),

                    "Goal Conceded Conversion":
                        format_rate(
                            metrics["goal"],
                            metrics["attempt"],
                        ),

                    "2nd Phase":
                        format_rate(
                            metrics["second_phase"],
                            total,
                        ),

                    "Counter Launched":
                        format_rate(
                            metrics["counter"],
                            total,
                        ),
                }
            )

        else:
            row.update(
                {
                    "Attempt":
                        format_rate(
                            metrics["attempt"],
                            total,
                        ),

                    "Goal":
                        format_rate(
                            metrics["goal"],
                            total,
                        ),

                    "Goal Conversion":
                        format_rate(
                            metrics["goal"],
                            metrics["attempt"],
                        ),

                    "2nd Phase Attack":
                        format_rate(
                            metrics["second_phase"],
                            total,
                        ),

                    "Counter Allowed":
                        format_rate(
                            metrics["counter"],
                            total,
                        ),
                }
            )

        rows.append(
            row
        )

    df = pd.DataFrame(
        rows
    )

    if df.empty:
        return df

    return (
        df
        .sort_values(
            "Corners",
            ascending=False,
        )
        .reset_index(
            drop=True
        )
    )


# ============================================================
# ZONE EFFECTIVENESS CHART
# ============================================================

def render_zone_effectiveness_chart(
    records: list[dict],
    zone_key: str,
    phase: str,
    report_context: dict | None = None,
):
    zones = category_counts(
        records,
        zone_key,
    )

    rows = []

    for zone in zones:
        zone_records = (
            records_with_category(
                records,
                zone_key,
                zone,
            )
        )

        metrics = get_corner_metrics(
            zone_records,
            phase,
        )

        total = metrics[
            "total"
        ]

        if phase == "defensive":
            chart_metrics = [
                (
                    "FC Won",
                    metrics["fc_won"],
                ),
                (
                    "Attempt Conceded",
                    metrics["attempt"],
                ),
                (
                    "2nd Phase",
                    metrics["second_phase"],
                ),
            ]

        else:
            chart_metrics = [
                (
                    "FC Won",
                    metrics["fc_won"],
                ),
                (
                    "Attempt",
                    metrics["attempt"],
                ),
                (
                    "2nd Phase",
                    metrics["second_phase"],
                ),
            ]

        for metric_name, count in chart_metrics:
            rows.append(
                {
                    "Zone":
                        zone,

                    "Metric":
                        metric_name,

                    "Rate":
                        calculate_rate(
                            count,
                            total,
                        ),

                    "Count":
                        count,

                    "Total":
                        total,

                    "Display":
                        format_rate(
                            count,
                            total,
                        ),
                }
            )

    df = pd.DataFrame(
        rows
    )

    if df.empty:
        return

    fig = px.bar(
        df,
        x="Zone",
        y="Rate",
        color="Metric",
        barmode="group",
        text="Display",

        custom_data=[
            "Count",
            "Total",
        ],
        color_discrete_map=CORNER_GRAYSCALE,
    )

    fig.update_traces(
        textposition="outside",
        cliponaxis=False,

        hovertemplate=(
            "<b>%{x}</b><br>"
            "%{fullData.name}: "
            "%{y:.0f}% "
            "(%{customdata[0]}/"
            "%{customdata[1]})"
            "<extra></extra>"
        ),
    )

    fig.update_layout(
        height=380,

        margin=dict(
            l=20,
            r=20,
            t=10,
            b=20,
        ),

        xaxis_title="",

        yaxis_title=(
            "Rate (%)"
        ),

        yaxis=dict(
            range=[
                0,
                118,
            ]
        ),

        legend_title="",
    )

    st.plotly_chart(
        fig,
        width="stretch",
    )

    if report_context is not None:
        zone_label = (
            "Delivery Zone"
            if zone_key == "delivery_zone"
            else "Finishing Zone"
        )

        report_item = create_plotly_report_item(
            module="corner_kick",
            section_title=(
                f"{zone_label} Effectiveness"
            ),
            figure=fig,
            context=report_context,
        )

        render_add_to_report_button(
            report_item,
            key=(
                "report_corner_zone_chart_"
                f"{zone_key}_"
                f"{report_item['id']}"
            ),
        )


# ============================================================
# ZONE TABLE
# ============================================================

def render_zone_table(
    title: str,
    records: list[dict],
    zone_key: str,
    phase: str,
    show_title: bool = True,
    report_context: dict | None = None,
    report_section_title: str | None = None,
):
    if show_title:
        st.markdown(
            f"#### {title}"
        )

    df = build_zone_dataframe(
        records,
        zone_key,
        phase,
    )

    if df.empty:
        st.info(
            "No zone data available."
        )
        return

    if phase == "defensive":
        display_columns = [
            "Zone",
            "Corners",
            "FC Won",
            "Attempt Conceded",
            "2nd Phase",
            "Counter Launched",
        ]

    else:
        display_columns = [
            "Zone",
            "Corners",
            "FC Won",
            "Attempt",
            "2nd Phase Attack",
            "Counter Allowed",
        ]

    display_df = df[
        display_columns
    ].copy()

    display_df = display_df.rename(
        columns={
            "2nd Phase Attack":
                "2nd Phase",
        }
    )

    st.dataframe(
        display_df,
        hide_index=True,
        width="stretch",

        column_config={
            "Zone":
                st.column_config.TextColumn(
                    "Zone",
                    width="large",
                ),

            "Corners":
                st.column_config.NumberColumn(
                    "Corners",
                    width="small",
                ),
        },
    )

    if report_context is not None:
        section_title = (
            report_section_title
            or title
            or (
                "Delivery Zone Summary"
                if zone_key == "delivery_zone"
                else "Finishing Zone Summary"
            )
        )

        report_item = create_table_report_item(
            module="corner_kick",
            section_title=section_title,
            dataframe=display_df,
            context=report_context,
        )

        render_add_to_report_button(
            report_item,
            key=(
                "report_corner_zone_table_"
                f"{zone_key}_"
                f"{report_item['id']}"
            ),
        )


# ============================================================
# ZONE EFFECTIVENESS
# ============================================================

def render_zone_effectiveness(
    records: list[dict],
    phase: str,
    report_context: dict | None = None,
):
    st.markdown(
        "### Zone Effectiveness"
    )

    st.markdown(
        "#### Delivery Zone Summary"
    )

    render_zone_effectiveness_chart(
        records=records,
        zone_key="delivery_zone",
        phase=phase,
        report_context=report_context,
    )

    render_zone_table(
        title="",
        records=records,
        zone_key="delivery_zone",
        phase=phase,
        show_title=False,
        report_context=report_context,
        report_section_title=(
            "Delivery Zone Summary"
        ),
    )

    st.write("")

    render_zone_table(
        title=(
            "Finishing Zone Summary"
        ),
        records=records,
        zone_key="finishing_zone",
        phase=phase,
        report_context=report_context,
        report_section_title=(
            "Finishing Zone Summary"
        ),
    )


# ============================================================
# CORNER EXECUTION FLOW
# ============================================================

def render_corner_execution_flow(
    records: list[dict],
    phase: str,
    analysis_scope: str | None = None,
    report_context: dict | None = None,
):
    """Render existing corner content in the sequence of corner execution."""
    st.markdown("### Corner Execution")

    # 1. TAKER / DEFENSIVE SETUP
    if phase == "offensive":
        render_effectiveness_table(
            title="Taker Effectiveness",
            records=records,
            group_key="taker",
            phase=phase,
            category_name="Taker",
            include_unknown=True,
            report_context=report_context,
        )
    else:
        render_effectiveness_table(
            title="Opponent Players Effectiveness",
            records=records,
            group_key="opponent_players",
            phase=phase,
            category_name="Opponent Players",
            include_unknown=True,
            report_context=report_context,
        )

    st.write("")

    # 2. SIDE
    render_effectiveness_table(
        title="Side Effectiveness",
        records=records,
        group_key="side",
        phase=phase,
        category_name="Side",
        report_context=report_context,
    )

    st.write("")

    # 3. DELIVERY TYPE
    st.markdown("#### Delivery Type Effectiveness")

    if analysis_scope in {
        "Competition Analysis",
        "All Matches Analysis",
    }:
        render_delivery_type_scatter(
            records,
            phase,
            report_context=report_context,
        )

    render_effectiveness_table(
        title="",
        records=records,
        group_key="delivery_type",
        phase=phase,
        category_name="Delivery Type",
        show_title=False,
        report_context=report_context,
        report_section_title="Delivery Type Effectiveness — Table",
    )

    if phase == "offensive":
        st.write("")
        st.markdown("#### Opponent Context")
        render_effectiveness_table(
            title="Opponent Organization",
            records=records,
            group_key="opponent_organization",
            phase=phase,
            category_name="Opponent Organization",
            report_context=report_context,
        )

    st.markdown("---")

    # 4. DELIVERY ZONE
    st.markdown("### Delivery Zone")

    render_zone_visualisation(
        records,
        phase,
        report_context=report_context,
        show_delivery=True,
        show_finishing=False,
        show_heading=False,
    )

    st.markdown("#### Delivery Zone Effectiveness")

    render_zone_effectiveness_chart(
        records=records,
        zone_key="delivery_zone",
        phase=phase,
        report_context=report_context,
    )

    render_zone_table(
        title="",
        records=records,
        zone_key="delivery_zone",
        phase=phase,
        show_title=False,
        report_context=report_context,
        report_section_title="Delivery Zone Summary",
    )

    st.markdown("---")

    # 5. FIRST CONTACT
    st.markdown("### First Contact → Outcome")

    render_first_contact_chart(
        records,
        phase,
        report_context=report_context,
    )

    render_effectiveness_table(
        title="",
        records=records,
        group_key="first_contact",
        phase=phase,
        category_name="First Contact",
        first_contact_table=True,
        show_title=False,
        report_context=report_context,
        report_section_title="First Contact Effectiveness — Table",
    )

    st.markdown("---")

    # 6. FINISHING ZONE
    st.markdown("### Finishing Zone")

    render_zone_visualisation(
        records,
        phase,
        report_context=report_context,
        show_delivery=False,
        show_finishing=True,
        show_heading=False,
    )

    render_zone_table(
        title="Finishing Zone Summary",
        records=records,
        zone_key="finishing_zone",
        phase=phase,
        show_title=True,
        report_context=report_context,
        report_section_title="Finishing Zone Summary",
    )

    st.markdown("---")

    # 7. OUTCOME
    render_outcome_breakdown(
        records,
        report_context=report_context,
    )


# ============================================================
# MAIN RENDER
# ============================================================

def render_corner_kick_analysis(
    analysis: dict,
    phase: str | None = None,
    analysis_scope: str | None = None,
    report_context: dict | None = None,
):
    records = analysis.get(
        "records",
        [],
    )

    if not records:
        st.info(
            "No corner events found "
            "for the selected filters."
        )
        return

    phase = resolve_phase(
        analysis,
        phase,
    )

    phase_title = (
        "Defensive"
        if phase == "defensive"
        else "Offensive"
    )

    st.subheader(
        f"Corner Kicks — {phase_title}"
    )

    render_create_report_button(
        "corner_kick",
        key="create_corner_kick_report",
    )

    render_kpis(
        records,
        phase,
        report_context=report_context,
    )

    st.markdown("---")

    render_corner_execution_flow(
        records,
        phase,
        analysis_scope,
        report_context=report_context,
    )
