from collections import Counter


import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.reports.report_items import (
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

KEEP_POSS = "KEEP POSS"
LOSS_POSS = "LOSS POSS"

FORWARD = "FORWARD"

BOX_ENTRY = "BOX ENTRY"
SWITCH_PLAY = "SWITCH PLAY"
WIN_SET_PLAY = "WIN SP (TI,FK,CK)"
CROSS_DECOY_RUNS = "CROSS/DECOY RUNS"

THROW_IN_ZONE_ORDER = [
    "DEF ZONE",
    "PRE-DEF ZONE",
    "PRE-OFF ZONE",
    "OFF ZONE",
]


THROW_IN_GRAYSCALE = {
    "Keep Possession": "#404040",
    "Forward": "#656565",
    "Loss Possession": "#C8C8C8",
    "Box Entry": "#A0A0A0",
    "Win Set Play": "#FFFFFF",
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


def _normalize_text(value):
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
    target_value: str,
) -> bool:
    target = _normalize_text(
        target_value
    )

    for value in _as_list(
        record.get(key)
    ):
        if (
            _normalize_text(value)
            == target
        ):
            return True

    return False


def count_events_with_value(
    records: list[dict],
    key: str,
    target_value: str,
) -> int:
    return sum(
        1
        for record in records
        if event_has_value(
            record,
            key,
            target_value,
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
        return "0% (0/0)"

    return (
        f"{calculate_rate(numerator, denominator):.0f}% "
        f"({numerator}/{denominator})"
    )


# ============================================================
# CATEGORY HELPERS
# ============================================================

def get_record_category_values(
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

        normalized = (
            _normalize_text(value)
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


def count_categories(
    records: list[dict],
    key: str,
    include_unknown: bool = False,
) -> Counter:
    counts = Counter()

    for record in records:
        values = (
            get_record_category_values(
                record,
                key,
                include_unknown,
            )
        )

        for value in values:
            counts[value] += 1

    return counts


def get_most_common_value(
    records: list[dict],
    key: str,
    include_unknown: bool = False,
) -> tuple[str, int]:
    counts = count_categories(
        records,
        key,
        include_unknown,
    )

    if not counts:
        return "-", 0

    return counts.most_common(1)[0]


def records_with_category(
    records: list[dict],
    key: str,
    category: str,
) -> list[dict]:
    return [
        record
        for record in records
        if event_has_value(
            record,
            key,
            category,
        )
    ]


# ============================================================
# RETENTION HELPERS
# ============================================================

def has_retention_label(
    record: dict,
) -> bool:
    return bool(
        get_record_category_values(
            record,
            "retention",
        )
    )


def get_retention_coded_records(
    records: list[dict],
) -> list[dict]:
    return [
        record
        for record in records
        if has_retention_label(
            record
        )
    ]


def calculate_retention_metrics(
    records: list[dict],
) -> dict:
    coded_records = (
        get_retention_coded_records(
            records
        )
    )

    denominator = len(
        coded_records
    )

    kept = (
        count_events_with_value(
            coded_records,
            "retention",
            KEEP_POSS,
        )
    )

    lost = (
        count_events_with_value(
            coded_records,
            "retention",
            LOSS_POSS,
        )
    )

    return {
        "coded":
            denominator,

        "kept":
            kept,

        "lost":
            lost,

        "keep_rate":
            calculate_rate(
                kept,
                denominator,
            ),

        "loss_rate":
            calculate_rate(
                lost,
                denominator,
            ),
    }


# ============================================================
# KPI CALCULATION
# ============================================================

def calculate_throw_in_kpis(
    records: list[dict],
) -> dict:
    total = len(
        records
    )

    retention = (
        calculate_retention_metrics(
            records
        )
    )

    forward_records = (
        records_with_category(
            records,
            "direction",
            FORWARD,
        )
    )

    forward = len(
        forward_records
    )

    forward_retention = (
        calculate_retention_metrics(
            forward_records
        )
    )

    box_entry = (
        count_events_with_value(
            records,
            "result",
            BOX_ENTRY,
        )
    )

    win_set_play = (
        count_events_with_value(
            records,
            "result",
            WIN_SET_PLAY,
        )
    )

    switch_play = (
        count_events_with_value(
            records,
            "result",
            SWITCH_PLAY,
        )
    )

    cross_decoy = (
        count_events_with_value(
            records,
            "result",
            CROSS_DECOY_RUNS,
        )
    )

    (
        most_common_zone,
        zone_count,
    ) = get_most_common_value(
        records,
        "throw_in_zone",
    )

    (
        most_common_length,
        length_count,
    ) = get_most_common_value(
        records,
        "length",
    )

    (
        most_common_speed,
        speed_count,
    ) = get_most_common_value(
        records,
        "speed",
    )

    (
        most_common_taker,
        taker_count,
    ) = get_most_common_value(
        records,
        "taker",
        include_unknown=True,
    )

    return {
        "total":
            total,

        "retention_coded":
            retention["coded"],

        "kept":
            retention["kept"],

        "lost":
            retention["lost"],

        "forward":
            forward,

        "forward_retention_coded":
            forward_retention["coded"],

        "forward_kept":
            forward_retention["kept"],

        "box_entry":
            box_entry,

        "win_set_play":
            win_set_play,

        "switch_play":
            switch_play,

        "cross_decoy":
            cross_decoy,

        "most_common_zone":
            most_common_zone,

        "zone_count":
            zone_count,

        "most_common_length":
            most_common_length,

        "length_count":
            length_count,

        "most_common_speed":
            most_common_speed,

        "speed_count":
            speed_count,

        "most_common_taker":
            most_common_taker,

        "taker_count":
            taker_count,
    }


# ============================================================
# RESULT BREAKDOWN
# ============================================================

def build_result_dataframe(
    records: list[dict],
) -> pd.DataFrame:
    total = len(
        records
    )

    counts = count_categories(
        records,
        "result",
    )

    rows = []

    for (
        result,
        count,
    ) in counts.items():
        rows.append(
            {
                "Result":
                    result,

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


def render_result_breakdown(
    records: list[dict],
    report_context: dict | None = None,
):
    st.markdown(
        "### Result Breakdown"
    )

    df = build_result_dataframe(
        records
    )

    if df.empty:
        st.info(
            "No RESULT data available "
            "for the selected throw-ins."
        )
        return

    fig = px.bar(
        df,
        x="Percentage",
        y="Result",
        orientation="h",
        text="Display",
    )

    fig.update_traces(
        textposition="outside",
        cliponaxis=False,
        marker_color="#787878",
    )

    fig.update_layout(
        height=max(
            280,
            55 * len(df),
        ),
        margin=dict(
            l=20,
            r=130,
            t=10,
            b=20,
        ),
        xaxis_title=(
            "Throw-in Rate (%)"
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
        "RESULT labels are not mutually exclusive. "
        "One throw-in can contain more than one result, "
        "so percentages do not need to total 100%."
    )

    if report_context is not None:
        report_item = create_plotly_report_item(
            module="throw_in",
            section_title="Result Breakdown",
            figure=fig,
            context=report_context,
            notes=[
                "RESULT labels are not mutually exclusive. "
                "One throw-in can contain more than one result, "
                "so percentages do not need to total 100%.",
            ],
        )
        render_add_to_report_button(
            report_item,
            key=f"report_throw_result_{report_item['id']}",
        )


# ============================================================
# RETENTION BY ZONE
# ============================================================

def build_retention_by_zone_dataframe(
    records: list[dict],
) -> pd.DataFrame:
    zones = count_categories(
        records,
        "throw_in_zone",
    )

    ordered_zones = [
        zone
        for zone in THROW_IN_ZONE_ORDER
        if zone in zones
    ]

    unexpected_zones = sorted(
        zone
        for zone in zones
        if zone not in THROW_IN_ZONE_ORDER
    )

    rows = []

    for zone in [
        *ordered_zones,
        *unexpected_zones,
    ]:
        zone_records = (
            records_with_category(
                records,
                "throw_in_zone",
                zone,
            )
        )

        total_throw_ins = len(
            zone_records
        )

        retention = (
            calculate_retention_metrics(
                zone_records
            )
        )

        coded = retention[
            "coded"
        ]

        box_entry_count = (
            count_events_with_value(
                zone_records,
                "result",
                BOX_ENTRY,
            )
        )

        rows.append(
            {
                "Zone":
                    zone,

                "Throw-ins":
                    total_throw_ins,

                "Retention Coded":
                    coded,

                "Keep Count":
                    retention[
                        "kept"
                    ],

                "Loss Count":
                    retention[
                        "lost"
                    ],

                "Keep %":
                    calculate_rate(
                        retention["kept"],
                        coded,
                    ),

                "Loss %":
                    calculate_rate(
                        retention["lost"],
                        coded,
                    ),

                "Keep Possession":
                    format_rate(
                        retention["kept"],
                        coded,
                    ),

                "Loss Possession":
                    format_rate(
                        retention["lost"],
                        coded,
                    ),

                "Box Entry Count":
                    box_entry_count,

                "Box Entry %":
                    calculate_rate(
                        box_entry_count,
                        total_throw_ins,
                    ),

                "Box Entry":
                    format_rate(
                        box_entry_count,
                        total_throw_ins,
                    ),
            }
        )

    return pd.DataFrame(
        rows
    )


def render_retention_by_zone(
    records: list[dict],
    report_context: dict | None = None,
):
    st.markdown(
        "### Retention by Zone"
    )

    df = (
        build_retention_by_zone_dataframe(
            records
        )
    )

    if df.empty:
        st.info(
            "No throw-in zone data available."
        )
        return

    fig = go.Figure()

    keep_display = [
        format_rate(
            int(row["Keep Count"]),
            int(row["Retention Coded"]),
        )
        for _, row
        in df.iterrows()
    ]

    fig.add_bar(
        x=df["Zone"],
        y=df["Keep %"],
        name="Keep Possession",
        marker_color=THROW_IN_GRAYSCALE["Keep Possession"],
        text=keep_display,
        textposition="inside",
        customdata=keep_display,
        hovertemplate=(
            "<b>%{x}</b><br>"
            "Keep Possession: %{customdata}"
            "<extra></extra>"
        ),
    )

    loss_display = [
        format_rate(
            int(row["Loss Count"]),
            int(row["Retention Coded"]),
        )
        for _, row
        in df.iterrows()
    ]

    fig.add_bar(
        x=df["Zone"],
        y=df["Loss %"],
        name="Loss Possession",
        marker_color=THROW_IN_GRAYSCALE["Loss Possession"],
        text=loss_display,
        textposition="inside",
        customdata=loss_display,
        hovertemplate=(
            "<b>%{x}</b><br>"
            "Loss Possession: %{customdata}"
            "<extra></extra>"
        ),
    )

    fig.add_trace(
        go.Scatter(
            x=df["Zone"],
            y=df["Box Entry %"],
            mode="lines+markers+text",
            name="Box Entry",
            text=[
                format_rate(
                    int(row["Box Entry Count"]),
                    int(row["Throw-ins"]),
                )
                for _, row
                in df.iterrows()
            ],
            textposition="top center",
            textfont=dict(
                size=14,
                color="white",
            ),
            line=dict(
                width=5,
                color="#FFD54F",
            ),
            marker=dict(
                size=12,
                color="#FFD54F",
                line=dict(
                    width=2,
                    color="white",
                ),
            ),
            yaxis="y2",
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Box Entry: %{text}"
                "<extra></extra>"
            ),
        )
    )

    fig.update_layout(
        barmode="stack",
        height=430,
        margin=dict(
            l=20,
            r=150,
            t=10,
            b=20,
        ),
        xaxis_title="",
        yaxis_title=(
            "Retention Outcome (%)"
        ),
        yaxis=dict(
            range=[
                0,
                100,
            ]
        ),
        yaxis2=dict(
            title=dict(
                text="Box Entry Rate (%)",
                font=dict(
                    color="#FFD54F",
                ),
            ),
            range=[
                0,
                100,
            ],
            overlaying="y",
            side="right",
            showgrid=False,
            tickfont=dict(
                color="#FFD54F",
            ),
        ),
        legend_title="",
        legend=dict(
            x=1.08,
            xanchor="left",
            y=1.0,
            yanchor="top",
            bgcolor="rgba(0,0,0,0.35)",
        ),
    )

    st.plotly_chart(
        fig,
        width="stretch",
    )

    st.caption(
        "Retention percentages use only throw-ins "
        "with a RETENTION label as the denominator. "
        "Box Entry rate uses all throw-ins in each zone "
        "as the denominator."
    )

    if report_context is not None:
        report_item = create_plotly_report_item(
            module="throw_in",
            section_title="Retention by Zone",
            figure=fig,
            context=report_context,
            notes=[
                "Retention percentages use only throw-ins with a RETENTION label as the denominator.",
                "Box Entry rate uses all throw-ins in each zone as the denominator.",
            ],
        )
        render_add_to_report_button(
            report_item,
            key=f"report_throw_retention_zone_{report_item['id']}",
        )


# ============================================================
# EFFECTIVENESS DATA
# ============================================================

def build_effectiveness_dataframe(
    records: list[dict],
    group_key: str,
    include_unknown: bool = False,
) -> pd.DataFrame:
    categories = count_categories(
        records,
        group_key,
        include_unknown,
    )

    rows = []

    for category in categories:
        if category == "UNKNOWN":
            category_records = [
                record
                for record in records
                if not get_record_category_values(
                    record,
                    group_key,
                )
            ]

        else:
            category_records = (
                records_with_category(
                    records,
                    group_key,
                    category,
                )
            )

        total = len(
            category_records
        )

        retention = (
            calculate_retention_metrics(
                category_records
            )
        )

        retention_coded = (
            retention["coded"]
        )

        keep = retention[
            "kept"
        ]

        loss = retention[
            "lost"
        ]

        forward = (
            count_events_with_value(
                category_records,
                "direction",
                FORWARD,
            )
        )

        box_entry = (
            count_events_with_value(
                category_records,
                "result",
                BOX_ENTRY,
            )
        )

        win_sp = (
            count_events_with_value(
                category_records,
                "result",
                WIN_SET_PLAY,
            )
        )

        switch_play = (
            count_events_with_value(
                category_records,
                "result",
                SWITCH_PLAY,
            )
        )

        cross_decoy = (
            count_events_with_value(
                category_records,
                "result",
                CROSS_DECOY_RUNS,
            )
        )

        fast = (
            count_events_with_value(
                category_records,
                "speed",
                "FAST",
            )
        )

        rows.append(
            {
                "Category":
                    category,

                "Throw-ins":
                    total,

                "Retention Coded":
                    retention_coded,

                "Keep %":
                    calculate_rate(
                        keep,
                        retention_coded,
                    ),

                "Keep Possession":
                    format_rate(
                        keep,
                        retention_coded,
                    ),

                "Loss %":
                    calculate_rate(
                        loss,
                        retention_coded,
                    ),

                "Loss Possession":
                    format_rate(
                        loss,
                        retention_coded,
                    ),

                "Forward %":
                    calculate_rate(
                        forward,
                        total,
                    ),

                "Forward":
                    format_rate(
                        forward,
                        total,
                    ),

                "Box Entry %":
                    calculate_rate(
                        box_entry,
                        total,
                    ),

                "Box Entry":
                    format_rate(
                        box_entry,
                        total,
                    ),

                "Win SP %":
                    calculate_rate(
                        win_sp,
                        total,
                    ),

                "Win SP":
                    format_rate(
                        win_sp,
                        total,
                    ),

                "Switch Play %":
                    calculate_rate(
                        switch_play,
                        total,
                    ),

                "Switch Play":
                    format_rate(
                        switch_play,
                        total,
                    ),

                "Cross / Decoy Runs %":
                    calculate_rate(
                        cross_decoy,
                        total,
                    ),

                "Cross / Decoy Runs":
                    format_rate(
                        cross_decoy,
                        total,
                    ),

                "Fast %":
                    calculate_rate(
                        fast,
                        total,
                    ),

                "Fast":
                    format_rate(
                        fast,
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
            [
                "Throw-ins",
                "Category",
            ],
            ascending=[
                False,
                True,
            ],
        )
        .reset_index(
            drop=True
        )
    )


# ============================================================
# PDF-ONLY CHART LABELS
# ============================================================

def _build_pdf_labeled_bar_figure(
    df: pd.DataFrame,
    metric_specs: list[tuple[str, str, str]],
    *,
    xaxis_title: str = "",
):
    """
    Build a dedicated PDF-only grouped bar chart directly from the
    analytical dataframe.

    metric_specs contains:
        (numeric_percentage_column, legend_name, display_label_column)

    This avoids relying on the Streamlit Plotly trace ordering and
    guarantees that every printed label is attached to the exact bar
    that produced it.
    """
    rows = []

    category_order = [
        str(value)
        for value in df[
            "Category"
        ].tolist()
    ]

    for _, row in df.iterrows():
        category = str(
            row[
                "Category"
            ]
        )

        for (
            percentage_column,
            metric_name,
            display_column,
        ) in metric_specs:
            percentage = row.get(
                percentage_column,
                0,
            )

            display = row.get(
                display_column,
                "",
            )

            rows.append(
                {
                    "Category":
                        category,

                    "Metric":
                        metric_name,

                    "Percentage":
                        percentage,

                    "Display":
                        str(display),
                }
            )

    pdf_df = pd.DataFrame(
        rows
    )

    pdf_fig = px.bar(
        pdf_df,
        x="Category",
        y="Percentage",
        color="Metric",
        barmode="group",
        text="Display",
        category_orders={
            "Category":
                category_order,

            "Metric":
                [
                    metric_name
                    for (
                        _,
                        metric_name,
                        _,
                    )
                    in metric_specs
                ],
        },
        color_discrete_map=THROW_IN_GRAYSCALE,
    )

    pdf_fig.update_traces(
        textposition="outside",
        cliponaxis=False,
        textfont=dict(
            size=12,
            color="#222222",
        ),
    )

    pdf_fig.update_layout(
        height=520,
        margin=dict(
            l=30,
            r=30,
            t=20,
            b=30,
        ),
        xaxis_title=xaxis_title,
        yaxis_title="Rate (%)",
        yaxis=dict(
            range=[
                0,
                115,
            ]
        ),
        legend_title="",
    )

    return pdf_fig


# ============================================================
# EFFECTIVENESS CHART
# ============================================================

def render_effectiveness_chart(
    title: str,
    df: pd.DataFrame,
    report_context: dict | None = None,
):
    st.markdown(
        f"#### {title}"
    )

    if df.empty:
        st.info(
            "No data available."
        )
        return

    chart_df = df[
        [
            "Category",
            "Keep %",
            "Box Entry %",
            "Win SP %",
        ]
    ].copy()

    chart_long = (
        chart_df
        .melt(
            id_vars=[
                "Category"
            ],
            value_vars=[
                "Keep %",
                "Box Entry %",
                "Win SP %",
            ],
            var_name="Metric",
            value_name="Percentage",
        )
    )

    chart_long[
        "Metric"
    ] = (
        chart_long[
            "Metric"
        ]
        .replace(
            {
                "Keep %":
                    "Keep Possession",

                "Box Entry %":
                    "Box Entry",

                "Win SP %":
                    "Win Set Play",
            }
        )
    )

    display_lookup = {}

    for _, row in df.iterrows():
        category = str(
            row[
                "Category"
            ]
        )

        display_lookup[
            (
                category,
                "Keep Possession",
            )
        ] = row[
            "Keep Possession"
        ]

        display_lookup[
            (
                category,
                "Box Entry",
            )
        ] = row[
            "Box Entry"
        ]

        display_lookup[
            (
                category,
                "Win Set Play",
            )
        ] = row[
            "Win SP"
        ]

    chart_long[
        "Display"
    ] = [
        display_lookup.get(
            (
                str(category),
                str(metric),
            ),
            "",
        )
        for category, metric
        in zip(
            chart_long[
                "Category"
            ],
            chart_long[
                "Metric"
            ],
        )
    ]

    fig = px.bar(
        chart_long,
        x="Category",
        y="Percentage",
        color="Metric",
        barmode="group",
        text="Display",
        color_discrete_map=THROW_IN_GRAYSCALE,
    )

    fig.update_traces(
        textposition="outside",
        cliponaxis=False,
        textfont=dict(
            size=12,
        ),
    )

    fig.update_layout(
        height=390,
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
                115,
            ]
        ),
        legend_title="",
    )

    st.plotly_chart(
        fig,
        width="stretch",
    )

    if report_context is not None:
        pdf_fig = _build_pdf_labeled_bar_figure(
            df,
            [
                (
                    "Keep %",
                    "Keep Possession",
                    "Keep Possession",
                ),
                (
                    "Box Entry %",
                    "Box Entry",
                    "Box Entry",
                ),
                (
                    "Win SP %",
                    "Win Set Play",
                    "Win SP",
                ),
            ],
        )

        report_item = create_plotly_report_item(
            module="throw_in",
            section_title=title,
            figure=pdf_fig,
            context=report_context,
        )

        render_add_to_report_button(
            report_item,
            key=(
                "report_throw_effectiveness_"
                f"{title}_{report_item['id']}"
            ),
        )

    display_df = df[
        [
            "Category",
            "Throw-ins",
            "Keep Possession",
            "Loss Possession",
            "Forward",
            "Box Entry",
            "Win SP",
            "Switch Play",
        ]
    ].copy()

    display_df = display_df.rename(
        columns={
            "Win SP":
                "Win Set Play",
        }
    )

    st.dataframe(
        display_df,
        hide_index=True,
        width="stretch",
    )

    if report_context is not None:
        table_item = create_table_report_item(
            module="throw_in",
            section_title=f"{title} — Table",
            dataframe=display_df,
            context=report_context,
        )

        render_add_to_report_button(
            table_item,
            key=(
                "report_throw_effectiveness_table_"
                f"{title}_{table_item['id']}"
            ),
        )


# ============================================================
# PLAYER COMPARISON
# ============================================================

def render_player_comparison(
    records: list[dict],
    report_context: dict | None = None,
):
    st.markdown(
        "### Player Comparison"
    )

    df = (
        build_effectiveness_dataframe(
            records,
            "taker",
            include_unknown=True,
        )
    )

    if df.empty:
        st.info(
            "No taker data available."
        )
        return

    chart_df = df[
        [
            "Category",
            "Keep %",
            "Forward %",
            "Box Entry %",
            "Win SP %",
        ]
    ].copy()

    chart_long = (
        chart_df
        .melt(
            id_vars=[
                "Category"
            ],
            value_vars=[
                "Keep %",
                "Forward %",
                "Box Entry %",
                "Win SP %",
            ],
            var_name="Metric",
            value_name="Percentage",
        )
    )

    chart_long[
        "Metric"
    ] = (
        chart_long[
            "Metric"
        ]
        .replace(
            {
                "Keep %":
                    "Keep Possession",

                "Forward %":
                    "Forward",

                "Box Entry %":
                    "Box Entry",

                "Win SP %":
                    "Win Set Play",
            }
        )
    )

    display_lookup = {}

    for _, row in df.iterrows():
        category = str(
            row[
                "Category"
            ]
        )

        display_lookup[
            (
                category,
                "Keep Possession",
            )
        ] = row[
            "Keep Possession"
        ]

        display_lookup[
            (
                category,
                "Forward",
            )
        ] = row[
            "Forward"
        ]

        display_lookup[
            (
                category,
                "Box Entry",
            )
        ] = row[
            "Box Entry"
        ]

        display_lookup[
            (
                category,
                "Win Set Play",
            )
        ] = row[
            "Win SP"
        ]

    chart_long[
        "Display"
    ] = [
        display_lookup.get(
            (
                str(category),
                str(metric),
            ),
            "",
        )
        for category, metric
        in zip(
            chart_long[
                "Category"
            ],
            chart_long[
                "Metric"
            ],
        )
    ]

    fig = px.bar(
        chart_long,
        x="Category",
        y="Percentage",
        color="Metric",
        barmode="group",
        text="Display",
        color_discrete_map=THROW_IN_GRAYSCALE,
    )

    # Force the Player Comparison palette explicitly so Plotly cannot
    # fall back to its default red for Win Set Play.
    for trace in fig.data:
        if trace.name in THROW_IN_GRAYSCALE:
            trace.marker.color = THROW_IN_GRAYSCALE[trace.name]

    fig.update_traces(
        textposition="outside",
        cliponaxis=False,
        textfont=dict(
            size=12,
        ),
    )

    fig.update_layout(
        height=420,
        margin=dict(
            l=20,
            r=20,
            t=10,
            b=20,
        ),
        xaxis_title="Taker",
        yaxis_title="Rate (%)",
        yaxis=dict(
            range=[
                0,
                115,
            ]
        ),
        legend_title="",
    )

    st.plotly_chart(
        fig,
        width="stretch",
    )

    if report_context is not None:
        pdf_fig = _build_pdf_labeled_bar_figure(
            df,
            [
                (
                    "Keep %",
                    "Keep Possession",
                    "Keep Possession",
                ),
                (
                    "Forward %",
                    "Forward",
                    "Forward",
                ),
                (
                    "Box Entry %",
                    "Box Entry",
                    "Box Entry",
                ),
                (
                    "Win SP %",
                    "Win Set Play",
                    "Win SP",
                ),
            ],
            xaxis_title="Taker",
        )

        report_item = create_plotly_report_item(
            module="throw_in",
            section_title="Player Comparison",
            figure=pdf_fig,
            context=report_context,
        )

        render_add_to_report_button(
            report_item,
            key=f"report_throw_player_{report_item['id']}",
        )

    table_df = df[
        [
            "Category",
            "Throw-ins",
            "Keep Possession",
            "Loss Possession",
            "Forward",
            "Box Entry",
            "Win SP",
            "Switch Play",
        ]
    ].copy()

    table_df = table_df.rename(
        columns={
            "Category":
                "Taker",

            "Win SP":
                "Win Set Play",
        }
    )

    st.dataframe(
        table_df,
        hide_index=True,
        width="stretch",
    )

    if report_context is not None:
        table_item = create_table_report_item(
            module="throw_in",
            section_title="Player Comparison — Table",
            dataframe=table_df,
            context=report_context,
        )

        render_add_to_report_button(
            table_item,
            key=(
                "report_throw_player_table_"
                f"{table_item['id']}"
            ),
        )

    st.caption(
        "Use the Taker filter to turn the whole "
        "dashboard into an individual player profile."
    )


# ============================================================
# ZONE EFFECTIVENESS
# ============================================================

def render_zone_effectiveness(
    records: list[dict],
    report_context: dict | None = None,
):
    st.markdown(
        "### Zone Effectiveness"
    )

    df = (
        build_effectiveness_dataframe(
            records,
            "throw_in_zone",
        )
    )

    if df.empty:
        st.info(
            "No throw-in zone data available."
        )
        return

    df = df.rename(
        columns={
            "Category":
                "Zone",
        }
    )

    display_df = df[
        [
            "Zone",
            "Throw-ins",
            "Keep Possession",
            "Loss Possession",
            "Forward",
            "Fast",
            "Box Entry",
            "Win SP",
            "Switch Play",
            "Cross / Decoy Runs",
        ]
    ].copy()

    display_df = display_df.rename(
        columns={
            "Win SP":
                "Win Set Play",
        }
    )

    st.dataframe(
        display_df,
        hide_index=True,
        width="stretch",
    )

    if report_context is not None:
        report_item = create_table_report_item(
            module="throw_in",
            section_title="Zone Effectiveness",
            dataframe=display_df,
            context=report_context,
        )
        render_add_to_report_button(
            report_item,
            key=f"report_throw_zone_table_{report_item['id']}",
        )


# ============================================================
# MAIN RENDER
# ============================================================

def render_offensive_throw_in_analysis(
    analysis: dict,
    report_context: dict | None = None,
):
    records = analysis[
        "records"
    ]

    if not records:
        st.info(
            "No throw-in events found "
            "for the selected filters."
        )
        return

    kpis = (
        calculate_throw_in_kpis(
            records
        )
    )

    total = kpis[
        "total"
    ]

    retention_denominator = (
        kpis[
            "retention_coded"
        ]
    )

    forward_retention_denominator = (
        kpis[
            "forward_retention_coded"
        ]
    )

    st.subheader(
        "Throw-ins — Offensive"
    )

    render_create_report_button(
        "throw_in",
        key="create_throw_in_report",
    )

    # ========================================================
    # KEY KPIs
    # ========================================================

    st.markdown(
        "### KPIs Overview"
    )

    col1, col2, col3, col4 = (
        st.columns(4)
    )

    with col1:
        st.metric(
            "Total Throw-ins",
            total,
        )

    with col2:
        st.metric(
            "Retention Rate",
            format_rate(
                kpis[
                    "kept"
                ],
                retention_denominator,
            ),
        )

    with col3:
        st.metric(
            "Forward Throw Rate",
            format_rate(
                kpis[
                    "forward"
                ],
                total,
            ),
        )

    with col4:
        st.metric(
            "Forward Retention",
            format_rate(
                kpis[
                    "forward_kept"
                ],
                forward_retention_denominator,
            ),
            help=(
                "Keep Possession rate for "
                "throw-ins coded FORWARD."
            ),
        )

    col5, col6, col7, col8 = (
        st.columns(4)
    )

    with col5:
        st.metric(
            "Box Entry Rate",
            format_rate(
                kpis[
                    "box_entry"
                ],
                total,
            ),
        )

    with col6:
        st.metric(
            "Set Play Won",
            format_rate(
                kpis[
                    "win_set_play"
                ],
                total,
            ),
        )

    with col7:
        st.metric(
            "Most Common Zone",
            kpis[
                "most_common_zone"
            ],
            help=(
                f"{kpis['zone_count']}/{total} "
                f"throw-ins"
            ),
        )

    with col8:
        st.metric(
            "Most Common Taker",
            kpis[
                "most_common_taker"
            ],
            help=(
                f"{kpis['taker_count']}/{total} "
                f"throw-ins"
            ),
        )

    col9, col10 = (
        st.columns(2)
    )

    with col9:
        st.metric(
            "Most Common Length",
            kpis[
                "most_common_length"
            ],
            help=(
                f"{kpis['length_count']}/{total} "
                f"throw-ins"
            ),
        )

    with col10:
        st.metric(
            "Most Common Speed",
            kpis[
                "most_common_speed"
            ],
            help=(
                f"{kpis['speed_count']}/{total} "
                f"throw-ins"
            ),
        )

    if (
        retention_denominator
        < total
    ):
        st.caption(
            f"Retention is coded for "
            f"{retention_denominator}/{total} "
            f"of the currently filtered throw-ins."
        )

    if report_context is not None:
        kpi_item = create_kpi_report_item(
            module="throw_in",
            section_title="KPIs Overview",
            context=report_context,
            kpis=[
                {"label": "Total Throw-ins", "value": str(total)},
                {"label": "Retention Rate", "value": format_rate(kpis["kept"], retention_denominator)},
                {"label": "Forward Throw Rate", "value": format_rate(kpis["forward"], total)},
                {"label": "Forward Retention", "value": format_rate(kpis["forward_kept"], forward_retention_denominator)},
                {"label": "Box Entry Rate", "value": format_rate(kpis["box_entry"], total)},
                {"label": "Set Play Won", "value": format_rate(kpis["win_set_play"], total)},
                {"label": "Most Common Zone", "value": kpis["most_common_zone"]},
                {"label": "Most Common Taker", "value": kpis["most_common_taker"]},
                {"label": "Most Common Length", "value": kpis["most_common_length"]},
                {"label": "Most Common Speed", "value": kpis["most_common_speed"]},
            ],
            notes=(
                [
                    f"Retention is coded for {retention_denominator}/{total} of the currently filtered throw-ins."
                ]
                if retention_denominator < total
                else []
            ),
        )
        render_add_to_report_button(
            kpi_item,
            key=f"report_throw_kpis_{kpi_item['id']}",
        )

    # ========================================================
    # PLAYER ANALYSIS — WHO TAKES THE THROW
    # ========================================================

    st.markdown("---")

    render_player_comparison(
        records,
        report_context=report_context,
    )

    # ========================================================
    # ZONE EFFECTIVENESS — WHERE THE THROW STARTS
    # ========================================================

    st.markdown("---")

    render_zone_effectiveness(
        records,
        report_context=report_context,
    )

    # ========================================================
    # EXECUTION EFFECTIVENESS — HOW THE THROW IS EXECUTED
    # ========================================================

    st.markdown("---")

    st.markdown(
        "### Execution Effectiveness"
    )

    direction_df = (
        build_effectiveness_dataframe(
            records,
            "direction",
        )
    )

    speed_df = (
        build_effectiveness_dataframe(
            records,
            "speed",
        )
    )

    length_df = (
        build_effectiveness_dataframe(
            records,
            "length",
        )
    )

    tab1, tab2, tab3 = (
        st.tabs(
            [
                "Direction",
                "Speed",
                "Length",
            ]
        )
    )

    with tab1:
        render_effectiveness_chart(
            "Direction Effectiveness",
            direction_df,
            report_context=report_context,
        )

    with tab2:
        render_effectiveness_chart(
            "Speed Effectiveness",
            speed_df,
            report_context=report_context,
        )

    with tab3:
        render_effectiveness_chart(
            "Length Effectiveness",
            length_df,
            report_context=report_context,
        )

    # ========================================================
    # RETENTION BY ZONE — IMMEDIATE OUTCOME
    # ========================================================

    st.markdown("---")

    render_retention_by_zone(
        records,
        report_context=report_context,
    )

    # ========================================================
    # RESULT BREAKDOWN — FINAL RESULT
    # ========================================================

    st.markdown("---")

    render_result_breakdown(
        records,
        report_context=report_context,
    )

# ============================================================
# DEFENSIVE THROW-INS
# ============================================================

OPP_POSS = "OPP POSS"
WIN_POSS = "WIN POSS"

ACTIVE_PRESS = "ACTIVE PRESS"
UNORGANIZED_LATE = "UNORGANIZED/LATE"

SWITCH_PLAY_OPP = "SWITCH PLAY OPP"
WIN_SET_PLAY_OPP = "WIN SP OPP (TI,FK,CK)"
ATTACK_SPACE_OPP = "ATTACK SPACE OPP"
BOX_ENTRY_OPP = "BOX ENTRY OPP"
COUNTER_LAUNCHED = "COUNTER LAUNCHED"

# Sportscode panel wording can vary slightly between versions/templates.
# These aliases keep the analysis robust without changing the raw XML values.
DEFENSIVE_RESULT_ALIASES = {
    "Switch Play Opp": ["SWITCH PLAY OPP"],
    "Win Set Play Opp": [
        "WIN SP OPP (TI,FK,CK)",
        "WIN SP OPP",
    ],
    "Attack Space Opp": ["ATTACK SPACE OPP"],
    "Box Entry Opp": ["BOX ENTRY OPP"],
    "Finishing Opp": [
        "FINISHING OFF",
        "FINISHING OPP",
        "FINISHING",
    ],
    "Counter Launched": ["COUNTER LAUNCHED"],
}


def count_events_with_any_value(
    records: list[dict],
    key: str,
    target_values: list[str],
) -> int:
    """Count events that contain at least one of the requested values."""
    return sum(
        1
        for record in records
        if any(
            event_has_value(record, key, target)
            for target in target_values
        )
    )


def _defensive_retention_metrics(
    records: list[dict],
) -> dict:
    coded_records = [
        record
        for record in records
        if get_record_category_values(record, "retention")
    ]

    denominator = len(coded_records)

    opponent_possession = count_events_with_value(
        coded_records,
        "retention",
        OPP_POSS,
    )
    possession_won = count_events_with_value(
        coded_records,
        "retention",
        WIN_POSS,
    )

    return {
        "coded": denominator,
        "opp_poss": opponent_possession,
        "win_poss": possession_won,
        "opp_poss_rate": calculate_rate(opponent_possession, denominator),
        "win_poss_rate": calculate_rate(possession_won, denominator),
    }


def calculate_defensive_throw_in_kpis(
    records: list[dict],
) -> dict:
    total = len(records)
    retention = _defensive_retention_metrics(records)

    most_common_zone, zone_count = get_most_common_value(
        records,
        "throw_in_zone",
    )
    most_common_length, length_count = get_most_common_value(
        records,
        "length",
    )
    most_common_speed, speed_count = get_most_common_value(
        records,
        "speed",
    )
    most_common_pressing, pressing_count = get_most_common_value(
        records,
        "pressing",
    )

    return {
        "total": total,
        "retention_coded": retention["coded"],
        "opp_poss": retention["opp_poss"],
        "win_poss": retention["win_poss"],
        "counter_launched": count_events_with_any_value(
            records,
            "outcome",
            DEFENSIVE_RESULT_ALIASES["Counter Launched"],
        ),
        "box_entry_opp": count_events_with_any_value(
            records,
            "outcome",
            DEFENSIVE_RESULT_ALIASES["Box Entry Opp"],
        ),
        "finishing_opp": count_events_with_any_value(
            records,
            "outcome",
            DEFENSIVE_RESULT_ALIASES["Finishing Opp"],
        ),
        "win_set_play_opp": count_events_with_any_value(
            records,
            "outcome",
            DEFENSIVE_RESULT_ALIASES["Win Set Play Opp"],
        ),
        "most_common_zone": most_common_zone,
        "zone_count": zone_count,
        "most_common_length": most_common_length,
        "length_count": length_count,
        "most_common_speed": most_common_speed,
        "speed_count": speed_count,
        "most_common_pressing": most_common_pressing,
        "pressing_count": pressing_count,
    }


def build_defensive_effectiveness_dataframe(
    records: list[dict],
    group_key: str,
) -> pd.DataFrame:
    categories = count_categories(records, group_key)
    rows = []

    for category in categories:
        category_records = records_with_category(
            records,
            group_key,
            category,
        )
        total = len(category_records)
        retention = _defensive_retention_metrics(category_records)
        retention_coded = retention["coded"]

        active_press = count_events_with_value(
            category_records,
            "pressing",
            ACTIVE_PRESS,
        )
        counter_launched = count_events_with_any_value(
            category_records,
            "outcome",
            DEFENSIVE_RESULT_ALIASES["Counter Launched"],
        )
        box_entry = count_events_with_any_value(
            category_records,
            "outcome",
            DEFENSIVE_RESULT_ALIASES["Box Entry Opp"],
        )
        finishing = count_events_with_any_value(
            category_records,
            "outcome",
            DEFENSIVE_RESULT_ALIASES["Finishing Opp"],
        )
        win_sp = count_events_with_any_value(
            category_records,
            "outcome",
            DEFENSIVE_RESULT_ALIASES["Win Set Play Opp"],
        )

        rows.append(
            {
                "Category": category,
                "Throw-ins Faced": total,
                "Retention Coded": retention_coded,
                "Win Possession %": calculate_rate(
                    retention["win_poss"],
                    retention_coded,
                ),
                "Win Possession": format_rate(
                    retention["win_poss"],
                    retention_coded,
                ),
                "Opp Possession %": calculate_rate(
                    retention["opp_poss"],
                    retention_coded,
                ),
                "Opp Possession": format_rate(
                    retention["opp_poss"],
                    retention_coded,
                ),
                "Active Press %": calculate_rate(active_press, total),
                "Active Press": format_rate(active_press, total),
                "Counter Launched %": calculate_rate(counter_launched, total),
                "Counter Launched": format_rate(counter_launched, total),
                "Box Entry Opp %": calculate_rate(box_entry, total),
                "Box Entry Opp": format_rate(box_entry, total),
                "Finishing Opp %": calculate_rate(finishing, total),
                "Finishing Opp": format_rate(finishing, total),
                "Win Set Play Opp %": calculate_rate(win_sp, total),
                "Win Set Play Opp": format_rate(win_sp, total),
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    return (
        df
        .sort_values(
            ["Throw-ins Faced", "Category"],
            ascending=[False, True],
        )
        .reset_index(drop=True)
    )


def render_defensive_effectiveness_table(
    title: str,
    df: pd.DataFrame,
    report_context: dict | None = None,
):
    st.markdown(f"#### {title}")

    if df.empty:
        st.info("No defensive throw-in data available for this section.")
        return

    display_df = df[
        [
            "Category",
            "Throw-ins Faced",
            "Win Possession",
            "Opp Possession",
            "Active Press",
            "Counter Launched",
            "Box Entry Opp",
            "Finishing Opp",
            "Win Set Play Opp",
        ]
    ].copy()

    st.dataframe(
        display_df,
        hide_index=True,
        width="stretch",
    )

    if report_context is not None:
        item = create_table_report_item(
            module="throw_in",
            section_title=title,
            dataframe=display_df,
            context=report_context,
        )
        render_add_to_report_button(
            item,
            key=f"report_throw_def_table_{title}_{item['id']}",
        )


def render_defensive_effectiveness_chart(
    title: str,
    df: pd.DataFrame,
    report_context: dict | None = None,
):
    """
    Defensive equivalent of the offensive effectiveness chart.

    The visual structure intentionally mirrors the offensive Throw-ins page:
    grouped bars first, followed by the detailed table.
    """
    st.markdown(f"#### {title}")

    if df.empty:
        st.info("No defensive throw-in data available for this section.")
        return

    chart_df = df[
        [
            "Category",
            "Win Possession %",
            "Box Entry Opp %",
            "Win Set Play Opp %",
        ]
    ].copy()

    chart_long = (
        chart_df
        .melt(
            id_vars=["Category"],
            value_vars=[
                "Win Possession %",
                "Box Entry Opp %",
                "Win Set Play Opp %",
            ],
            var_name="Metric",
            value_name="Percentage",
        )
    )

    chart_long["Metric"] = (
        chart_long["Metric"]
        .replace(
            {
                "Win Possession %": "Win Possession",
                "Box Entry Opp %": "Box Entry Opp",
                "Win Set Play Opp %": "Win Set Play Opp",
            }
        )
    )

    display_lookup = {}

    for _, row in df.iterrows():
        category = str(row["Category"])

        display_lookup[
            (category, "Win Possession")
        ] = row["Win Possession"]

        display_lookup[
            (category, "Box Entry Opp")
        ] = row["Box Entry Opp"]

        display_lookup[
            (category, "Win Set Play Opp")
        ] = row["Win Set Play Opp"]

    chart_long["Display"] = [
        display_lookup.get(
            (str(category), str(metric)),
            "",
        )
        for category, metric in zip(
            chart_long["Category"],
            chart_long["Metric"],
        )
    ]

    defensive_grayscale = {
        "Win Possession": "#404040",
        "Box Entry Opp": "#A0A0A0",
        "Win Set Play Opp": "#FFFFFF",
    }

    fig = px.bar(
        chart_long,
        x="Category",
        y="Percentage",
        color="Metric",
        barmode="group",
        text="Display",
        color_discrete_map=defensive_grayscale,
    )

    fig.update_traces(
        textposition="outside",
        cliponaxis=False,
        textfont=dict(
            size=12,
        ),
    )

    fig.update_layout(
        height=390,
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
                115,
            ]
        ),
        legend_title="",
    )

    st.plotly_chart(
        fig,
        width="stretch",
    )

    if report_context is not None:
        pdf_fig = _build_pdf_labeled_bar_figure(
            df,
            [
                (
                    "Win Possession %",
                    "Win Possession",
                    "Win Possession",
                ),
                (
                    "Box Entry Opp %",
                    "Box Entry Opp",
                    "Box Entry Opp",
                ),
                (
                    "Win Set Play Opp %",
                    "Win Set Play Opp",
                    "Win Set Play Opp",
                ),
            ],
        )

        report_item = create_plotly_report_item(
            module="throw_in",
            section_title=title,
            figure=pdf_fig,
            context=report_context,
        )

        render_add_to_report_button(
            report_item,
            key=(
                "report_throw_def_effectiveness_"
                f"{title}_{report_item['id']}"
            ),
        )

    display_df = df[
        [
            "Category",
            "Throw-ins Faced",
            "Win Possession",
            "Opp Possession",
            "Active Press",
            "Counter Launched",
            "Box Entry Opp",
            "Finishing Opp",
            "Win Set Play Opp",
        ]
    ].copy()

    st.dataframe(
        display_df,
        hide_index=True,
        width="stretch",
    )

    if report_context is not None:
        table_item = create_table_report_item(
            module="throw_in",
            section_title=f"{title} — Table",
            dataframe=display_df,
            context=report_context,
        )

        render_add_to_report_button(
            table_item,
            key=(
                "report_throw_def_effectiveness_table_"
                f"{title}_{table_item['id']}"
            ),
        )


def render_defensive_retention_by_zone(
    records: list[dict],
    report_context: dict | None = None,
):
    st.markdown("### Possession Outcome by Zone")

    df = build_defensive_effectiveness_dataframe(
        records,
        "throw_in_zone",
    )

    if df.empty:
        st.info("No defensive throw-in zone data available.")
        return

    # Keep the same pitch progression used throughout the Throw-ins module:
    # DEF -> PRE-DEF -> PRE-OFF -> OFF.
    zone_rank = {
        zone: index
        for index, zone in enumerate(
            THROW_IN_ZONE_ORDER
        )
    }

    df = (
        df.assign(
            _zone_order=df["Category"].map(
                zone_rank
            ).fillna(
                len(
                    THROW_IN_ZONE_ORDER
                )
            )
        )
        .sort_values(
            [
                "_zone_order",
                "Category",
            ]
        )
        .drop(
            columns=[
                "_zone_order",
            ]
        )
        .reset_index(
            drop=True
        )
    )

    fig = go.Figure()

    # Win Possession is intentionally the lower segment.
    fig.add_bar(
        x=df["Category"],
        y=df["Win Possession %"],
        name="Win Possession",
        marker_color="#404040",
        text=df["Win Possession"],
        textposition="inside",
    )

    # Opponent Possession is stacked above Win Possession.
    fig.add_bar(
        x=df["Category"],
        y=df["Opp Possession %"],
        name="Opponent Possession",
        marker_color="#C8C8C8",
        text=df["Opp Possession"],
        textposition="inside",
    )

    fig.add_trace(
        go.Scatter(
            x=df["Category"],
            y=df["Counter Launched %"],
            mode="lines+markers+text",
            name="Counter Launched",
            text=df["Counter Launched"],
            textposition="top center",
            line=dict(
                width=5,
                color="#FFD54F",
            ),
            marker=dict(
                size=12,
                color="#FFD54F",
                line=dict(
                    width=2,
                    color="white",
                ),
            ),
            yaxis="y2",
        )
    )

    fig.update_layout(
        barmode="stack",
        height=430,
        margin=dict(
            l=20,
            r=260,
            t=10,
            b=20,
        ),
        xaxis_title="",
        xaxis=dict(
            categoryorder="array",
            categoryarray=[
                zone
                for zone in THROW_IN_ZONE_ORDER
                if zone in set(
                    df["Category"]
                )
            ],
        ),
        yaxis_title=(
            "Possession Outcome (%)"
        ),
        yaxis=dict(
            range=[
                0,
                100,
            ]
        ),
        yaxis2=dict(
            title=dict(
                text=(
                    "Counter Launched Rate (%)"
                ),
                font=dict(
                    color="#FFD54F"
                ),
            ),
            range=[
                0,
                100,
            ],
            overlaying="y",
            side="right",
            showgrid=False,
            tickfont=dict(
                color="#FFD54F"
            ),
        ),
        legend_title="",
        legend=dict(
            x=1.16,
            xanchor="left",
            y=1.0,
            yanchor="top",
            traceorder="normal",
            bgcolor="rgba(0,0,0,0.35)",
        ),
    )

    st.plotly_chart(
        fig,
        width="stretch",
    )

    if report_context is not None:
        item = create_plotly_report_item(
            module="throw_in",
            section_title=(
                "Defensive Possession Outcome by Zone"
            ),
            figure=fig,
            context=report_context,
        )
        render_add_to_report_button(
            item,
            key=(
                "report_throw_def_ret_zone_"
                f"{item['id']}"
            ),
        )


def build_defensive_result_dataframe(
    records: list[dict],
) -> pd.DataFrame:
    total = len(records)
    rows = []

    for label, aliases in DEFENSIVE_RESULT_ALIASES.items():
        count = count_events_with_any_value(
            records,
            "outcome",
            aliases,
        )
        rows.append(
            {
                "Outcome": label,
                "Count": count,
                "Percentage": calculate_rate(count, total),
                "Display": format_rate(count, total),
            }
        )

    df = pd.DataFrame(rows)
    return (
        df
        .sort_values("Percentage", ascending=True)
        .reset_index(drop=True)
    )


def render_defensive_result_breakdown(
    records: list[dict],
    report_context: dict | None = None,
):
    st.markdown("### Defensive Outcome Breakdown")

    df = build_defensive_result_dataframe(records)

    fig = px.bar(
        df,
        x="Percentage",
        y="Outcome",
        orientation="h",
        text="Display",
    )
    fig.update_traces(
        textposition="outside",
        cliponaxis=False,
        marker_color="#787878",
    )
    fig.update_layout(
        height=max(300, 55 * len(df)),
        margin=dict(l=20, r=130, t=10, b=20),
        xaxis_title="Throw-in Faced Rate (%)",
        yaxis_title="",
        xaxis=dict(range=[0, 110]),
        showlegend=False,
    )

    st.plotly_chart(fig, width="stretch")
    st.caption(
        "Defensive outcome labels are not assumed to be mutually exclusive. "
        "One opponent throw-in can contain more than one outcome label."
    )

    if report_context is not None:
        item = create_plotly_report_item(
            module="throw_in",
            section_title="Defensive Outcome Breakdown",
            figure=fig,
            context=report_context,
            notes=[
                "Defensive outcome labels are not assumed to be mutually exclusive."
            ],
        )
        render_add_to_report_button(
            item,
            key=f"report_throw_def_results_{item['id']}",
        )


def render_defensive_throw_in_analysis(
    analysis: dict,
    report_context: dict | None = None,
):
    records = analysis["records"]

    if not records:
        st.info("No defensive throw-in events found for the selected filters.")
        return

    kpis = calculate_defensive_throw_in_kpis(records)
    total = kpis["total"]
    retention_denominator = kpis["retention_coded"]

    st.subheader("Throw-ins — Defensive")

    render_create_report_button(
        "throw_in",
        key="create_throw_in_defensive_report",
    )

    st.markdown("### KPIs Overview")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Throw-ins Faced", total)
    with c2:
        st.metric(
            "Win Possession",
            format_rate(kpis["win_poss"], retention_denominator),
        )
    with c3:
        st.metric(
            "Counter Launched",
            format_rate(kpis["counter_launched"], total),
        )
    with c4:
        st.metric(
            "Box Entry Opp",
            format_rate(kpis["box_entry_opp"], total),
        )

    c5, c6, c7, c8 = st.columns(4)
    with c5:
        st.metric(
            "Finishing Opp",
            format_rate(kpis["finishing_opp"], total),
        )
    with c6:
        st.metric(
            "Set Play Won Opp",
            format_rate(kpis["win_set_play_opp"], total),
        )
    with c7:
        st.metric(
            "Most Common Zone",
            kpis["most_common_zone"],
            help=f"{kpis['zone_count']}/{total} opponent throw-ins",
        )
    with c8:
        st.metric(
            "Most Common Pressing",
            kpis["most_common_pressing"],
            help=f"{kpis['pressing_count']}/{total} opponent throw-ins",
        )

    c9, c10 = st.columns(2)
    with c9:
        st.metric(
            "Most Common Length",
            kpis["most_common_length"],
            help=f"{kpis['length_count']}/{total} opponent throw-ins",
        )
    with c10:
        st.metric(
            "Most Common Speed",
            kpis["most_common_speed"],
            help=f"{kpis['speed_count']}/{total} opponent throw-ins",
        )

    if retention_denominator < total:
        st.caption(
            f"Defensive retention is coded for {retention_denominator}/{total} "
            "of the currently filtered opponent throw-ins."
        )

    if report_context is not None:
        item = create_kpi_report_item(
            module="throw_in",
            section_title="Defensive KPIs Overview",
            context=report_context,
            kpis=[
                {"label": "Throw-ins Faced", "value": str(total)},
                {"label": "Win Possession", "value": format_rate(kpis["win_poss"], retention_denominator)},
                {"label": "Counter Launched", "value": format_rate(kpis["counter_launched"], total)},
                {"label": "Box Entry Opp", "value": format_rate(kpis["box_entry_opp"], total)},
                {"label": "Finishing Opp", "value": format_rate(kpis["finishing_opp"], total)},
                {"label": "Set Play Won Opp", "value": format_rate(kpis["win_set_play_opp"], total)},
                {"label": "Most Common Zone", "value": kpis["most_common_zone"]},
                {"label": "Most Common Pressing", "value": kpis["most_common_pressing"]},
                {"label": "Most Common Length", "value": kpis["most_common_length"]},
                {"label": "Most Common Speed", "value": kpis["most_common_speed"]},
            ],
        )
        render_add_to_report_button(
            item,
            key=f"report_throw_def_kpis_{item['id']}",
        )

    # Where the opponent throw starts
    st.markdown("---")
    zone_df = build_defensive_effectiveness_dataframe(
        records,
        "throw_in_zone",
    )
    render_defensive_effectiveness_table(
        "Zone Effectiveness",
        zone_df,
        report_context=report_context,
    )

    # How the opponent throw is executed
    st.markdown("---")
    st.markdown("### Execution Effectiveness")

    direction_df = build_defensive_effectiveness_dataframe(records, "direction")
    speed_df = build_defensive_effectiveness_dataframe(records, "speed")
    length_df = build_defensive_effectiveness_dataframe(records, "length")

    tab1, tab2, tab3 = st.tabs(["Direction", "Speed", "Length"])
    with tab1:
        render_defensive_effectiveness_chart(
            "Direction Effectiveness",
            direction_df,
            report_context=report_context,
        )
    with tab2:
        render_defensive_effectiveness_chart(
            "Speed Effectiveness",
            speed_df,
            report_context=report_context,
        )
    with tab3:
        render_defensive_effectiveness_chart(
            "Length Effectiveness",
            length_df,
            report_context=report_context,
        )

    # Pressing response
    st.markdown("---")
    pressing_df = build_defensive_effectiveness_dataframe(records, "pressing")
    render_defensive_effectiveness_chart(
        "Pressing Effectiveness",
        pressing_df,
        report_context=report_context,
    )

    # Immediate possession outcome by field zone
    st.markdown("---")
    render_defensive_retention_by_zone(
        records,
        report_context=report_context,
    )

    # Final coded outcomes
    st.markdown("---")
    render_defensive_result_breakdown(
        records,
        report_context=report_context,
    )


def _get_throw_in_phase(
    analysis: dict,
    records: list[dict],
) -> str:
    """Resolve phase without requiring a change to the existing caller."""
    phase = analysis.get("phase")
    if phase:
        return _normalize_text(phase).lower()

    for record in records:
        record_phase = record.get("phase")
        if record_phase:
            return _normalize_text(record_phase).lower()

        code = _normalize_text(record.get("code"))
        if code == "16 THROW IN OPP":
            return "defensive"
        if code == "12 THROW IN":
            return "offensive"

    # Preserve the behaviour of the existing dashboard for old data/callers.
    return "offensive"


def render_throw_in_analysis(
    analysis: dict,
    report_context: dict | None = None,
):
    records = analysis.get("records", [])
    phase = _get_throw_in_phase(analysis, records)

    if phase == "defensive":
        render_defensive_throw_in_analysis(
            analysis,
            report_context=report_context,
        )
        return

    render_offensive_throw_in_analysis(
        analysis,
        report_context=report_context,
    )

