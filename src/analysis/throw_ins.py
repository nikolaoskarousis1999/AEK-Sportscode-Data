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


def calculate_throw_in_kpi(
    records: list[dict],
) -> dict:
    total_events = len(records)

    retained_events = sum(
        1
        for record in records
        if event_has_value(
            record,
            "retention",
            "KEEP POSS",
        )
    )

    percentage = (
        retained_events / total_events * 100
        if total_events
        else 0
    )

    return {
        "retained_events": retained_events,
        "total_events": total_events,
        "percentage": percentage,
    }


def render_throw_in_analysis(
    analysis: dict,
):
    kpi = calculate_throw_in_kpi(
        analysis["records"]
    )

    st.metric(
        label="Possession Retained",
        value=f"{kpi['percentage']:.0f}%",
        help=(
            f"{kpi['retained_events']} of "
            f"{kpi['total_events']} throw-in events."
        ),
    )