from collections import defaultdict

from src.data.data_loader import (
    load_sportscode_data,
)


def load_selected_analysis(
    match_id: int,
    event_family: str,
    phase: str,
) -> dict:
    events, labels = load_sportscode_data(
        match_id=match_id,
        event_family=event_family,
        phase=phase,
    )

    labels_by_event = defaultdict(list)

    for label in labels:
        labels_by_event[
            label["event_id"]
        ].append(label)

    records = build_event_records(
        events=events,
        labels_by_event=labels_by_event,
    )

    return {
        "events": events,
        "labels": labels,
        "labels_by_event": dict(
            labels_by_event
        ),
        "records": records,
        "event_count": len(events),
    }


def build_event_records(
    events: list[dict],
    labels_by_event: dict,
) -> list[dict]:
    records = []

    for event in events:
        record = {
            "event_id": event["id"],
            "source_instance_id":
                event["source_instance_id"],
            "code": event["code"],
            "event_family":
                event["event_family"],
            "phase": event["phase"],
            "start_seconds":
                event["start_seconds"],
            "end_seconds":
                event["end_seconds"],
        }

        event_labels = labels_by_event.get(
            event["id"],
            [],
        )

        for label in event_labels:
            group_key = label["group_key"]
            value = label["value"]

            if group_key is None:
                continue

            if group_key not in record:
                record[group_key] = value
                continue

            existing_value = record[
                group_key
            ]

            if not isinstance(
                existing_value,
                list,
            ):
                record[group_key] = [
                    existing_value
                ]

            record[group_key].append(
                value
            )

        records.append(record)

    return records


def get_values(
    records: list[dict],
    key: str,
) -> list[str]:
    values = []

    for record in records:
        value = record.get(key)

        if value is None:
            continue

        if isinstance(value, list):
            values.extend(value)
        else:
            values.append(value)

    return values


def count_value(
    records: list[dict],
    key: str,
    target_value: str,
) -> int:
    values = get_values(
        records,
        key,
    )

    return sum(
        1
        for value in values
        if value == target_value
    )


def percentage(
    numerator: int,
    denominator: int,
) -> float:
    if denominator == 0:
        return 0.0

    return (
        numerator
        / denominator
    ) * 100