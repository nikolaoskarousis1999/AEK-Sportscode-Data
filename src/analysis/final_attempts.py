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


def calculate_final_attempt_kpi(
    records: list[dict],
) -> dict:
    total_events = len(records)

    on_target_events = sum(
        1
        for record in records
        if event_has_value(
            record,
            "outcome",
            "ON TARGET",
        )
    )

    percentage = (
        on_target_events / total_events * 100
        if total_events
        else 0
    )

    return {
        "on_target_events": on_target_events,
        "total_events": total_events,
        "percentage": percentage,
    }


def render_final_attempt_analysis(
    analysis: dict,
):
    kpi = calculate_final_attempt_kpi(
        analysis["records"]
    )

    st.metric(
        label="On Target",
        value=f"{kpi['percentage']:.0f}%",
        help=(
            f"{kpi['on_target_events']} of "
            f"{kpi['total_events']} final-attempt events."
        ),
    )