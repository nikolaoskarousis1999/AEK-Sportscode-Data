EVENT_CODE_MAP = {
    "09 Corner Kick": {
        "event_family": "corner_kick",
        "phase": "offensive",
    },

    "13 Corner Kick Opp": {
        "event_family": "corner_kick",
        "phase": "defensive",
    },

    "10 Free Kick": {
        "event_family": "free_kick",
        "phase": "offensive",
    },

    "14 Free Kick Opp": {
        "event_family": "free_kick",
        "phase": "defensive",
    },

    "12 Throw in": {
        "event_family": "throw_in",
        "phase": "offensive",
    },

    "sGoal": {
        "event_family": "final_attempt",
        "phase": "offensive",
    },

    "cGoal": {
        "event_family": "final_attempt",
        "phase": "defensive",
    },
}


GROUP_KEY_MAP = {
    "LOCATION": "location",

    "COMPETITION": "competition",
    "19 Competition": "competition",

    "TIME": "half",
    "01 Time": "time_period",

    "TEAM": "opponent",
    "TEAMS": "opponent",

    "OPP PLAYERS":
        "opponent_players",

    "OPP ORGANIZATION":
        "opponent_organization",

    "TAKER": "taker",
    "SIDE": "side",

    "DELIVERY TYPE":
        "delivery_type",

    "DROP ZONE":
        "drop_zone",

    "GK ACTION":
        "gk_action",

    "1 CONTACT":
        "first_contact",

    "OUTCOME":
        "outcome",

    "ORIGIN":
        "origin_zone",

    "DELIVERY":
        "delivery_zone",

    "FINISHING":
        "finishing_zone",

    "DIRECTION":
        "direction",

    "ZONES":
        "throw_in_zone",

    "SPEED":
        "speed",

    "LENGTH":
        "length",

    "RESULT":
        "result",

    "RETENTION":
        "retention",

    "15 Outcome":
        "outcome",

    "02 Type of attack":
        "attack_type",

    "16 Type of org. attack":
        "organized_attack_type",

    "13 Zone":
        "attack_zone",

    "03 Type of SP":
        "set_play_type",

    "17 Type of corner kick":
        "corner_kick_type",

    "18 Type of free kick c":
        "free_kick_type",

    "04 Passes":
        "passes",

    "05 Pass type":
        "pass_type",

    "06 Touches":
        "touches",

    "07 RecoveryZone":
        "recovery_zone",

    "08 Recovery Player":
        "recovery_player",

    "09 AssistZone":
        "assist_zone",

    "10 FAttZone":
        "final_attempt_zone",

    "11 Scorer":
        "final_attempt_player",

    "12 Assist":
        "assist",

    "14 2nd Assist":
        "second_assist",

    "20 Venue":
        "venue",
}


# ============================================================
# VALUE NORMALIZATION
# ============================================================

SET_PLAY_TYPE_VALUE_MAP = {
    "FREE KICK C":
        "Free Kick Cross",

    "FREE KICK CROSS":
        "Free Kick Cross",

    "FREE KICK D":
        "Free Kick Direct",

    "FREE KICK DIRECT":
        "Free Kick Direct",

    "CORNER KICK":
        "Corner Kick",

    "PENALTY KICK":
        "Penalty Kick",

    "THROW IN":
        "Throw In",
}


def normalize_group_value(
    group_key: str | None,
    value: str | None,
) -> str | None:
    """
    Normalize selected Sportscode label values while keeping
    all unrelated raw values unchanged.

    This should be called by the parser/importer after the raw
    Sportscode group name has been converted with GROUP_KEY_MAP.
    """
    if value is None:
        return None

    cleaned_value = str(value).strip()

    if not cleaned_value:
        return cleaned_value

    if group_key == "set_play_type":
        return SET_PLAY_TYPE_VALUE_MAP.get(
            cleaned_value.upper(),
            cleaned_value,
        )

    return cleaned_value


COMPETITION_NAME_MAP = {
    "CHAMPIONS LEAGUE":
        "Champions League",

    "SUPERLEAGUE":
        "Super League",

    "SUPER LEAGUE":
        "Super League",

    "GREEK CUP":
        "Greek Cup",
}


FILE_TYPE_MAP = {
    "CK": "corner_kicks",
    "FK": "free_kicks",
    "TI": "throw_ins",
    "FA": "final_attempts",
}