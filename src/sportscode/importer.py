import hashlib
import re

from src.data.supabase_client import (
    get_supabase_client,
)

from src.drive.google_drive import (
    download_file,
    find_root_folder,
    get_drive_service,
    scan_xml_files,
)

from src.sportscode.mappings import (
    COMPETITION_NAME_MAP,
    FILE_TYPE_MAP,
)

from src.sportscode.parser import (
    normalize_spaces,
    parse_sportscode_xml,
)


def calculate_file_hash(
    xml_bytes: bytes,
) -> str:
    return hashlib.sha256(
        xml_bytes
    ).hexdigest()


def get_file_type(
    file_name: str,
) -> str:
    name = file_name.upper()

    for code, file_type in (
        FILE_TYPE_MAP.items()
    ):
        if f" {code} " in name:
            return file_type

    return "unknown"


def get_competition_name(
    folder_name: str,
) -> str:
    normalized = normalize_spaces(
        folder_name
    )

    return COMPETITION_NAME_MAP.get(
        normalized.upper(),
        normalized,
    )


def get_opponent(
    match_folder: str,
) -> str:
    parts = [
        part.strip()
        for part in (
            match_folder.split("-")
        )
        if part.strip()
    ]

    opponents = [
        part
        for part in parts
        if part.upper() != "AEK"
    ]

    if len(opponents) == 1:
        return opponents[0]

    return match_folder


def find_venue(
    events: list[dict],
) -> str | None:
    for event in events:
        for label in event["labels"]:
            if label["group_key"] not in {
                "location",
                "venue",
            }:
                continue

            value = label[
                "value"
            ].upper()

            if value in {
                "HOME",
                "AWAY",
            }:
                return value

    return None


def get_competition_id(
    supabase,
    competition_name: str,
) -> int:
    response = (
        supabase
        .table("competitions")
        .select("id")
        .eq(
            "name",
            competition_name,
        )
        .execute()
    )

    if response.data:
        return response.data[0][
            "id"
        ]

    response = (
        supabase
        .table("competitions")
        .insert(
            {
                "name":
                    competition_name
            }
        )
        .execute()
    )

    return response.data[0][
        "id"
    ]


def get_or_create_match(
    supabase,
    competition_id: int,
    opponent: str,
    venue: str,
) -> int:
    response = (
        supabase
        .table("matches")
        .select("id")
        .eq(
            "competition_id",
            competition_id,
        )
        .eq(
            "opponent",
            opponent,
        )
        .eq(
            "venue",
            venue,
        )
        .execute()
    )

    if response.data:
        return response.data[0][
            "id"
        ]

    response = (
        supabase
        .table("matches")
        .insert(
            {
                "competition_id":
                    competition_id,

                "opponent":
                    opponent,

                "venue":
                    venue,

                "match_date":
                    None,

                "aek_score":
                    None,

                "opponent_score":
                    None,
            }
        )
        .execute()
    )

    return response.data[0][
        "id"
    ]


def import_exists(
    supabase,
    file_hash: str,
) -> bool:
    response = (
        supabase
        .table(
            "sportscode_imports"
        )
        .select("id")
        .eq(
            "file_hash",
            file_hash,
        )
        .execute()
    )

    return bool(
        response.data
    )


def import_xml(
    supabase,
    file_info: dict,
    xml_bytes: bytes,
):
    file_name = file_info[
        "name"
    ]

    folder_path = file_info[
        "path"
    ]

    if len(folder_path) < 2:
        print(
            f"SKIP: {file_name} "
            "is not inside "
            "Competition / Match."
        )
        return

    competition_folder = (
        folder_path[0]
    )

    match_folder = (
        folder_path[-1]
    )

    competition_name = (
        get_competition_name(
            competition_folder
        )
    )

    opponent = get_opponent(
        match_folder
    )

    file_type = get_file_type(
        file_name
    )

    file_hash = calculate_file_hash(
        xml_bytes
    )

    if import_exists(
        supabase,
        file_hash,
    ):
        print(
            f"SKIP: already imported "
            f"{file_name}"
        )
        return

    events = parse_sportscode_xml(
        xml_bytes
    )

    if not events:
        print(
            f"SKIP: no events in "
            f"{file_name}"
        )
        return

    venue = find_venue(
        events
    )

    if venue is None:
        print(
            f"SKIP: venue not found "
            f"for {file_name}"
        )
        return

    competition_id = (
        get_competition_id(
            supabase,
            competition_name,
        )
    )

    match_id = get_or_create_match(
        supabase=supabase,
        competition_id=competition_id,
        opponent=opponent,
        venue=venue,
    )

    import_response = (
        supabase
        .table(
            "sportscode_imports"
        )
        .insert(
            {
                "match_id":
                    match_id,

                "file_name":
                    file_name,

                "file_type":
                    file_type,

                "file_hash":
                    file_hash,
            }
        )
        .execute()
    )

    import_id = (
        import_response
        .data[0]["id"]
    )

    event_count = 0
    label_count = 0

    for event in events:
        event_response = (
            supabase
            .table(
                "sportscode_events"
            )
            .insert(
                {
                    "match_id":
                        match_id,

                    "import_id":
                        import_id,

                    "source_instance_id":
                        event[
                            "source_instance_id"
                        ],

                    "code":
                        event["code"],

                    "event_family":
                        event[
                            "event_family"
                        ],

                    "phase":
                        event["phase"],

                    "start_seconds":
                        event[
                            "start_seconds"
                        ],

                    "end_seconds":
                        event[
                            "end_seconds"
                        ],
                }
            )
            .execute()
        )

        event_id = (
            event_response
            .data[0]["id"]
        )

        event_count += 1

        labels = []

        for label in event[
            "labels"
        ]:
            labels.append(
                {
                    "event_id":
                        event_id,

                    "group_name_raw":
                        label[
                            "group_name_raw"
                        ],

                    "group_key":
                        label[
                            "group_key"
                        ],

                    "value_raw":
                        label[
                            "value_raw"
                        ],

                    "value":
                        label[
                            "value"
                        ],

                    "label_order":
                        label[
                            "label_order"
                        ],
                }
            )

        if labels:
            (
                supabase
                .table(
                    "sportscode_event_labels"
                )
                .insert(
                    labels
                )
                .execute()
            )

            label_count += len(
                labels
            )

    print(
        f"IMPORTED: {file_name}"
    )

    print(
        f"  Competition: "
        f"{competition_name}"
    )

    print(
        f"  Match: "
        f"{match_folder}"
    )

    print(
        f"  Opponent: "
        f"{opponent}"
    )

    print(
        f"  Venue: "
        f"{venue}"
    )

    print(
        f"  Events: "
        f"{event_count}"
    )

    print(
        f"  Labels: "
        f"{label_count}"
    )


def import_sportscode_drive():
    supabase = (
        get_supabase_client()
    )

    drive = (
        get_drive_service()
    )

    root = find_root_folder(
        drive
    )

    xml_files = scan_xml_files(
        drive=drive,
        folder_id=root["id"],
    )

    print(
        f"Connected to Google Drive."
    )

    print(
        f"Drive root: "
        f"{root['name']}"
    )

    print(
        f"Found "
        f"{len(xml_files)} "
        f"XML files."
    )

    print()

    for file_info in xml_files:
        path = " / ".join(
            file_info["path"]
        )

        print(
            "=" * 70
        )

        print(
            f"{path} / "
            f"{file_info['name']}"
        )

        xml_bytes = (
            download_file(
                drive,
                file_info["id"],
            )
        )

        import_xml(
            supabase=supabase,
            file_info=file_info,
            xml_bytes=xml_bytes,
        )

    print()

    print(
        "Sportscode import finished."
    )