from src.data.supabase_client import (
    get_supabase_client,
)


def load_competitions() -> list[dict]:
    supabase = get_supabase_client()

    response = (
        supabase
        .table("competitions")
        .select("id,name")
        .order("id")
        .execute()
    )

    return response.data


def load_matches(
    competition_id: int,
) -> list[dict]:
    supabase = get_supabase_client()

    response = (
        supabase
        .table("matches")
        .select(
            "id,"
            "competition_id,"
            "match_date,"
            "opponent,"
            "venue,"
            "aek_score,"
            "opponent_score"
        )
        .eq(
            "competition_id",
            competition_id,
        )
        .order(
            "id"
        )
        .execute()
    )

    return response.data


def load_events(
    match_id: int,
    event_family: str | None = None,
    phase: str | None = None,
) -> list[dict]:
    supabase = get_supabase_client()

    query = (
        supabase
        .table("sportscode_events")
        .select(
            "id,"
            "match_id,"
            "import_id,"
            "source_instance_id,"
            "code,"
            "event_family,"
            "phase,"
            "start_seconds,"
            "end_seconds"
        )
        .eq(
            "match_id",
            match_id,
        )
    )

    if event_family:
        query = query.eq(
            "event_family",
            event_family,
        )

    if phase:
        query = query.eq(
            "phase",
            phase,
        )

    response = (
        query
        .order("start_seconds")
        .execute()
    )

    return response.data


def load_event_labels(
    event_ids: list[int],
) -> list[dict]:
    if not event_ids:
        return []

    supabase = get_supabase_client()

    response = (
        supabase
        .table("sportscode_event_labels")
        .select(
            "id,"
            "event_id,"
            "group_name_raw,"
            "group_key,"
            "value_raw,"
            "value,"
            "label_order"
        )
        .in_(
            "event_id",
            event_ids,
        )
        .order("event_id")
        .order("label_order")
        .execute()
    )

    return response.data


def load_sportscode_data(
    match_id: int,
    event_family: str,
    phase: str,
) -> tuple[list[dict], list[dict]]:
    events = load_events(
        match_id=match_id,
        event_family=event_family,
        phase=phase,
    )

    event_ids = [
        event["id"]
        for event in events
    ]

    labels = load_event_labels(
        event_ids
    )

    return events, labels