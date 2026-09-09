from __future__ import annotations


FILTER_LABELS = {
    "half": "Half",
    "side": "Side",
    "taker": "Taker",
    "delivery_type": "Delivery Type",
    "delivery_zone": "Delivery Zone",
    "drop_zone": "Drop Zone",
    "first_contact": "First Contact",
    "outcome": "Outcome",
    "opponent_organization": "Opponent Organization",
    "opponent_players": "Opponent Players in Box",
    "direction": "Direction",
    "throw_in_zone": "Zone",
    "speed": "Speed",
    "length": "Length",
    "result": "Result",
    "retention": "Retention",
    "time_period": "Time Period",
    "attack_type": "Attack Type",
    "organized_attack_type": "Organized Attack Type",
    "attack_zone": "Attack Zone",
    "set_play_type": "Set Play Type",
    "corner_kick_type": "Corner Kick Type",
    "free_kick_type": "Free Kick Type",
    "passes": "Passes",
    "pass_type": "Pass Type",
    "touches": "Touches",
    "recovery_zone": "Recovery Zone",
    "recovery_player": "Recovery Player",
    "assist_zone": "Assist Zone",
    "final_attempt_zone": "Final Attempt Zone",
    "final_attempt_player": "Final Attempt Player",
    "assist": "Assist",
    "second_assist": "Pre-Assist / 2nd Assist",
}

INACTIVE_TEXT_VALUES = {
    "",
    "ALL",
    "ALL MATCHES",
    "NONE",
}


def _clean_filter_value(
    value,
):
    if value is None:
        return None

    if isinstance(
        value,
        (list, tuple, set),
    ):
        cleaned = []

        for item in value:
            cleaned_item = (
                _clean_filter_value(
                    item
                )
            )

            if cleaned_item is None:
                continue

            cleaned.append(
                cleaned_item
            )

        return cleaned or None

    if isinstance(value, str):
        text = value.strip()

        if (
            not text
            or text.upper()
            in INACTIVE_TEXT_VALUES
        ):
            return None

        return text

    return value


def clean_active_filters(
    filters: dict | None,
) -> dict:
    cleaned_filters = {}

    for key, value in (
        filters
        or {}
    ).items():
        cleaned_value = (
            _clean_filter_value(
                value
            )
        )

        if cleaned_value is None:
            continue

        label = FILTER_LABELS.get(
            key,
            key.replace(
                "_",
                " ",
            ).title(),
        )

        cleaned_filters[
            label
        ] = cleaned_value

    return cleaned_filters


def build_report_context(
    *,
    event_family: str,
    analysis_name: str,
    scope: str,
    phase: str | None,
    competition: str | None = None,
    match: str | None = None,
    matches: list[str] | None = None,
    filters: dict | None = None,
) -> dict:
    clean_matches = []

    for match_name in (
        matches
        or []
    ):
        cleaned = _clean_filter_value(
            match_name
        )

        if cleaned is not None:
            clean_matches.append(
                cleaned
            )

    context = {
        "event_family": event_family,
        "analysis_name": analysis_name,
        "scope": scope,
        "phase": (
            str(phase).title()
            if phase
            else None
        ),
        "competition": _clean_filter_value(
            competition
        ),
        "match": _clean_filter_value(
            match
        ),
        "matches": clean_matches,
        "filters": clean_active_filters(
            filters
        ),
    }

    return context
