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

_ACTIVE_REPORT_CONTEXT = None

# Goal charts use a violet accent instead of red.
GOAL_CHART_COLOR = "#F5C400"


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
    "GOAL",
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
    "ZERO",
    "1-3",
    "4-5",
    "6-9",
    "10+",
]

PASSES_ALIASES = {
    "ZERO": [
        "ZERO",
        "0",
    ],
}

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
    "FREE KICK D",
    "CORNER KICK",
    "PENALTY KICK",
    "THROW IN",
]

SET_PLAY_ALIASES = {
    "FREE KICK C": [
        "FREE KICK C",
        "FREE KICK CROSS",
    ],
    "FREE KICK D": [
        "FREE KICK D",
        "FREE KICK DIRECT",
    ],
    "CORNER KICK": [
        "CORNER KICK",
    ],
    "PENALTY KICK": [
        "PENALTY KICK",
    ],
    "THROW IN": [
        "THROW IN",
    ],
}

CORNER_TYPE_ORDER = [
    "DIRECT CROSS",
    "SHORT PASS",
    "2ND PHASE",
]

CORNER_TYPE_ALIASES = {
    "DIRECT CROSS": [
        "DIRECT CROSS",
    ],
    "SHORT PASS": [
        "SHORT PASS",
    ],
    "2ND PHASE": [
        "2ND PHASE",
    ],
}

FREE_KICK_TYPE_ORDER = [
    "FK DIRECT CROSS",
    "FK SHORT PASS",
    "FK 2ND PHASE",
]

FREE_KICK_TYPE_ALIASES = {
    "FK DIRECT CROSS": [
        "FK DIRECT CROSS",
        "DIRECT CROSS",
    ],
    "FK SHORT PASS": [
        "FK SHORT PASS",
        "SHORT PASS",
    ],
    "FK 2ND PHASE": [
        "FK 2ND PHASE",
        "2ND PHASE",
    ],
}

PASS_TYPE_ORDER = [
    "PASS",
    "CROSS",
    "VERTICAL",
    "CUTBACK",
    "BEHIND OPP LINE",
]


FINAL_ATTEMPT_INSIDE_BOX_ZONES = {
    "L GREEN",
    "R GREEN",
    "RED",
    "ORANGE",
    "YELLOW",
}

FINAL_ATTEMPT_OUTSIDE_BOX_ZONES = {
    "L BLUE",
    "R BLUE",
    "PINK",
    "L GREY",
    "R GREY",
}

BOX_LOCATION_ORDER = [
    "Inside Box",
    "Outside Box",
]


SET_PLAY_DISPLAY_NAMES = {
    "FREE KICK C": "Free Kick Cross",
    "FREE KICK CROSS": "Free Kick Cross",
    "FREE KICK D": "Free Kick Direct",
    "FREE KICK DIRECT": "Free Kick Direct",
    "CORNER KICK": "Corner Kick",
    "PENALTY KICK": "Penalty Kick",
    "THROW IN": "Throw In",
}

CORNER_TYPE_DISPLAY_NAMES = {
    "DIRECT CROSS": "Direct Cross",
    "SHORT PASS": "Short Pass",
    "2ND PHASE": "2nd Phase",
}

PASS_SEQUENCE_DISPLAY_NAMES = {
    "ZERO": "Zero",
    "0": "Zero",
}


FREE_KICK_TYPE_DISPLAY_NAMES = {
    "FK DIRECT CROSS": "Direct Cross",
    "DIRECT CROSS": "Direct Cross",
    "FK SHORT PASS": "Short Pass",
    "SHORT PASS": "Short Pass",
    "FK 2ND PHASE": "2nd Phase",
    "2ND PHASE": "2nd Phase",
}


def _set_play_display_name(value):
    normalized = _norm(value)
    return SET_PLAY_DISPLAY_NAMES.get(
        normalized,
        value,
    )


def _corner_type_display_name(value):
    normalized = _norm(value)
    return CORNER_TYPE_DISPLAY_NAMES.get(
        normalized,
        value,
    )


def _free_kick_type_display_name(value):
    normalized = _norm(value)
    return FREE_KICK_TYPE_DISPLAY_NAMES.get(
        normalized,
        value,
    )


def _pass_sequence_display_name(value):
    normalized = _norm(value)
    return PASS_SEQUENCE_DISPLAY_NAMES.get(
        normalized,
        value,
    )


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


def get_final_attempt_box_location(record):
    """
    Derive Inside Box / Outside Box from the Sportscode
    Final Attempt colour-zone coding used by the spatial report.
    """
    zones = {
        _norm(value)
        for value in _clean_values(
            record,
            "final_attempt_zone",
        )
    }

    if zones & FINAL_ATTEMPT_INSIDE_BOX_ZONES:
        return "Inside Box"

    if zones & FINAL_ATTEMPT_OUTSIDE_BOX_ZONES:
        return "Outside Box"

    return None


def add_final_attempt_box_location(records):
    """Add the derived box-location field in-place and return records."""
    for record in records:
        box_location = get_final_attempt_box_location(record)
        if box_location is not None:
            record["final_attempt_box_location"] = box_location
        else:
            record.pop("final_attempt_box_location", None)

    return records


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

    on_target = count_value(records, "outcome", "ON TARGET")
    off_target = count_value(records, "outcome", "OFF TARGET")
    blocked = count_value(records, "outcome", "BLOCKED")
    goals = count_value(records, "outcome", "GOAL")

    return {
        "total": total,
        "on_target": on_target,
        "off_target": off_target,
        "blocked": blocked,
        "goals": goals,
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
    category_aliases=None,
):
    rows = []

    present_categories = list(category_counts(records, key).keys())
    categories = (
        list(preferred_order)
        if preferred_order
        else ordered_categories(records, key)
    )
    matched_present = set()

    def build_row(category, subset):
        m = outcome_metrics(subset)
        total = m["total"]
        return {
            category_name: category,
            "Attempts": total,
            "On Target": fmt_rate(m["on_target"], total),
            "Off Target": fmt_rate(m["off_target"], total),
            "Blocked": fmt_rate(m["blocked"], total),
            "Goals": m["goals"],
            "Goal Conversion": fmt_rate(m["goals"], total),
            "On Target Conversion": fmt_rate(m["goals"], m["on_target"]),
            "_On Target %": rate(m["on_target"], total),
            "_Off Target %": rate(m["off_target"], total),
            "_Blocked %": rate(m["blocked"], total),
            "_Goal %": rate(m["goals"], total),
            "_On Target Count": m["on_target"],
            "_Off Target Count": m["off_target"],
            "_Blocked Count": m["blocked"],
            "_Goal Count": m["goals"],
        }

    for category in categories:
        alias_values = (
            category_aliases.get(category, [category])
            if category_aliases
            else [category]
        )
        normalized_aliases = {_norm(value) for value in alias_values}

        subset = [
            record
            for record in records
            if any(event_has_value(record, key, alias) for alias in alias_values)
        ]

        for present in present_categories:
            if _norm(present) in normalized_aliases:
                matched_present.add(_norm(present))

        rows.append(build_row(category, subset))

    if preferred_order:
        for present in present_categories:
            if _norm(present) in matched_present:
                continue
            subset = records_with_category(records, key, present)
            rows.append(build_row(present, subset))

    return pd.DataFrame(rows)

def _display_df(
    df,
    first_column,
    report_section_title: str | None = None,
    report_key: str | None = None,
):
    if df.empty:
        st.info("No coded data available.")
        return

    visible = [c for c in df.columns if not c.startswith("_")]
    display_df = df[visible].copy()
    st.dataframe(
        display_df,
        hide_index=True,
        width="stretch",
        column_config={
            first_column: st.column_config.TextColumn(first_column, width="large"),
            "Attempts": st.column_config.NumberColumn("Attempts", width="small"),
        },
    )

    if _ACTIVE_REPORT_CONTEXT is not None:
        titles = {
            "Period": "Time Profile — Table",
            "Attack Type": "Attack Type — Table",
            "Org. Attack Phase": "Type of Organized Attack — Table",
            "Block Context": "Organized Attack vs Block — Table",
            "Possession Won Context": "Counter Attack Context — Table",
            "Recovery Zone": "Recovery Zone Effectiveness — Table",
            "Pass Sequence": "Number of Passes — Table",
            "Assist / Pass Type": "Chance Creation Method — Table",
            "Touches": "Number of Touches — Table",
            "Set Play": "Type of Set Play — Table",
            "Corner Type": "Type of Corner Kick — Table",
            "Free Kick Type": "Type of Free Kick — Table",
            "Assist Zone": "Assist Zone Effectiveness",
            "Final Attempt Zone": "Final Attempt Zone Effectiveness",
            "Player": "Player Contribution",
        }
        item=create_table_report_item(
            module="final_attempt",
            section_title=report_section_title or titles.get(first_column, f"{first_column} — Table"),
            dataframe=display_df,
            context=_ACTIVE_REPORT_CONTEXT,
        )
        render_add_to_report_button(
            item,
            key=f"report_final_attempt_table_{report_key or first_column}_{item['id']}",
        )


def _metric_chart_long_df(
    df,
    category_col,
    metrics=None,
):
    if metrics is None:
        metrics = [
            "On Target",
            "Off Target",
            "Blocked",
            "Goals",
        ]

    metric_map = {
        "On Target": ("_On Target %", "_On Target Count"),
        "Off Target": ("_Off Target %", "_Off Target Count"),
        "Blocked": ("_Blocked %", "_Blocked Count"),
        "Goals": ("_Goal %", "_Goal Count"),
    }

    rows = []
    for _, row in df.iterrows():
        attempts = int(row.get("Attempts", 0))
        for metric in metrics:
            pct_col, count_col = metric_map[metric]
            pct = float(row.get(pct_col, 0.0))
            count = int(row.get(count_col, 0))
            label = "—" if attempts == 0 else f"{pct:.0f}% ({count}/{attempts})"
            rows.append(
                {
                    category_col: row[category_col],
                    "Metric": metric,
                    "Rate": pct,
                    "Attempts": attempts,
                    "Count": count,
                    "Label": label,
                }
            )

    return pd.DataFrame(rows)

def render_metric_chart(
    df,
    category_col,
    metrics=None,
    height=None,
    report_section_title: str | None = None,
    report_key: str | None = None,
):
    if df.empty:
        return

    if metrics is None:
        metrics = [
            "On Target",
            "Off Target",
            "Blocked",
            "Goals",
        ]

    chart_df = (
        _metric_chart_long_df(
            df,
            category_col,
            metrics,
        )
    )

    if chart_df.empty:
        return

    categories = (
        df[category_col]
        .tolist()
    )

    use_horizontal = (
        len(categories) > 5
        or max(
            (
                len(str(value))
                for value
                in categories
            ),
            default=0,
        ) > 16
    )

    if use_horizontal:
        fig = px.bar(
            chart_df,
            x="Rate",
            y=category_col,
            color="Metric",
            text="Label",
            orientation="h",
            barmode="group",
            category_orders={
                category_col:
                    categories[::-1],
                "Metric":
                    metrics,
            },
        )

        for trace in fig.data:
            if trace.name == "Goals":
                trace.update(
                    marker_color=GOAL_CHART_COLOR
                )

        fig.update_traces(
            textposition="outside",
            cliponaxis=False,
            hovertemplate=(
                "<b>%{y}</b><br>"
                "%{fullData.name}: "
                "%{text}"
                "<extra></extra>"
            ),
        )

        fig.update_layout(
            height=(
                height
                or max(
                    320,
                    len(categories) * 58,
                )
            ),
            margin=dict(
                l=20,
                r=45,
                t=10,
                b=20,
            ),
            xaxis_title="Rate (%)",
            yaxis_title="",
            xaxis=dict(
                range=[
                    0,
                    110,
                ]
            ),
            legend_title_text="",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
            ),
        )

    else:
        fig = px.bar(
            chart_df,
            x=category_col,
            y="Rate",
            color="Metric",
            text="Label",
            barmode="group",
            category_orders={
                category_col:
                    categories,
                "Metric":
                    metrics,
            },
        )

        for trace in fig.data:
            if trace.name == "Goals":
                trace.update(
                    marker_color=GOAL_CHART_COLOR
                )

        fig.update_traces(
            textposition="outside",
            cliponaxis=False,
            hovertemplate=(
                "<b>%{x}</b><br>"
                "%{fullData.name}: "
                "%{text}"
                "<extra></extra>"
            ),
        )

        fig.update_layout(
            height=(
                height
                or 310
            ),
            margin=dict(
                l=20,
                r=20,
                t=10,
                b=20,
            ),
            xaxis_title="",
            yaxis_title="Rate (%)",
            yaxis=dict(
                range=[
                    0,
                    110,
                ]
            ),
            legend_title_text="",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
            ),
        )

    st.plotly_chart(
        fig,
        width="stretch",
    )

    if _ACTIVE_REPORT_CONTEXT is not None:
        titles={
            "Org. Attack Phase": "Type of Organized Attack",
            "Block Context": "Organized Attack vs Block",
            "Possession Won Context": "Counter Attack Context",
            "Recovery Zone": "Recovery Zone Effectiveness",
            "Pass Sequence": "Number of Passes",
            "Assist / Pass Type": "Chance Creation Method",
            "Touches": "Number of Touches",
            "Set Play": "Type of Set Play",
            "Corner Type": "Type of Corner Kick",
            "Free Kick Type": "Type of Free Kick",
        }
        item=create_plotly_report_item(
            module="final_attempt",
            section_title=report_section_title or titles.get(category_col, category_col),
            figure=fig,
            context=_ACTIVE_REPORT_CONTEXT,
        )
        render_add_to_report_button(
            item,
            key=f"report_final_attempt_chart_{report_key or category_col}_{item['id']}",
        )


# ============================================================
# KEY KPIs
# ============================================================

def render_kpis(records, phase):
    m = outcome_metrics(records)
    total = m["total"]

    attack_type, attack_count = most_common(records, "attack_type")
    time_period, time_count = most_common(records, "time_period")
    final_attempt_player, final_attempt_player_count = most_common(
        records,
        "final_attempt_player",
    )
    assist, assist_count = most_common(records, "assist")

    goal_records = [
        record
        for record in records
        if event_has_value(record, "outcome", "GOAL")
    ]
    top_goal_player, top_goal_player_count = most_common(
        goal_records,
        "final_attempt_player",
    )
    goal_period, goal_period_count = most_common(
        goal_records,
        "time_period",
    )

    goal_label = "Goals" if phase == "offensive" else "Goals Conceded"
    conversion_label = (
        "Goal Conversion"
        if phase == "offensive"
        else "Goal Conceded Conversion"
    )
    on_target_conversion_label = (
        "On Target Conversion"
        if phase == "offensive"
        else "On Target Conceded Conversion"
    )
    top_goal_player_label = (
        "Top Scorer"
        if phase == "offensive"
        else "Most Common Scorer Against"
    )

    st.markdown("### KPIs Overview")

    cols = st.columns(4)
    cols[0].metric(
        "Final Attempts" if phase == "offensive" else "Final Attempts Faced",
        total,
    )
    cols[1].metric("On Target", fmt_rate(m["on_target"], total))
    cols[2].metric("Off Target", fmt_rate(m["off_target"], total))
    cols[3].metric("Blocked", fmt_rate(m["blocked"], total))

    cols = st.columns(4)
    cols[0].metric(goal_label, m["goals"])
    cols[1].metric(conversion_label, fmt_rate(m["goals"], total))
    cols[2].metric(
        on_target_conversion_label,
        fmt_rate(m["goals"], m["on_target"]),
    )
    cols[3].metric(
        top_goal_player_label,
        top_goal_player,
        help=(
            f"{top_goal_player_count}/{m['goals']} goals"
            if top_goal_player != "-" and m["goals"]
            else None
        ),
    )

    cols = st.columns(5)
    cols[0].metric(
        "Most Common Attack Type",
        attack_type,
        help=f"{attack_count}/{total} attempts" if attack_type != "-" else None,
    )
    cols[1].metric(
        "Most Common Final Attempt Period",
        time_period,
        help=f"{time_count}/{total} attempts" if time_period != "-" else None,
    )
    cols[2].metric(
        "Most Common Goal Period",
        goal_period,
        help=(
            f"{goal_period_count}/{m['goals']} goals"
            if goal_period != "-" and m["goals"]
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
        help=f"{assist_count}/{total} attempts" if assist != "-" else None,
    )

    if _ACTIVE_REPORT_CONTEXT is not None:
        item = create_kpi_report_item(
            module="final_attempt",
            section_title="KPIs Overview",
            kpis=[
                {
                    "label": "Final Attempts" if phase == "offensive" else "Final Attempts Faced",
                    "value": total,
                },
                {"label": "On Target", "value": fmt_rate(m["on_target"], total)},
                {"label": "Off Target", "value": fmt_rate(m["off_target"], total)},
                {"label": "Blocked", "value": fmt_rate(m["blocked"], total)},
                {"label": goal_label, "value": m["goals"]},
                {"label": conversion_label, "value": fmt_rate(m["goals"], total)},
                {
                    "label": on_target_conversion_label,
                    "value": fmt_rate(m["goals"], m["on_target"]),
                },
                {"label": top_goal_player_label, "value": top_goal_player},
                {"label": "Most Common Attack Type", "value": attack_type},
                {"label": "Most Common Final Attempt Period", "value": time_period},
                {"label": "Most Common Goal Period", "value": goal_period},
                {"label": "Most Common Final Attempt Player", "value": final_attempt_player},
                {"label": "Most Common Assist Player", "value": assist},
            ],
            context=_ACTIVE_REPORT_CONTEXT,
        )
        render_add_to_report_button(
            item,
            key=f"report_final_attempt_kpis_{item['id']}",
        )

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

    if _ACTIVE_REPORT_CONTEXT is not None:
        item=create_plotly_report_item(module="final_attempt",section_title="Time Profile",figure=fig,context=_ACTIVE_REPORT_CONTEXT)
        render_add_to_report_button(item,key=f"report_final_attempt_time_{item['id']}")

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
                "Goals": 0,
                "Goal Conversion": "—",
                "On Target Conversion": "—",
                "_On Target %": 0.0,
                "_Off Target %": 0.0,
                "_Blocked %": 0.0,
                "_Goal %": 0.0,
                "_On Target Count": 0,
                "_Off Target Count": 0,
                "_Blocked Count": 0,
                "_Goal Count": 0,
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

    if _ACTIVE_REPORT_CONTEXT is not None:
        item=create_plotly_report_item(module="final_attempt",section_title="Attack Type",figure=fig,context=_ACTIVE_REPORT_CONTEXT)
        render_add_to_report_button(item,key=f"report_final_attempt_attack_{item['id']}")

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

    if not df.empty:
        render_metric_chart(
            df,
            "Org. Attack Phase",
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

        render_metric_chart(
            context_df,
            "Block Context",
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
        render_metric_chart(
            context_df,
            "Possession Won Context",
        )

        _display_df(
            context_df,
            "Possession Won Context",
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
        PASSES_ALIASES,
    )

    if not passes_df.empty:
        passes_df = passes_df.copy()
        passes_df["Pass Sequence"] = (
            passes_df["Pass Sequence"]
            .map(_pass_sequence_display_name)
        )

        render_metric_chart(
            passes_df,
            "Pass Sequence",
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

    if not pass_type_df.empty:
        render_metric_chart(
            pass_type_df,
            "Assist / Pass Type",
            height=max(
                320,
                len(pass_type_df) * 52,
            ),
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

    if not touches_df.empty:
        render_metric_chart(
            touches_df,
            "Touches",
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
        SET_PLAY_ALIASES,
    )

    if not set_play_df.empty:
        set_play_df = set_play_df.copy()
        set_play_df["Set Play"] = (
            set_play_df["Set Play"]
            .map(_set_play_display_name)
        )
        render_metric_chart(
            set_play_df,
            "Set Play",
            height=max(
                320,
                len(set_play_df) * 52,
            ),
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
            CORNER_TYPE_ORDER,
            CORNER_TYPE_ALIASES,
        )

        if not corner_df.empty:
            corner_df = corner_df.copy()
            corner_df["Corner Type"] = (
                corner_df["Corner Type"]
                .map(_corner_type_display_name)
            )

            render_metric_chart(
                corner_df,
                "Corner Type",
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
            FREE_KICK_TYPE_ORDER,
            FREE_KICK_TYPE_ALIASES,
        )

        if not free_kick_df.empty:
            free_kick_df = free_kick_df.copy()
            free_kick_df["Free Kick Type"] = (
                free_kick_df["Free Kick Type"]
                .map(_free_kick_type_display_name)
            )

            render_metric_chart(
                free_kick_df,
                "Free Kick Type",
            )

            _display_df(
                free_kick_df,
                "Free Kick Type",
            )


# ============================================================
# GOAL ANALYSIS
# ============================================================

def _goal_breakdown_table(
    records,
    key,
    category_name,
    preferred_order=None,
    display_name_fn=None,
):
    goal_records = [
        record
        for record in records
        if event_has_value(record, "outcome", "GOAL")
    ]

    categories = ordered_categories(goal_records, key, preferred_order)
    rows = []

    for category in categories:
        goal_subset = records_with_category(goal_records, key, category)
        attempt_subset = records_with_category(records, key, category)
        label = display_name_fn(category) if display_name_fn else category
        rows.append(
            {
                category_name: label,
                "Goals": len(goal_subset),
                "Attempts": len(attempt_subset),
                "Conversion": fmt_rate(len(goal_subset), len(attempt_subset)),
            }
        )

    return pd.DataFrame(rows)


def _render_goal_breakdown(
    records,
    key,
    category_name,
    title,
    preferred_order=None,
    display_name_fn=None,
    report_key=None,
):
    df = _goal_breakdown_table(
        records,
        key,
        category_name,
        preferred_order,
        display_name_fn,
    )

    if df.empty:
        return

    st.markdown(f"#### {title}")

    fig = px.bar(
        df,
        x=category_name,
        y="Goals",
        text="Goals",
        hover_data={"Attempts": True, "Conversion": True},
    )
    fig.update_traces(
        textposition="outside",
        cliponaxis=False,
        marker_color=GOAL_CHART_COLOR,
    )
    fig.update_layout(
        height=310,
        margin=dict(l=20, r=20, t=10, b=20),
        xaxis_title="",
        yaxis_title="Goals",
        showlegend=False,
    )
    st.plotly_chart(
        fig,
        width="stretch",
    )

    if _ACTIVE_REPORT_CONTEXT is not None:
        chart_item = create_plotly_report_item(
            module="final_attempt",
            section_title=title,
            figure=fig,
            context=_ACTIVE_REPORT_CONTEXT,
        )
        render_add_to_report_button(
            chart_item,
            key=f"report_final_attempt_goal_chart_{report_key or key}_{chart_item['id']}",
        )

    st.dataframe(
        df,
        hide_index=True,
        width="stretch",
    )

    if _ACTIVE_REPORT_CONTEXT is not None:
        table_item = create_table_report_item(
            module="final_attempt",
            section_title=f"{title} — Table",
            dataframe=df,
            context=_ACTIVE_REPORT_CONTEXT,
        )
        render_add_to_report_button(
            table_item,
            key=f"report_final_attempt_goal_table_{report_key or key}_{table_item['id']}",
        )


def render_goal_analysis(records, phase):
    """Render only the high-level goal summary.

    Goal breakdowns are intentionally rendered next to the matching
    attempt analysis later in the page so every variable reads as:
    attempts first, goals second.
    """
    goal_records = [
        record
        for record in records
        if event_has_value(record, "outcome", "GOAL")
    ]

    title = "Goal Analysis" if phase == "offensive" else "Goals Conceded Analysis"
    st.markdown(f"### {title}")

    if not goal_records:
        st.info("No goals coded in the currently filtered Final Attempt events.")
        return

    total = len(records)
    on_target = count_value(records, "outcome", "ON TARGET")
    goal_period, goal_period_count = most_common(goal_records, "time_period")

    cols = st.columns(4)
    cols[0].metric(
        "Goals" if phase == "offensive" else "Goals Conceded",
        len(goal_records),
    )
    cols[1].metric(
        "Goal Conversion" if phase == "offensive" else "Goal Conceded Conversion",
        fmt_rate(len(goal_records), total),
    )
    cols[2].metric(
        "On Target Conversion" if phase == "offensive" else "On Target Conceded Conversion",
        fmt_rate(len(goal_records), on_target),
    )
    cols[3].metric(
        "Most Common Goal Period",
        goal_period,
        help=(
            f"{goal_period_count}/{len(goal_records)} goals"
            if goal_period != "-"
            else None
        ),
    )

    st.caption(
        "GOAL is an additional outcome flag on the same Final Attempt event and does not increase the Final Attempt count."
    )


def render_goal_breakdown_for_variable(
    records,
    key,
    category_name,
    title,
    preferred_order=None,
    display_name_fn=None,
    report_key=None,
):
    """Render the goal view immediately after the matching attempt view."""
    _render_goal_breakdown(
        records,
        key,
        category_name,
        title,
        preferred_order,
        display_name_fn,
        report_key,
    )


# ============================================================
# SPATIAL ANALYSIS
# ============================================================

def _zone_counts(records, key):
    return category_counts(
        records,
        key,
    )


def _normalized_count_map(counts):
    return {
        _norm(key): value
        for key, value
        in counts.items()
        if _norm(key) != "OTHER"
    }


def _zone_count(
    normalized_counts,
    label,
):
    return normalized_counts.get(
        _norm(label),
        0,
    )


def _report_colour_zone_counts(
    records,
    key,
):
    counts = _normalized_count_map(
        _zone_counts(
            records,
            key,
        )
    )

    return {
        "L BLUE":
            _zone_count(
                counts,
                "L BLUE",
            ),
        "L GREEN":
            _zone_count(
                counts,
                "L GREEN",
            ),
        "RED":
            _zone_count(
                counts,
                "RED",
            ),
        "ORANGE":
            _zone_count(
                counts,
                "ORANGE",
            ),
        "YELLOW":
            _zone_count(
                counts,
                "YELLOW",
            ),
        "R GREEN":
            _zone_count(
                counts,
                "R GREEN",
            ),
        "R BLUE":
            _zone_count(
                counts,
                "R BLUE",
            ),
        "PINK":
            _zone_count(
                counts,
                "PINK",
            ),
        "L GREY":
            _zone_count(
                counts,
                "L GREY",
            ),
        "R GREY":
            _zone_count(
                counts,
                "R GREY",
            ),
    }


def _inside_outside_box_counts(
    colour_counts,
):
    # This follows the exact visual logic in the Sportscode
    # Final Attempts report:
    #
    # Inside box:
    #   L GREEN, R GREEN, RED, ORANGE, YELLOW
    #
    # Outside box:
    #   L BLUE, R BLUE, PINK, L GREY, R GREY
    #
    # This mapping is supported directly by the report totals.
    inside_labels = FINAL_ATTEMPT_INSIDE_BOX_ZONES
    outside_labels = FINAL_ATTEMPT_OUTSIDE_BOX_ZONES

    inside = sum(
        colour_counts.get(
            label,
            0,
        )
        for label
        in inside_labels
    )

    outside = sum(
        colour_counts.get(
            label,
            0,
        )
        for label
        in outside_labels
    )

    return inside, outside


def _report_recovery_panel(
    counts,
):
    normalized = _normalized_count_map(
        counts
    )

    def c(label):
        return _zone_count(
            normalized,
            label,
        )

    total = sum(
        c(zone)
        for zone
        in RECOVERY_ZONE_ORDER
    )

    return f"""
    <div class="report-panel">
        <div class="report-title-row">
            <span class="report-title">
                Recovery zones (Transition phase)
            </span>
            <span class="report-total">
                {total}
            </span>
        </div>

        <div class="recovery-layout">

            <div class="sector-labels">
                <div>
                    Offensive<br>
                    sector
                    <strong>
                        {
                            c("Zone O3")
                            + c("Zone O2")
                            + c("Zone O1")
                        }
                    </strong>
                </div>

                <div>
                    Pre-<br>
                    Offensive<br>
                    sector
                    <strong>
                        {
                            c("Zone PO3")
                            + c("Zone PO2")
                            + c("Zone PO1")
                        }
                    </strong>
                </div>

                <div>
                    Pre-<br>
                    Defensive<br>
                    sector
                    <strong>
                        {
                            c("Zone PD3")
                            + c("Zone PD2")
                            + c("Zone PD1")
                        }
                    </strong>
                </div>

                <div>
                    Defensive<br>
                    sector
                    <strong>
                        {
                            c("Zone D3")
                            + c("Zone D2")
                            + c("Zone D1")
                        }
                    </strong>
                </div>
            </div>

            <div class="recovery-pitch">

                <div class="recovery-row recovery-o">
                    <div>
                        <span>Zone O3</span>
                        <strong>{c("Zone O3")}</strong>
                    </div>
                    <div>
                        <span>Zone O2</span>
                        <strong>{c("Zone O2")}</strong>
                    </div>
                    <div>
                        <span>Zone O1</span>
                        <strong>{c("Zone O1")}</strong>
                    </div>
                </div>

                <div class="recovery-row recovery-po">
                    <div>
                        <span>Zone PO3</span>
                        <strong>{c("Zone PO3")}</strong>
                    </div>
                    <div>
                        <span>Zone PO2</span>
                        <strong>{c("Zone PO2")}</strong>
                    </div>
                    <div>
                        <span>Zone PO1</span>
                        <strong>{c("Zone PO1")}</strong>
                    </div>
                </div>

                <div class="recovery-row recovery-pd">
                    <div>
                        <span>Zone PD3</span>
                        <strong>{c("Zone PD3")}</strong>
                    </div>
                    <div>
                        <span>Zone PD2</span>
                        <strong>{c("Zone PD2")}</strong>
                    </div>
                    <div>
                        <span>Zone PD1</span>
                        <strong>{c("Zone PD1")}</strong>
                    </div>
                </div>

                <div class="recovery-row recovery-d">
                    <div>
                        <span>Zone D3</span>
                        <strong>{c("Zone D3")}</strong>
                    </div>
                    <div>
                        <span>Zone D2</span>
                        <strong>{c("Zone D2")}</strong>
                    </div>
                    <div>
                        <span>Zone D1</span>
                        <strong>{c("Zone D1")}</strong>
                    </div>
                </div>

                <div class="recovery-centre-circle"></div>
                <div class="recovery-bottom-box"></div>
                <div class="recovery-bottom-goal"></div>

            </div>

            <div class="attack-arrow recovery-arrow">
                <div class="arrow-head"></div>
                <div class="arrow-body"></div>
            </div>

        </div>
    </div>
    """


def _report_half_pitch_panel(
    records,
    key,
    title,
):
    counts = _report_colour_zone_counts(
        records,
        key,
    )

    total = sum(
        counts.values()
    )

    inside, outside = (
        _inside_outside_box_counts(
            counts
        )
    )

    return f"""
    <div class="report-panel">

        <div class="report-title-row">
            <span class="report-title">
                {title}
            </span>
            <span class="report-total">
                {total}
            </span>
        </div>

        <div class="half-pitch-wrap">

            <div class="half-pitch">

                <!--
                    SPORTSCODE COLOUR ZONES
                    -----------------------
                    Wide channels:
                    L BLUE / R BLUE

                    Inside-box zones:
                    L GREEN / R GREEN /
                    RED / ORANGE / YELLOW

                    Central outside-box strip:
                    PINK

                    Deeper outside-box zones:
                    L GREY / R GREY
                -->

                <div class="zone l-blue">
                    <strong>
                        {counts["L BLUE"]}
                    </strong>
                </div>

                <div class="zone r-blue">
                    <strong>
                        {counts["R BLUE"]}
                    </strong>
                </div>

                <div class="zone l-green">
                    <strong>
                        {counts["L GREEN"]}
                    </strong>
                </div>

                <div class="zone r-green">
                    <strong>
                        {counts["R GREEN"]}
                    </strong>
                </div>

                <div class="zone red-zone">
                    <strong>
                        {counts["RED"]}
                    </strong>
                </div>

                <div class="zone orange-zone">
                    <strong>
                        {counts["ORANGE"]}
                    </strong>
                </div>

                <div class="zone yellow-zone">
                    <strong>
                        {counts["YELLOW"]}
                    </strong>
                </div>

                <div class="zone pink-zone">
                    <strong>
                        {counts["PINK"]}
                    </strong>
                </div>

                <div class="zone l-grey">
                    <strong>
                        {counts["L GREY"]}
                    </strong>
                </div>

                <div class="zone r-grey">
                    <strong>
                        {counts["R GREY"]}
                    </strong>
                </div>

                <!-- Pitch markings -->
                <div class="top-box-line"></div>
                <div class="top-semicircle"></div>

                <div class="centre-line"></div>
                <div class="centre-circle"></div>

                <div class="bottom-penalty-box"></div>
                <div class="bottom-goal-box"></div>
                <div class="bottom-semicircle"></div>

            </div>

            <div class="attack-arrow half-pitch-arrow">
                <div class="arrow-head"></div>
                <div class="arrow-body"></div>
            </div>

        </div>

        <div class="box-summary">
            <div>
                <span>Inside box</span>
                <strong>{inside}</strong>
            </div>

            <div>
                <span>Outside box</span>
                <strong>{outside}</strong>
            </div>
        </div>

    </div>
    """


def _get_spatial_css():
    return f"""
* {{
    box-sizing: border-box;
}}

html,
body {{
    margin: 0;
    padding: 0;
    background: #0d1117;
    color: #f4f4f4;
    font-family:
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        sans-serif;
}}

body {{
    overflow-x: hidden;
}}

.spatial-report-shell {{
    width: 100%;
    padding:
        2px 4px
        8px 4px;
}}

.spatial-report-grid {{
    display: grid;
    grid-template-columns:
        1fr 1fr 1fr;
    gap: 18px;
    align-items: start;
}}

.report-panel {{
    width: 100%;
    min-width: 0;
}}

.report-title-row {{
    height: 30px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    margin-bottom: 5px;
}}

.report-title {{
    color: #f3f3f3;
    font-size: 12px;
    font-weight: 700;
    text-align: center;
}}

.report-total {{
    color: #ff4545;
    font-size: 12px;
    font-weight: 800;
}}


/* ==========================================================
   RECOVERY ZONES
   ========================================================== */

.recovery-layout {{
    display: grid;
    grid-template-columns:
        66px
        minmax(0, 1fr)
        24px;
    gap: 7px;
    align-items: stretch;
}}

.sector-labels {{
    height: 348px;
    display: grid;
    grid-template-rows:
        repeat(4, 1fr);
}}

.sector-labels > div {{
    display: flex;
    flex-direction: column;
    justify-content: center;
    text-align: center;
    font-size: 9px;
    line-height: 1.15;
    color:
        rgba(255,255,255,.78);
}}

.sector-labels strong {{
    display: block;
    margin-top: 5px;
    font-size: 12px;
    color: #fff;
}}

.recovery-pitch {{
    position: relative;
    height: 348px;
    border:
        2px solid
        rgba(255,255,255,.88);
    overflow: hidden;
    background: #1785d0;
}}

.recovery-row {{
    position: relative;
    z-index: 2;
    height: 25%;
    display: grid;
    grid-template-columns:
        repeat(3, 1fr);
}}

.recovery-row > div {{
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    border-right:
        1px solid
        rgba(255,255,255,.46);
    border-bottom:
        1px solid
        rgba(255,255,255,.46);
    text-align: center;
}}

.recovery-row > div:last-child {{
    border-right: 0;
}}

.recovery-row span {{
    font-size: 9px;
    color:
        rgba(0,0,0,.67);
}}

.recovery-row strong {{
    margin-top: 5px;
    color: #111;
    font-size: 13px;
}}

.recovery-o {{
    background: #ef7b21;
}}

.recovery-po {{
    background: #f0a51c;
}}

.recovery-pd {{
    background: #f3ca1d;
}}

.recovery-d {{
    background: #2f93ea;
}}

.recovery-centre-circle {{
    position: absolute;
    z-index: 3;
    left: 50%;
    top: 50%;
    width: 52px;
    height: 52px;
    transform:
        translate(-50%, -50%);
    border:
        1px dashed
        rgba(255,255,255,.42);
    border-radius: 50%;
    pointer-events: none;
}}

.recovery-bottom-box {{
    position: absolute;
    z-index: 3;
    left: 24%;
    bottom: -1px;
    width: 52%;
    height: 37px;
    border:
        1px solid
        rgba(255,255,255,.40);
    pointer-events: none;
}}

.recovery-bottom-goal {{
    position: absolute;
    z-index: 3;
    left: 40%;
    bottom: -1px;
    width: 20%;
    height: 13px;
    border:
        1px solid
        rgba(255,255,255,.40);
    pointer-events: none;
}}


/* ==========================================================
   ASSIST / FINAL ATTEMPT HALF PITCH
   ========================================================== */

.half-pitch-wrap {{
    display: grid;
    grid-template-columns:
        minmax(0, 1fr)
        24px;
    gap: 7px;
    align-items: end;
}}

.half-pitch {{
    position: relative;
    width: 100%;
    height: 348px;
    overflow: hidden;

    border:
        2px solid
        #69b4ff;

    background: #dadada;
}}

.zone {{
    position: absolute;
    z-index: 2;

    display: flex;
    align-items: center;
    justify-content: center;

    border:
        1px solid
        rgba(255,255,255,.62);
}}

.zone strong {{
    color: #101010;
    font-size: 14px;
    font-weight: 700;
}}


/* Wide channels */
.l-blue {{
    left: 0%;
    top: 0%;
    width: 21%;
    height: 35%;
    background: #72b7ef;
}}

.r-blue {{
    right: 0%;
    top: 0%;
    width: 21%;
    height: 35%;
    background: #72b7ef;
}}


/* Inside-box left/right channels */
.l-green {{
    left: 21%;
    top: 0%;
    width: 16%;
    height: 21%;
    background: #4fc64b;
}}

.r-green {{
    right: 21%;
    top: 0%;
    width: 16%;
    height: 21%;
    background: #4fc64b;
}}


/* Central inside-box stack */
.red-zone {{
    left: 37%;
    top: 0%;
    width: 26%;
    height: 7%;
    background: #ff7059;
}}

.orange-zone {{
    left: 37%;
    top: 7%;
    width: 26%;
    height: 7%;
    background: #eea34b;
}}

.yellow-zone {{
    left: 37%;
    top: 14%;
    width: 26%;
    height: 7%;
    background: #f1dd72;
}}


/* Central outside-box strip */
.pink-zone {{
    left: 21%;
    top: 21%;
    width: 58%;
    height: 14%;
    background: #ef8ce9;
}}


/* Deeper outside-box bands */
.l-grey {{
    left: 0%;
    top: 35%;
    width: 100%;
    height: 29%;
    background: #d6d6d6;
}}

.r-grey {{
    left: 0%;
    top: 64%;
    width: 100%;
    height: 23%;
    background: #aaaaaa;
}}


/* Remaining defensive end */
.half-pitch::after {{
    content: "";
    position: absolute;
    z-index: 0;
    left: 0;
    bottom: 0;
    width: 100%;
    height: 13%;
    background: #d6d6d6;
}}


/* ==========================================================
   PITCH MARKINGS
   ========================================================== */

.top-box-line {{
    position: absolute;
    z-index: 4;

    left: 21%;
    top: 0%;
    width: 58%;
    height: 21%;

    border-left:
        1px solid
        rgba(95,95,95,.65);
    border-right:
        1px solid
        rgba(95,95,95,.65);
    border-bottom:
        1px solid
        rgba(95,95,95,.65);

    pointer-events: none;
}}

.top-semicircle {{
    position: absolute;
    z-index: 4;

    left: 43%;
    top: 17%;
    width: 14%;
    height: 9%;

    border:
        1px dashed
        rgba(95,95,95,.70);

    border-radius:
        0 0 50% 50%;

    border-top: 0;

    pointer-events: none;
}}

.centre-line {{
    position: absolute;
    z-index: 4;

    left: 0;
    top: 64%;
    width: 100%;
    height: 1px;

    background:
        rgba(100,100,100,.46);

    pointer-events: none;
}}

.centre-circle {{
    position: absolute;
    z-index: 4;

    left: 50%;
    top: 64%;

    width: 54px;
    height: 54px;

    transform:
        translate(-50%, -50%);

    border:
        1px dashed
        rgba(100,100,100,.70);

    border-radius: 50%;

    pointer-events: none;
}}

.bottom-penalty-box {{
    position: absolute;
    z-index: 4;

    left: 22%;
    bottom: 0;

    width: 56%;
    height: 18%;

    border:
        1px solid
        rgba(100,100,100,.68);

    pointer-events: none;
}}

.bottom-goal-box {{
    position: absolute;
    z-index: 4;

    left: 39%;
    bottom: 0;

    width: 22%;
    height: 7%;

    border:
        1px solid
        rgba(100,100,100,.50);

    pointer-events: none;
}}

.bottom-semicircle {{
    position: absolute;
    z-index: 4;

    left: 43%;
    bottom: 14%;

    width: 14%;
    height: 7%;

    border:
        1px dashed
        rgba(100,100,100,.60);

    border-radius:
        50% 50% 0 0;

    border-bottom: 0;

    pointer-events: none;
}}


/* ==========================================================
   ATTACK DIRECTION ARROW
   ========================================================== */

.attack-arrow {{
    position: relative;
    width: 22px;
    height: 45px;
}}

.recovery-arrow {{
    align-self: end;
    margin-bottom: 1px;
}}

.half-pitch-arrow {{
    margin-bottom: 1px;
}}

.arrow-body {{
    position: absolute;
    left: 8px;
    bottom: 0;

    width: 7px;
    height: 24px;

    background: #f52222;
}}

.arrow-head {{
    position: absolute;
    left: 0;
    bottom: 21px;

    width: 0;
    height: 0;

    border-left:
        11px solid transparent;
    border-right:
        11px solid transparent;
    border-bottom:
        18px solid #f52222;
}}


/* ==========================================================
   INSIDE / OUTSIDE BOX SUMMARY
   ========================================================== */

.box-summary {{
    width:
        calc(100% - 31px);

    display: grid;
    grid-template-columns:
        1fr 1fr;

    margin-top: 2px;

    background: #d8d8d8;

    color: #151515;

    border-top:
        1px solid
        rgba(90,90,90,.34);
}}

.box-summary > div {{
    min-height: 48px;

    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;

    font-size: 10px;
}}

.box-summary strong {{
    margin-top: 3px;

    color: #f22;
    font-size: 12px;
}}


/* ==========================================================
   RESPONSIVE
   ========================================================== */

@media (
    max-width: 1100px
) {{

    .spatial-report-grid {{
        grid-template-columns:
            1fr;
        gap: 28px;
    }}

    .report-panel {{
        max-width: 620px;
        margin:
            0 auto;
    }}

}}
"""


def _build_zone_relationship_reference_html(records):
    spatial_css = _get_spatial_css()

    return f"""
<!doctype html>
<html>
<head>
<meta charset="UTF-8">
<style>
{spatial_css}

.spatial-report-grid {{
    grid-template-columns: 1fr 1fr;
    gap: 12px;
}}

.report-panel {{
    max-width: none;
    margin: 0;
}}

.half-pitch {{
    height: 315px;
}}

@media (max-width: 850px) {{
    .spatial-report-grid {{
        grid-template-columns: 1fr;
    }}
}}
</style>
</head>
<body>
<div class="spatial-report-shell">
    <div class="spatial-report-grid">
        {_report_half_pitch_panel(records, "assist_zone", "Assist zone (ex. SP)")}
        {_report_half_pitch_panel(records, "final_attempt_zone", "Final attempt zone")}
    </div>
</div>
</body>
</html>
"""


def render_spatial_analysis(records):
    add_final_attempt_box_location(records)

    st.markdown(
        "### Spatial Analysis"
    )

    recovery_counts = _zone_counts(
        records,
        "recovery_zone",
    )

    spatial_css = _get_spatial_css()

    def build_panel_html(panel_html):
        return f"""
<!doctype html>
<html>
<head>
<meta charset="UTF-8">
<style>
{spatial_css}

.spatial-report-grid {{
    display: block;
}}

.report-panel {{
    max-width: none;
    margin: 0;
}}
</style>
</head>
<body>
<div class="spatial-report-shell">
    <div class="spatial-report-grid">
        {panel_html}
    </div>
</div>
</body>
</html>
"""

    recovery_panel_html = build_panel_html(
        _report_recovery_panel(
            recovery_counts
        )
    )

    assist_panel_html = build_panel_html(
        _report_half_pitch_panel(
            records,
            "assist_zone",
            "Assist zone (ex. SP)",
        )
    )

    final_panel_html = build_panel_html(
        _report_half_pitch_panel(
            records,
            "final_attempt_zone",
            "Final attempt zone",
        )
    )

    # Keep the combined spatial visual available for report export.
    combined_html = f"""
<!doctype html>
<html>
<head>
<meta charset="UTF-8">
<style>
{spatial_css}
</style>
</head>
<body>
<div class="spatial-report-shell">
    <div class="spatial-report-grid">
        {_report_recovery_panel(recovery_counts)}
        {_report_half_pitch_panel(records, "assist_zone", "Assist zone (ex. SP)")}
        {_report_half_pitch_panel(records, "final_attempt_zone", "Final attempt zone")}
    </div>
</div>
</body>
</html>
"""

    st.caption(
        "Spatial layout follows the Sportscode Final Attempts report. "
        "Counts are calculated from the currently filtered events."
    )

    # ========================================================
    # RECOVERY ZONE
    # ========================================================

    st.markdown(
        "#### Recovery Zone Effectiveness"
    )

    recovery_df = _metric_table(
        records,
        "recovery_zone",
        "Recovery Zone",
        RECOVERY_ZONE_ORDER,
    )

    recovery_map_col, recovery_table_col = st.columns(
        [0.9, 1.6],
        gap="large",
    )

    with recovery_map_col:
        st.iframe(
            recovery_panel_html,
            width="stretch",
            height=455,
        )

    with recovery_table_col:
        _display_df(
            recovery_df,
            "Recovery Zone",
            report_section_title="Recovery Zone Effectiveness",
            report_key="spatial_recovery_zone",
        )

    if not recovery_df.empty:
        render_metric_chart(
            recovery_df,
            "Recovery Zone",
            height=max(
                360,
                len(recovery_df) * 52,
            ),
            report_section_title="Recovery Zone Effectiveness",
            report_key="spatial_recovery_zone_chart",
        )

    st.write("")

    # ========================================================
    # ASSIST ZONE
    # ========================================================

    st.markdown(
        "#### Assist Zone Effectiveness"
    )

    assist_df = _metric_table(
        records,
        "assist_zone",
        "Assist Zone",
    )

    assist_map_col, assist_table_col = st.columns(
        [0.9, 1.6],
        gap="large",
    )

    with assist_map_col:
        st.iframe(
            assist_panel_html,
            width="stretch",
            height=455,
        )

    with assist_table_col:
        _display_df(
            assist_df,
            "Assist Zone",
            report_section_title="Assist Zone Effectiveness",
            report_key="spatial_assist_zone",
        )

    st.write("")

    # ========================================================
    # FINAL ATTEMPT ZONE
    # ========================================================

    st.markdown(
        "#### Final Attempt Zone Effectiveness"
    )

    final_df = _metric_table(
        records,
        "final_attempt_zone",
        "Final Attempt Zone",
    )

    final_map_col, final_table_col = st.columns(
        [0.9, 1.6],
        gap="large",
    )

    with final_map_col:
        st.iframe(
            final_panel_html,
            width="stretch",
            height=455,
        )

    with final_table_col:
        _display_df(
            final_df,
            "Final Attempt Zone",
            report_section_title="Final Attempt Zone Effectiveness",
            report_key="spatial_final_zone",
        )

        st.markdown(
            "#### Inside / Outside Box Effectiveness"
        )

        box_df = _metric_table(
            records,
            "final_attempt_box_location",
            "Box Location",
            BOX_LOCATION_ORDER,
        )

        _display_df(
            box_df,
            "Box Location",
            report_section_title="Inside / Outside Box Effectiveness",
            report_key="spatial_box_location",
        )

    if _ACTIVE_REPORT_CONTEXT is not None:
        item = create_image_report_item(
            module="final_attempt",
            section_title="Spatial Analysis",
            html=combined_html,
            context=_ACTIVE_REPORT_CONTEXT,
            width_px=1400,
            height_px=475,
        )
        render_add_to_report_button(
            item,
            key=f"report_final_attempt_spatial_{item['id']}",
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

    for player in ordered_categories(records, key):
        if _norm(player) == "OTHER":
            continue

        subset = records_with_category(records, key, player)
        m = outcome_metrics(subset)
        total = m["total"]

        rows.append(
            {
                player_column: player,
                metric_label: total,
                "On Target": fmt_rate(m["on_target"], total),
                "Off Target": fmt_rate(m["off_target"], total),
                "Blocked": fmt_rate(m["blocked"], total),
                "Goals": m["goals"],
                "Goal Conversion": fmt_rate(m["goals"], total),
                "On Target Conversion": fmt_rate(m["goals"], m["on_target"]),
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
        report_section_title="Final Attempt Player",
        report_key="final_attempt_player",
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
        report_section_title="Assist Player",
        report_key="assist_player",
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
        report_section_title="Pre-Assist / 2nd Assist",
        report_key="second_assist",
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
        report_section_title="Recovery Player",
        report_key="recovery_player",
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

        relationship_df=pd.DataFrame(rows)
        st.dataframe(relationship_df,hide_index=True,width="stretch")
        if _ACTIVE_REPORT_CONTEXT is not None:
            item=create_table_report_item(module="final_attempt",section_title="Pre-Assist → Assist → Final Attempt Player",dataframe=relationship_df,context=_ACTIVE_REPORT_CONTEXT)
            render_add_to_report_button(item,key=f"report_final_attempt_chain_{item['id']}")

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

        relationship_df = pd.DataFrame(rows)

        zone_map_col, relationship_table_col = st.columns(
            [1.2, 1.6],
            gap="large",
        )

        with zone_map_col:
            st.iframe(
                _build_zone_relationship_reference_html(records),
                width="stretch",
                height=470,
            )

        with relationship_table_col:
            st.dataframe(
                relationship_df,
                hide_index=True,
                width="stretch",
            )

            if _ACTIVE_REPORT_CONTEXT is not None:
                item = create_table_report_item(
                    module="final_attempt",
                    section_title="Assist Zone → Final Attempt Zone",
                    dataframe=relationship_df,
                    context=_ACTIVE_REPORT_CONTEXT,
                )
                render_add_to_report_button(
                    item,
                    key=f"report_final_attempt_zone_relation_{item['id']}",
                )


# ============================================================
# MAIN RENDERER
# ============================================================

def render_final_attempt_analysis(
    analysis: dict,
    phase: str | None = None,
    analysis_scope: str | None = None,
    report_context: dict | None = None,
):
    global _ACTIVE_REPORT_CONTEXT
    _ACTIVE_REPORT_CONTEXT = report_context

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

    render_create_report_button(
        "final_attempt",
        key="create_final_attempt_report",
    )

    # --------------------------------------------------------
    # OVERVIEW
    # --------------------------------------------------------
    render_kpis(
        records,
        phase,
    )

    st.markdown("---")

    # --------------------------------------------------------
    # TIME: ATTEMPTS -> GOALS
    # --------------------------------------------------------
    render_time_profile(
        records,
    )

    render_goal_breakdown_for_variable(
        records,
        "time_period",
        "Period",
        "Goals by Time Period",
        TIME_PERIODS,
        report_key="time_period",
    )

    st.markdown("---")

    # --------------------------------------------------------
    # ATTACK TYPE: ATTEMPTS -> GOALS
    # --------------------------------------------------------
    render_attack_type(
        records,
    )

    render_goal_breakdown_for_variable(
        records,
        "attack_type",
        "Attack Type",
        "Goals by Attack Type",
        ATTACK_TYPE_ORDER,
        report_key="attack_type",
    )

    render_organized_attack(
        records,
    )

    render_counter_context(
        records,
    )

    st.markdown("---")

    # --------------------------------------------------------
    # SET PLAYS: ATTEMPTS -> GOALS
    # --------------------------------------------------------
    render_set_plays(
        records,
    )

    set_play_records = records_with_category(
        records,
        "attack_type",
        "SET PLAY",
    )
    if any(
        event_has_value(record, "outcome", "GOAL")
        for record in set_play_records
    ):
        render_goal_breakdown_for_variable(
            set_play_records,
            "set_play_type",
            "Set Play",
            "Goals by Set Play Type",
            SET_PLAY_ORDER,
            _set_play_display_name,
            report_key="set_play_type",
        )

    st.markdown("---")

    # --------------------------------------------------------
    # SEQUENCE CONSTRUCTION
    # --------------------------------------------------------
    render_sequence_construction(
        records,
        analysis_scope,
    )

    st.markdown("---")

    # --------------------------------------------------------
    # SPATIAL: ATTEMPTS -> GOALS
    # --------------------------------------------------------
    render_spatial_analysis(
        records,
    )

    render_goal_breakdown_for_variable(
        records,
        "final_attempt_zone",
        "Final Attempt Zone",
        "Goals by Final Attempt Zone",
        report_key="final_attempt_zone",
    )

    st.markdown("---")

    # --------------------------------------------------------
    # PLAYERS: ATTEMPTS -> GOALS
    # --------------------------------------------------------
    render_players(
        records,
    )

    render_goal_breakdown_for_variable(
        records,
        "final_attempt_player",
        "Player",
        "Goals by Final Attempt Player",
        report_key="goal_player",
    )

    render_relationships(
        records,
        analysis_scope,
    )


# Backward-compatible alias.
render_final_attempts_analysis = (
    render_final_attempt_analysis
)
