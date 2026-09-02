import streamlit as st


def event_has_value(
    record: dict,
    key: str,
    target_value: str,
) -> bool:
    value = record.get(key)

    if value is None:
        return False

    if isinstance(value, list):
        return target_value in value

    return value == target_value


def calculate_corner_kick_kpi(
    records: list[dict],
) -> dict:
    total_events = len(records)

    won_events = sum(
        1
        for record in records
        if event_has_value(
            record,
            "first_contact",
            "1ST CONTACT WON",
        )
    )

    percentage = (
        won_events / total_events * 100
        if total_events
        else 0
    )

    return {
        "won_events": won_events,
        "total_events": total_events,
        "percentage": percentage,
    }


def render_corner_kick_analysis(
    analysis: dict,
    phase: str,
):
    kpi = calculate_corner_kick_kpi(
        analysis["records"]
    )

    st.metric(
        label="First Contact Won",
        value=f"{kpi['percentage']:.0f}%",
        help=(
            f"{kpi['won_events']} of "
            f"{kpi['total_events']} corner-kick events."
        ),
    )