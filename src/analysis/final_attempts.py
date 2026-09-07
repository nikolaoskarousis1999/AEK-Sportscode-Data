from collections import Counter

import pandas as pd
import plotly.express as px
import streamlit as st


TIME_PERIODS = [
    "1-15",
    "16-30",
    "31-45+",
    "46-60",
    "61-75",
    "76-90+",
]

OUTCOMES = [
    "ON TARGET",
    "OFF TARGET",
    "BLOCKED",
]

OTHER_VALUES = {
    "",
    "OTHER",
    "Other",
    "UNKNOWN",
    "Unknown",
    None,
}

RECOVERY_ZONE_ORDER = [
    "Zone O3",
    "Zone O2",
    "Zone O1",
    "Zone PO3",
    "Zone PO2",
    "Zone PO1",
    "Zone PD3",
    "Zone PD2",
    "Zone PD1",
    "Zone D3",
    "Zone D2",
    "Zone D1",
]

PASSES_ORDER = [
    "0",
    "ZERO",
    "1-3",
    "4-5",
    "6-9",
    "10+",
]

TOUCHES_ORDER = [
    "1 TOUCH",
    "2 TOUCHES",
    "3 TOUCHES",
    "4+ TOUCHES",
]

ATTACK_TYPE_ORDER = [
    "ORG. ATTACK",
    "COUNTER",
    "SET PLAY",
]

ORG_ATTACK_ORDER = [
    "BUILD UP",
    "ESTABLISH ATTACK",
    "FINISHING",
]

SET_PLAY_ORDER = [
    "FREE KICK C",
    "FREE KICK CROSS",
    "FREE KICK DIRECT",
    "CORNER KICK",
    "PENALTY KICK",
    "THROW IN",
]

PASS_TYPE_ORDER = [
    "PASS",
    "CROSS",
    "VERTICAL",
    "CUTBACK",
    "BEHIND OPP LINE",
]


# ============================================================
# BASIC HELPERS
# ============================================================

def _as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _norm(value):
    if value is None:
        return ""
    return " ".join(str(value).strip().upper().split())


def _clean_values(record, key, include_other=False):
    values = []
    seen = set()

    for raw in _as_list(record.get(key)):
        text = str(raw).strip() if raw is not None else ""
        if not text:
            continue

        if not include_other and _norm(text) == "OTHER":
            continue

        normalized = _norm(text)
        if normalized in seen:
            continue

        seen.add(normalized)
        values.append(text)

    return values


def event_has_value(record, key, target):
    target = _norm(target)
    return any(
        _norm(value) == target
        for value in _as_list(record.get(key))
    )


def count_value(records, key, value):
    return sum(
        1
        for record in records
        if event_has_value(record, key, value)
    )


def rate(numerator, denominator):
    if denominator == 0:
        return 0.0
    return numerator / denominator * 100


def fmt_rate(numerator, denominator):
    if denominator == 0:
        return "—"
    return f"{rate(numerator, denominator):.0f}% ({numerator}/{denominator})"


def fmt_count_rate(numerator, denominator):
    if denominator == 0:
        return "0"
    return f"{numerator} ({rate(numerator, denominator):.0f}%)"


def category_counts(records, key, include_other=False):
    counts = Counter()

    for record in records:
        for value in _clean_values(
            record,
            key,
            include_other=include_other,
        ):
            counts[value] += 1

    return counts


def records_with_category(records, key, category):
    return [
        record
        for record in records
        if event_has_value(
            record,
            key,
            category,
        )
    ]


def most_common(records, key):
    counts = category_counts(records, key)

    if not counts:
        return "-", 0

    return counts.most_common(1)[0]


def ordered_categories(
    records,
    key,
    preferred_order=None,
):
    categories = list(
        category_counts(
            records,
            key,
        ).keys()
    )

    if not categories:
        return []

    if not preferred_order:
        return sorted(
            categories,
            key=lambda value: _norm(value),
        )

    preferred_map = {
        _norm(value): index
        for index, value
        in enumerate(preferred_order)
    }

    return sorted(
        categories,
        key=lambda value: (
            preferred_map.get(
                _norm(value),
                999,
            ),
            _norm(value),
        ),
    )


def resolve_phase(analysis, phase):
    if phase:
        return str(phase).lower()

    analysis_phase = analysis.get("phase")
    if analysis_phase:
        return str(analysis_phase).lower()

    return "offensive"


def outcome_metrics(records):
    total = len(records)

    on_target = count_value(
        records,
        "outcome",
        "ON TARGET",
    )

    off_target = count_value(
        records,
        "outcome",
        "OFF TARGET",
    )

    blocked = count_value(
        records,
        "outcome",
        "BLOCKED",
    )

    return {
        "total": total,
        "on_target": on_target,
        "off_target": off_target,
        "blocked": blocked,
    }


def average_duration(records):
    durations = []

    for record in records:
        start = record.get("start_seconds")
        end = record.get("end_seconds")

        try:
            start = float(start)
            end = float(end)
        except (TypeError, ValueError):
            continue

        duration = end - start

        if duration >= 0:
            durations.append(duration)

    if not durations:
        return None

    return sum(durations) / len(durations)


def _metric_table(
    records,
    key,
    category_name,
    preferred_order=None,
):
    rows = []

    for category in ordered_categories(
        records,
        key,
        preferred_order,
    ):
        subset = records_with_category(
            records,
            key,
            category,
        )

        m = outcome_metrics(subset)
        total = m["total"]

        rows.append(
            {
                category_name: category,
                "Attempts": total,
                "On Target": fmt_rate(
                    m["on_target"],
                    total,
                ),
                "Off Target": fmt_rate(
                    m["off_target"],
                    total,
                ),
                "Blocked": fmt_rate(
                    m["blocked"],
                    total,
                ),
                "On Target Rate": fmt_rate(
                    m["on_target"],
                    total,
                ),
                "_On Target %": rate(
                    m["on_target"],
                    total,
                ),
            }
        )

    return pd.DataFrame(rows)


def _display_df(df, first_column):
    if df.empty:
        st.info("No coded data available.")
        return

    visible = [
        column
        for column in df.columns
        if not column.startswith("_")
    ]

    st.dataframe(
        df[visible],
        hide_index=True,
        width="stretch",
        column_config={
            first_column:
                st.column_config.TextColumn(
                    first_column,
                    width="large",
                ),
            "Attempts":
                st.column_config.NumberColumn(
                    "Attempts",
                    width="small",
                ),
        },
    )


# ============================================================
# KEY KPIs
# ============================================================

def render_kpis(records, phase):
    m = outcome_metrics(records)
    total = m["total"]

    attack_type, attack_count = most_common(
        records,
        "attack_type",
    )
    time_period, time_count = most_common(
        records,
        "time_period",
    )
    final_zone, final_zone_count = most_common(
        records,
        "final_attempt_zone",
    )
    final_attempt_player, final_attempt_player_count = most_common(
        records,
        "final_attempt_player",
    )
    assist, assist_count = most_common(
        records,
        "assist",
    )

    duration = average_duration(records)

    st.markdown("### Key KPIs")

    cols = st.columns(5)

    cols[0].metric(
        "Final Attempts"
        if phase == "offensive"
        else "Final Attempts Faced",
        total,
    )

    cols[1].metric(
        "On Target",
        fmt_rate(
            m["on_target"],
            total,
        ),
    )

    cols[2].metric(
        "Off Target",
        fmt_rate(
            m["off_target"],
            total,
        ),
    )

    cols[3].metric(
        "Blocked",
        fmt_rate(
            m["blocked"],
            total,
        ),
    )

    cols[4].metric(
        "On Target Rate",
        fmt_rate(
            m["on_target"],
            total,
        ),
    )

    cols = st.columns(5)

    cols[0].metric(
        "Most Common Attack Type",
        attack_type,
        help=(
            f"{attack_count}/{total} attempts"
            if attack_type != "-"
            else None
        ),
    )

    cols[1].metric(
        "Most Common Period",
        time_period,
        help=(
            f"{time_count}/{total} attempts"
            if time_period != "-"
            else None
        ),
    )

    cols[2].metric(
        "Most Common Final Attempt Zone",
        final_zone,
        help=(
            f"{final_zone_count}/{total} attempts"
            if final_zone != "-"
            else None
        ),
    )

    cols[3].metric(
        "Most Common Final Attempt Player",
        final_attempt_player,
        help=(
            f"{final_attempt_player_count}/{total} attempts"
            if final_attempt_player != "-"
            else None
        ),
    )

    cols[4].metric(
        "Most Common Assist Player",
        assist,
        help=(
            f"{assist_count}/{total} attempts"
            if assist != "-"
            else None
        ),
    )

    if duration is not None:
        st.caption(
            f"Average coded event duration: "
            f"{duration:.1f} seconds."
        )


# ============================================================
# TIME PROFILE
# ============================================================

def render_time_profile(records):
    st.markdown("### Time Profile")

    rows = []

    for period in TIME_PERIODS:
        subset = records_with_category(
            records,
            "time_period",
            period,
        )

        m = outcome_metrics(subset)

        for outcome, key in [
            ("On Target", "on_target"),
            ("Off Target", "off_target"),
            ("Blocked", "blocked"),
        ]:
            rows.append(
                {
                    "Period": period,
                    "Outcome": outcome,
                    "Attempts": m[key],
                }
            )

    chart_df = pd.DataFrame(rows)

    fig = px.bar(
        chart_df,
        x="Period",
        y="Attempts",
        color="Outcome",
        barmode="stack",
        category_orders={
            "Period": TIME_PERIODS,
            "Outcome": [
                "On Target",
                "Off Target",
                "Blocked",
            ],
        },
        text="Attempts",
    )

    fig.update_traces(
        textposition="inside",
        hovertemplate=(
            "<b>%{x}</b><br>"
            "%{fullData.name}: %{y}"
            "<extra></extra>"
        ),
    )

    fig.update_layout(
        height=350,
        margin=dict(
            l=20,
            r=20,
            t=10,
            b=20,
        ),
        xaxis_title="Time Period",
        yaxis_title="Attempts",
        legend_title="",
    )

    st.plotly_chart(
        fig,
        width="stretch",
    )

    table = _metric_table(
        records,
        "time_period",
        "Period",
        TIME_PERIODS,
    )

    # Always show all six periods, including zero-event buckets.
    existing = {
        _norm(row["Period"]): row
        for row in table.to_dict("records")
    }

    completed_rows = []

    for period in TIME_PERIODS:
        row = existing.get(
            _norm(period)
        )

        if row is None:
            row = {
                "Period": period,
                "Attempts": 0,
                "On Target": "—",
                "Off Target": "—",
                "Blocked": "—",
                "On Target Rate": "—",
                "_On Target %": 0.0,
            }

        completed_rows.append(row)

    table = pd.DataFrame(completed_rows)

    _display_df(
        table,
        "Period",
    )


# ============================================================
# ATTACK TYPE
# ============================================================

def render_attack_type(records):
    st.markdown("### Attack Type")

    df = _metric_table(
        records,
        "attack_type",
        "Attack Type",
        ATTACK_TYPE_ORDER,
    )

    if df.empty:
        st.info(
            "No attack-type data available."
        )
        return

    chart_df = df[
        [
            "Attack Type",
            "Attempts",
        ]
    ].copy()

    fig = px.bar(
        chart_df,
        x="Attack Type",
        y="Attempts",
        text="Attempts",
    )

    fig.update_traces(
        textposition="outside",
    )

    fig.update_layout(
        height=300,
        margin=dict(
            l=20,
            r=20,
            t=10,
            b=20,
        ),
        xaxis_title="",
        yaxis_title="Attempts",
        showlegend=False,
    )

    st.plotly_chart(
        fig,
        width="stretch",
    )

    _display_df(
        df,
        "Attack Type",
    )


# ============================================================
# ORGANIZED ATTACK / CONTEXT
# ============================================================

def render_organized_attack(records):
    org_records = records_with_category(
        records,
        "attack_type",
        "ORG. ATTACK",
    )

    if not org_records:
        return

    st.markdown(
        "### Organized Attack Context"
    )

    st.markdown(
        "#### Type of Organized Attack"
    )

    df = _metric_table(
        org_records,
        "organized_attack_type",
        "Org. Attack Phase",
        ORG_ATTACK_ORDER,
    )

    _display_df(
        df,
        "Org. Attack Phase",
    )

    context_df = _metric_table(
        org_records,
        "attack_zone",
        "Block Context",
        [
            "LOW",
            "MID",
            "HIGH",
        ],
    )

    if not context_df.empty:
        st.markdown(
            "#### Organized Attack vs Block"
        )

        _display_df(
            context_df,
            "Block Context",
        )


def render_counter_context(records):
    counter_records = records_with_category(
        records,
        "attack_type",
        "COUNTER",
    )

    if not counter_records:
        return

    st.markdown(
        "### Counter Attack Context"
    )

    context_df = _metric_table(
        counter_records,
        "attack_zone",
        "Possession Won Context",
        [
            "LOW",
            "MID",
            "HIGH",
        ],
    )

    if not context_df.empty:
        _display_df(
            context_df,
            "Possession Won Context",
        )

    recovery_df = _metric_table(
        counter_records,
        "recovery_zone",
        "Recovery Zone",
        RECOVERY_ZONE_ORDER,
    )

    if not recovery_df.empty:
        st.markdown(
            "#### Recovery Zone Effectiveness"
        )

        _display_df(
            recovery_df,
            "Recovery Zone",
        )


# ============================================================
# SEQUENCE CONSTRUCTION
# ============================================================

def render_sequence_construction(
    records,
    analysis_scope,
):
    st.markdown(
        "### Sequence Construction"
    )

    st.markdown(
        "#### Number of Passes"
    )

    passes_df = _metric_table(
        records,
        "passes",
        "Pass Sequence",
        PASSES_ORDER,
    )

    if not passes_df.empty:
        if analysis_scope in {
            "Competition Analysis",
            "All Matches Analysis",
        }:
            fig = px.bar(
                passes_df,
                x="Pass Sequence",
                y="Attempts",
                text="Attempts",
            )

            fig.update_layout(
                height=300,
                margin=dict(
                    l=20,
                    r=20,
                    t=10,
                    b=20,
                ),
                xaxis_title="",
                yaxis_title="Attempts",
                showlegend=False,
            )

            fig.update_traces(
                textposition="outside",
            )

            st.plotly_chart(
                fig,
                width="stretch",
            )

        _display_df(
            passes_df,
            "Pass Sequence",
        )

    st.write("")

    st.markdown(
        "#### Chance Creation Method"
    )

    pass_type_df = _metric_table(
        records,
        "pass_type",
        "Assist / Pass Type",
        PASS_TYPE_ORDER,
    )

    _display_df(
        pass_type_df,
        "Assist / Pass Type",
    )

    st.write("")

    st.markdown(
        "#### Number of Touches"
    )

    touches_df = _metric_table(
        records,
        "touches",
        "Touches",
        TOUCHES_ORDER,
    )

    _display_df(
        touches_df,
        "Touches",
    )


# ============================================================
# SET PLAY ANALYSIS
# ============================================================

def render_set_plays(records):
    set_play_records = records_with_category(
        records,
        "attack_type",
        "SET PLAY",
    )

    if not set_play_records:
        return

    st.markdown(
        "### Set Play Contribution"
    )

    st.markdown(
        "#### Type of Set Play"
    )

    set_play_df = _metric_table(
        set_play_records,
        "set_play_type",
        "Set Play",
        SET_PLAY_ORDER,
    )

    _display_df(
        set_play_df,
        "Set Play",
    )

    corner_records = [
        record
        for record in set_play_records
        if _clean_values(
            record,
            "corner_kick_type",
        )
    ]

    if corner_records:
        st.markdown(
            "#### Type of Corner Kick"
        )

        corner_df = _metric_table(
            corner_records,
            "corner_kick_type",
            "Corner Type",
            [
                "DIRECT CROSS",
                "SHORT PASS",
                "2ND PHASE",
            ],
        )

        _display_df(
            corner_df,
            "Corner Type",
        )

    free_kick_records = [
        record
        for record in set_play_records
        if _clean_values(
            record,
            "free_kick_type",
        )
    ]

    if free_kick_records:
        st.markdown(
            "#### Type of Free Kick"
        )

        free_kick_df = _metric_table(
            free_kick_records,
            "free_kick_type",
            "Free Kick Type",
            [
                "DIRECT CROSS",
                "SHORT PASS",
                "2ND PHASE",
                "FK DIRECT CROSS",
            ],
        )

        _display_df(
            free_kick_df,
            "Free Kick Type",
        )


# ============================================================
# SPATIAL ANALYSIS
# ============================================================

def _zone_counts(records, key):
    return category_counts(
        records,
        key,
    )


def _heat_bg(
    count,
    max_count,
    palette,
):
    ratio = (
        0
        if max_count <= 0
        else count / max_count
    )

    if palette == "recovery":
        if count == 0:
            return "rgba(0, 74, 110, .24)"
        if ratio >= .75:
            return "rgba(0, 130, 190, .75)"
        if ratio >= .50:
            return "rgba(0, 112, 170, .62)"
        return "rgba(0, 95, 145, .48)"

    if palette == "assist":
        if count == 0:
            return "rgba(0, 80, 90, .22)"
        if ratio >= .75:
            return "rgba(0, 125, 135, .72)"
        if ratio >= .50:
            return "rgba(0, 105, 118, .58)"
        return "rgba(0, 90, 100, .45)"

    if count == 0:
        return "rgba(95, 10, 40, .22)"
    if ratio >= .75:
        return "rgba(175, 20, 70, .76)"
    if ratio >= .50:
        return "rgba(145, 16, 58, .62)"
    return "rgba(120, 12, 48, .48)"


def _tile(
    label,
    count,
    max_count,
    palette,
):
    return f"""
    <div
        class="zone-tile"
        style="background:{_heat_bg(count, max_count, palette)};"
    >
        <span>{label}</span>
        <strong>{count}</strong>
    </div>
    """


def _recovery_grid(counts):
    max_count = max(
        counts.values(),
        default=0,
    )

    cells = []

    for zone in RECOVERY_ZONE_ORDER:
        cells.append(
            _tile(
                zone.replace(
                    "Zone ",
                    "",
                ),
                counts.get(
                    zone,
                    0,
                ),
                max_count,
                "recovery",
            )
        )

    return "".join(cells)


def _color_zone_panel(
    counts,
    title,
    palette,
):
    # The source uses color-named zones.
    # We preserve those exact labels and place them in a stable
    # pitch-like grid without inventing football semantics.
    ordered = [
        "L BLUE",
        "L GREEN",
        "RED",
        "R GREEN",
        "R BLUE",
        "L GREY",
        "PINK",
        "R GREY",
        "ORANGE",
    ]

    normalized_counts = {
        _norm(key): value
        for key, value
        in counts.items()
    }

    unknown = [
        key
        for key
        in counts
        if _norm(key)
        not in {
            _norm(value)
            for value in ordered
        }
    ]

    max_count = max(
        counts.values(),
        default=0,
    )

    cells = []

    for label in ordered:
        cells.append(
            _tile(
                label,
                normalized_counts.get(
                    _norm(label),
                    0,
                ),
                max_count,
                palette,
            )
        )

    for label in unknown:
        cells.append(
            _tile(
                label,
                counts[label],
                max_count,
                palette,
            )
        )

    return f"""
    <div class="spatial-panel">
        <div class="spatial-title">
            {title}
        </div>
        <div class="colour-grid">
            {''.join(cells)}
        </div>
    </div>
    """


def render_spatial_analysis(records):
    st.markdown(
        "### Spatial Analysis"
    )

    recovery_counts = _zone_counts(
        records,
        "recovery_zone",
    )

    recovery_counts = {
        key: value
        for key, value
        in recovery_counts.items()
        if _norm(key) != "OTHER"
    }

    assist_counts = _zone_counts(
        records,
        "assist_zone",
    )

    assist_counts = {
        key: value
        for key, value
        in assist_counts.items()
        if _norm(key) != "OTHER"
    }

    final_counts = _zone_counts(
        records,
        "final_attempt_zone",
    )

    final_counts = {
        key: value
        for key, value
        in final_counts.items()
        if _norm(key) != "OTHER"
    }

    max_recovery = max(
        recovery_counts.values(),
        default=0,
    )

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
    background: #0d1117;
    color: #fff;
    font-family:
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        sans-serif;
}}

.spatial-shell {{
    width: 100%;
}}

.spatial-grid {{
    display: grid;
    grid-template-columns:
        1fr 1fr 1fr;
    gap: 14px;
}}

.spatial-panel {{
    min-width: 0;
}}

.spatial-title {{
    text-align: center;
    color: #c7f000;
    font-size: 12px;
    font-weight: 800;
    margin-bottom: 7px;
    text-transform: uppercase;
}}

.recovery-grid {{
    height: 330px;
    display: grid;
    grid-template-columns:
        repeat(3, 1fr);
    grid-template-rows:
        repeat(4, 1fr);
    border:
        2px solid
        rgba(255,255,255,.85);
    background:
        linear-gradient(
            180deg,
            #13313a 0%,
            #0e2530 100%
        );
}}

.colour-grid {{
    min-height: 330px;
    display: grid;
    grid-template-columns:
        repeat(3, 1fr);
    grid-auto-rows:
        minmax(76px, 1fr);
    gap: 2px;
    padding: 2px;
    border:
        2px solid
        rgba(255,255,255,.85);
    background:
        linear-gradient(
            180deg,
            #152029 0%,
            #101820 100%
        );
}}

.zone-tile {{
    min-width: 0;
    min-height: 0;
    border:
        1px solid
        rgba(255,255,255,.11);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 4px;
}}

.zone-tile span {{
    font-size: 10px;
    color:
        rgba(255,255,255,.72);
    line-height: 1.1;
}}

.zone-tile strong {{
    margin-top: 4px;
    font-size: 19px;
}}

@media (
    max-width: 1000px
) {{
    .spatial-grid {{
        grid-template-columns: 1fr;
    }}
}}

</style>
</head>

<body>

<div class="spatial-shell">

    <div class="spatial-grid">

        <div class="spatial-panel">
            <div class="spatial-title">
                Recovery Zones
            </div>

            <div class="recovery-grid">
                {_recovery_grid(
                    recovery_counts
                )}
            </div>
        </div>

        {_color_zone_panel(
            assist_counts,
            "Assist Zone",
            "assist",
        )}

        {_color_zone_panel(
            final_counts,
            "Final Attempt Zone",
            "final",
        )}

    </div>

</div>

</body>
</html>
"""

    st.iframe(
        html,
        width="stretch",
        height=385,
    )

    st.caption(
        "Zone labels are shown exactly as coded in Sportscode. "
        "The Assist and Final Attempt colour labels are not renamed "
        "into football areas until their template mapping is explicitly confirmed."
    )

    st.markdown(
        "#### Recovery Zone Effectiveness"
    )

    recovery_df = _metric_table(
        records,
        "recovery_zone",
        "Recovery Zone",
        RECOVERY_ZONE_ORDER,
    )

    _display_df(
        recovery_df,
        "Recovery Zone",
    )

    st.write("")

    st.markdown(
        "#### Assist Zone Effectiveness"
    )

    assist_df = _metric_table(
        records,
        "assist_zone",
        "Assist Zone",
    )

    _display_df(
        assist_df,
        "Assist Zone",
    )

    st.write("")

    st.markdown(
        "#### Final Attempt Zone Effectiveness"
    )

    final_df = _metric_table(
        records,
        "final_attempt_zone",
        "Final Attempt Zone",
    )

    _display_df(
        final_df,
        "Final Attempt Zone",
    )


# ============================================================
# PLAYER ANALYSIS
# ============================================================

def _player_table(
    records,
    key,
    player_column,
    metric_label,
):
    rows = []

    for player in ordered_categories(
        records,
        key,
    ):
        if _norm(player) == "OTHER":
            continue

        subset = records_with_category(
            records,
            key,
            player,
        )

        m = outcome_metrics(subset)
        total = m["total"]

        rows.append(
            {
                player_column: player,
                metric_label: total,
                "On Target": fmt_rate(
                    m["on_target"],
                    total,
                ),
                "Off Target": fmt_rate(
                    m["off_target"],
                    total,
                ),
                "Blocked": fmt_rate(
                    m["blocked"],
                    total,
                ),
                "On Target Rate": fmt_rate(
                    m["on_target"],
                    total,
                ),
            }
        )

    return pd.DataFrame(rows)


def render_players(records):
    st.markdown(
        "### Player Contribution"
    )

    st.markdown(
        "#### Final Attempt Player"
    )

    shooter_df = _player_table(
        records,
        "final_attempt_player",
        "Player",
        "Attempts",
    )

    _display_df(
        shooter_df,
        "Player",
    )

    st.write("")

    st.markdown(
        "#### Assist Player"
    )

    assist_df = _player_table(
        records,
        "assist",
        "Player",
        "Attempts Created",
    )

    _display_df(
        assist_df,
        "Player",
    )

    st.caption(
        "Attempts Created means final attempts following that player's assist action; "
        "it is not a goal-assist statistic."
    )

    st.write("")

    st.markdown(
        "#### Pre-Assist / 2nd Assist"
    )

    second_df = _player_table(
        records,
        "second_assist",
        "Player",
        "Sequences",
    )

    _display_df(
        second_df,
        "Player",
    )

    st.write("")

    st.markdown(
        "#### Recovery Player"
    )

    recovery_df = _player_table(
        records,
        "recovery_player",
        "Player",
        "Recoveries Leading to Attempt",
    )

    _display_df(
        recovery_df,
        "Player",
    )


# ============================================================
# AGGREGATED RELATIONSHIPS
# ============================================================

def render_relationships(
    records,
    analysis_scope,
):
    if analysis_scope not in {
        "Competition Analysis",
        "All Matches Analysis",
    }:
        return

    st.markdown(
        "### Advanced Relationships"
    )

    # --------------------------------------------------------
    # PLAYER CHAIN
    # --------------------------------------------------------

    chain_counter = Counter()

    for record in records:
        shooter = (
            _clean_values(
                record,
                "final_attempt_player",
            )
            or ["-"]
        )[0]

        assist = (
            _clean_values(
                record,
                "assist",
            )
            or ["-"]
        )[0]

        second = (
            _clean_values(
                record,
                "second_assist",
            )
            or ["-"]
        )[0]

        if (
            _norm(shooter) == "OTHER"
            and _norm(assist) == "OTHER"
            and _norm(second) == "OTHER"
        ):
            continue

        chain_counter[
            (
                second,
                assist,
                shooter,
            )
        ] += 1

    if chain_counter:
        st.markdown(
            "#### Pre-Assist → Assist → Final Attempt Player"
        )

        rows = []

        for (
            second,
            assist,
            final_attempt_player,
        ), count in (
            chain_counter
            .most_common()
        ):
            rows.append(
                {
                    "Pre-Assist":
                        second,
                    "Assist":
                        assist,
                    "Final Attempt Player":
                        final_attempt_player,
                    "Attempts":
                        count,
                }
            )

        st.dataframe(
            pd.DataFrame(rows),
            hide_index=True,
            width="stretch",
        )

    # --------------------------------------------------------
    # ASSIST ZONE -> FINAL ATTEMPT ZONE
    # --------------------------------------------------------

    relation_counter = Counter()

    for record in records:
        assist_zones = _clean_values(
            record,
            "assist_zone",
        )

        final_zones = _clean_values(
            record,
            "final_attempt_zone",
        )

        for assist_zone in assist_zones:
            for final_zone in final_zones:
                relation_counter[
                    (
                        assist_zone,
                        final_zone,
                    )
                ] += 1

    if relation_counter:
        st.markdown(
            "#### Assist Zone → Final Attempt Zone"
        )

        rows = []

        for (
            assist_zone,
            final_zone,
        ), count in (
            relation_counter
            .most_common()
        ):
            rows.append(
                {
                    "Assist Zone":
                        assist_zone,
                    "Final Attempt Zone":
                        final_zone,
                    "Attempts":
                        count,
                }
            )

        st.dataframe(
            pd.DataFrame(rows),
            hide_index=True,
            width="stretch",
        )


# ============================================================
# MAIN RENDERER
# ============================================================

def render_final_attempt_analysis(
    analysis: dict,
    phase: str | None = None,
    analysis_scope: str | None = None,
):
    records = analysis.get(
        "records",
        [],
    )

    if not records:
        st.info(
            "No Final Attempt events found "
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
        f"Final Attempts — {phase_title}"
    )

    render_kpis(
        records,
        phase,
    )

    st.markdown("---")

    render_time_profile(
        records,
    )

    st.markdown("---")

    render_attack_type(
        records,
    )

    render_organized_attack(
        records,
    )

    render_counter_context(
        records,
    )

    st.markdown("---")

    render_sequence_construction(
        records,
        analysis_scope,
    )

    st.markdown("---")

    render_set_plays(
        records,
    )

    st.markdown("---")

    render_spatial_analysis(
        records,
    )

    st.markdown("---")

    render_players(
        records,
    )

    render_relationships(
        records,
        analysis_scope,
    )


# Backward-compatible alias.
render_final_attempts_analysis = (
    render_final_attempt_analysis
)
