from collections import Counter

from src.data.data_loader import (
    load_event_labels,
    load_events,
    load_events_for_matches,
    load_matches,
    load_matches_all,
)


# ============================================================
# BASIC HELPERS
# ============================================================

def as_list(value):
    if value is None:
        return []

    if isinstance(value, list):
        return value

    return [value]


# ============================================================
# EVENT-LEVEL VALUE HELPERS
# ============================================================

def event_has_value(
    record: dict,
    key: str,
    target_value,
) -> bool:
    """
    Check whether one analytical EVENT contains a value.

    A field may contain either:
    - one value
    - multiple values in a list

    The event itself is never duplicated.
    """

    value = record.get(key)

    if value is None:
        return False

    if isinstance(value, list):
        return target_value in value

    return value == target_value


def event_has_any_value(
    record: dict,
    key: str,
    target_values,
) -> bool:
    """
    True if the event contains at least one target value.
    """

    return any(
        event_has_value(
            record,
            key,
            target_value,
        )
        for target_value
        in target_values
    )


def count_events_with_value(
    records: list[dict],
    key: str,
    target_value,
) -> int:
    """
    Count EVENTS containing a value.
    """

    return sum(
        1
        for record in records
        if event_has_value(
            record,
            key,
            target_value,
        )
    )


def count_events_with_any_values(
    records: list[dict],
    key: str,
    target_values,
) -> int:
    """
    Count EVENTS containing at least one target value.
    """

    return sum(
        1
        for record in records
        if event_has_any_value(
            record,
            key,
            target_values,
        )
    )


# ============================================================
# FLATTENED LABEL HELPERS
# ============================================================

def get_values(
    records: list[dict],
    key: str,
) -> list:
    """
    Flatten values for category/distribution analysis.

    Important:
    This is label-oriented.

    Do not use len(get_values(...)) as an event denominator
    when one event can contain multiple values.
    """

    values = []

    for record in records:

        value = record.get(key)

        if value is None:
            continue

        if isinstance(value, list):

            values.extend(
                item
                for item in value
                if item is not None
            )

        else:

            values.append(
                value
            )

    return values


def count_value(
    records: list[dict],
    key: str,
    target_value,
) -> int:
    """
    Count flattened label occurrences.

    For event-based KPIs prefer:
        count_events_with_value()
    """

    return sum(
        1
        for value in get_values(
            records,
            key,
        )
        if value == target_value
    )


def value_counts(
    records: list[dict],
    key: str,
) -> Counter:

    return Counter(
        get_values(
            records,
            key,
        )
    )


def most_common_value(
    records: list[dict],
    key: str,
):
    counts = value_counts(
        records,
        key,
    )

    if not counts:
        return None, 0

    return counts.most_common(1)[0]


# ============================================================
# PERCENTAGE HELPERS
# ============================================================

def percentage(
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


def format_percentage(
    numerator: int,
    denominator: int,
    decimals: int = 0,
) -> str:

    if denominator == 0:
        return "0% (0/0)"

    rate = percentage(
        numerator,
        denominator,
    )

    return (
        f"{rate:.{decimals}f}% "
        f"({numerator}/{denominator})"
    )


# ============================================================
# BUILD ANALYTICAL RECORDS
# ============================================================

def build_analysis(
    data: dict,
) -> list[dict]:
    """
    Build exactly ONE analytical record per Sportscode event.

    Expected input:

    {
        "events": [...],
        "labels": [...]
    }

    CRITICAL RULE
    -------------
    One XML <instance> = one event.

    If an event contains repeated values for the same
    analytical group, those values are stored as a list.

    Example:

    RESULT:
        CROSS/DECOY RUNS
        SWITCH PLAY
        BOX ENTRY

    becomes:

    {
        "result": [
            "CROSS/DECOY RUNS",
            "SWITCH PLAY",
            "BOX ENTRY"
        ]
    }

    The event still counts only once.
    """

    events = data.get(
        "events",
        [],
    )

    labels = data.get(
        "labels",
        [],
    )

    if not events:
        return []

    # --------------------------------------------------------
    # ONE RECORD PER EVENT
    # --------------------------------------------------------

    records_by_event_id = {}

    for event in events:

        event_id = event.get(
            "id"
        )

        if event_id is None:
            continue

        records_by_event_id[
            event_id
        ] = dict(event)

    # --------------------------------------------------------
    # ADD LABELS TO THE EVENT
    # --------------------------------------------------------

    for label in labels:

        event_id = label.get(
            "event_id"
        )

        if (
            event_id
            not in records_by_event_id
        ):
            continue

        group_key = label.get(
            "group_key"
        )

        # Group-less Sportscode labels remain preserved
        # in the raw DB but are not promoted analytically.
        if not group_key:
            continue

        value = label.get(
            "value"
        )

        if value is None:
            continue

        record = (
            records_by_event_id[
                event_id
            ]
        )

        existing_value = record.get(
            group_key
        )

        # ----------------------------------------------------
        # FIRST VALUE
        # ----------------------------------------------------

        if existing_value is None:

            record[
                group_key
            ] = value

            continue

        # ----------------------------------------------------
        # ALREADY MULTI-VALUE
        # ----------------------------------------------------

        if isinstance(
            existing_value,
            list,
        ):

            if (
                value
                not in existing_value
            ):
                existing_value.append(
                    value
                )

            continue

        # ----------------------------------------------------
        # SECOND DISTINCT VALUE
        # ----------------------------------------------------

        if existing_value != value:

            record[
                group_key
            ] = [
                existing_value,
                value,
            ]

    # --------------------------------------------------------
    # KEEP ORIGINAL EVENT ORDER
    # --------------------------------------------------------

    records = []

    for event in events:

        event_id = event.get(
            "id"
        )

        record = (
            records_by_event_id.get(
                event_id
            )
        )

        if record is not None:

            records.append(
                record
            )

    return records


# ============================================================
# LOAD LABELS FOR EVENTS
# ============================================================

def load_labels_for_events(
    events: list[dict],
) -> list[dict]:

    if not events:
        return []

    event_ids = [
        event["id"]
        for event in events
        if event.get(
            "id"
        ) is not None
    ]

    if not event_ids:
        return []

    return load_event_labels(
        event_ids
    )


# ============================================================
# STANDARD ANALYSIS OBJECT
# ============================================================

def make_analysis(
    events: list[dict],
) -> dict:

    if not events:

        return {
            "events": [],
            "labels": [],
            "records": [],
        }

    labels = (
        load_labels_for_events(
            events
        )
    )

    records = build_analysis(
        {
            "events":
                events,

            "labels":
                labels,
        }
    )

    return {
        "events":
            events,

        "labels":
            labels,

        "records":
            records,
    }


# ============================================================
# ANALYSIS SCOPE
# ============================================================

def load_analysis_scope(
    scope: str,
    event_family: str,
    phase: str,
    match_id=None,
    competition_id=None,
    match_ids=None,
) -> dict:
    """
    Supported scopes:

    Match Analysis
    Competition Analysis
    All Matches Analysis
    """

    # ========================================================
    # MATCH
    # ========================================================

    if scope == "Match Analysis":

        if match_id is None:

            return {
                "events": [],
                "labels": [],
                "records": [],
            }

        events = load_events(
            match_id=match_id,
            event_family=event_family,
            phase=phase,
        )

        return make_analysis(
            events
        )

    # ========================================================
    # COMPETITION
    # ========================================================

    if scope == "Competition Analysis":

        if competition_id is None:

            return {
                "events": [],
                "labels": [],
                "records": [],
            }

        matches = load_matches(
            competition_id
        )

        match_ids = [
            match["id"]
            for match in matches
            if match.get(
                "id"
            ) is not None
        ]

        if not match_ids:

            return {
                "events": [],
                "labels": [],
                "records": [],
            }

        events = (
            load_events_for_matches(
                match_ids=match_ids,
                event_family=event_family,
                phase=phase,
            )
        )

        return make_analysis(
            events
        )

    # ========================================================
    # ALL MATCHES
    # ========================================================

    if scope == "All Matches Analysis":

        # Preserve the original behaviour:
        # match_ids=None means analyse every available match.
        if match_ids is None:

            matches = (
                load_matches_all()
            )

            match_ids = [
                match["id"]
                for match in matches
                if match.get(
                    "id"
                ) is not None
            ]

        else:

            match_ids = [
                selected_match_id
                for selected_match_id in match_ids
                if selected_match_id is not None
            ]

        if not match_ids:

            return {
                "events": [],
                "labels": [],
                "records": [],
            }

        events = (
            load_events_for_matches(
                match_ids=match_ids,
                event_family=event_family,
                phase=phase,
            )
        )

        return make_analysis(
            events
        )

    raise ValueError(
        f"Unknown analysis scope: {scope}"
    )