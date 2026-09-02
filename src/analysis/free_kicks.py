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


def calculate_free_kick_kpi(
    records: list[dict],
    phase: str,
) -> dict:
    total_events = len(records)

    if phase == "offensive":
        target_value = "SHOT"
        label = "Shot Created"
    else:
        target_value = "SHOT CONCEDED"
        label = "Shot Conceded"

    matching_events = sum(
        1
        for record in records
        if event_has_value(
            record,
            "outcome",
            target_value,
        )
    )

    percentage = (
        matching_events / total_events * 100
        if total_events
        else 0
    )

    return {
        "label": label,
        "matching_events": matching_events,
        "total_events": total_events,
        "percentage": percentage,
    }


def render_free_kick_analysis(
    analysis: dict,
    phase: str,
):
    kpi = calculate_free_kick_kpi(
        records=analysis["records"],
        phase=phase,
    )

    st.metric(
        label=kpi["label"],
        value=f"{kpi['percentage']:.0f}%",
        help=(
            f"{kpi['matching_events']} of "
            f"{kpi['total_events']} free-kick events."
        ),
    )