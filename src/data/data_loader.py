from src.data.supabase_client import get_supabase_client


supabase = get_supabase_client()


def load_competitions() -> list[dict]:
    response = (
        supabase
        .table("competitions")
        .select("*")
        .order("name")
        .execute()
    )

    return response.data


def load_matches(
    competition_id: int,
) -> list[dict]:
    response = (
        supabase
        .table("matches")
        .select("*")
        .eq(
            "competition_id",
            competition_id,
        )
        .order("match_date")
        .execute()
    )

    return response.data


def load_matches_all() -> list[dict]:
    response = (
        supabase
        .table("matches")
        .select("*")
        .order("match_date")
        .execute()
    )

    return response.data


def load_events(
    match_id: int,
    event_family: str | None = None,
    phase: str | None = None,
) -> list[dict]:
    query = (
        supabase
        .table("sportscode_events")
        .select("*")
        .eq(
            "match_id",
            match_id,
        )
    )

    if event_family is not None:
        query = query.eq(
            "event_family",
            event_family,
        )

    if phase is not None:
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


def load_events_for_matches(
    match_ids: list[int],
    event_family: str | None = None,
    phase: str | None = None,
) -> list[dict]:
    if not match_ids:
        return []

    query = (
        supabase
        .table("sportscode_events")
        .select("*")
        .in_(
            "match_id",
            match_ids,
        )
    )

    if event_family is not None:
        query = query.eq(
            "event_family",
            event_family,
        )

    if phase is not None:
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

    response = (
        supabase
        .table("sportscode_event_labels")
        .select("*")
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
    event_family: str | None = None,
    phase: str | None = None,
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