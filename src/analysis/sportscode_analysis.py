from collections import defaultdict

from src.data.data_loader import (
    load_sportscode_data,
)


def load_selected_analysis(
    match_id: int,
    event_family: str,
    phase: str,
) -> dict:
    events, labels = (
        load_sportscode_data(
            match_id=match_id,
            event_family=event_family,
            phase=phase,
        )
    )

    labels_by_event = (
        defaultdict(list)
    )

    for label in labels:
        labels_by_event[
            label["event_id"]
        ].append(
            label
        )

    return {
        "events":
            events,

        "labels":
            labels,

        "labels_by_event":
            dict(
                labels_by_event
            ),

        "event_count":
            len(events),
    }