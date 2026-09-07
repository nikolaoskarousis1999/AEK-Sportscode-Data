import re
import xml.etree.ElementTree as ET

from src.sportscode.mappings import (
    EVENT_CODE_MAP,
    GROUP_KEY_MAP,
    normalize_group_value,
)


def normalize_spaces(
    value: str | None,
) -> str | None:
    if value is None:
        return None

    return re.sub(
        r"\s+",
        " ",
        value,
    ).strip()


def normalize_group_key(
    group_name: str | None,
) -> str | None:
    if group_name is None:
        return None

    normalized = normalize_spaces(
        group_name
    )

    if normalized in GROUP_KEY_MAP:
        return GROUP_KEY_MAP[
            normalized
        ]

    key = normalized.lower()

    key = re.sub(
        r"^[0-9]+\s*",
        "",
        key,
    )

    key = re.sub(
        r"[^a-z0-9]+",
        "_",
        key,
    )

    return key.strip("_")


def parse_sportscode_xml(
    xml_bytes: bytes,
) -> list[dict]:
    root = ET.fromstring(
        xml_bytes
    )

    events = []

    instances = root.findall(
        "./ALL_INSTANCES/instance"
    )

    for instance in instances:
        code = normalize_spaces(
            instance.findtext(
                "code"
            )
        )

        if code == "Periods":
            continue

        mapping = EVENT_CODE_MAP.get(
            code
        )

        if mapping is None:
            print(
                f"WARNING: "
                f"Unknown Sportscode code "
                f"'{code}'. Skipping."
            )
            continue

        source_instance_id = (
            instance.findtext("ID")
        )

        start_seconds = (
            instance.findtext("start")
        )

        end_seconds = (
            instance.findtext("end")
        )

        labels = []

        for (
            label_order,
            label,
        ) in enumerate(
            instance.findall(
                "label"
            ),
            start=1,
        ):
            group_raw = (
                label.findtext(
                    "group"
                )
            )

            value_raw = (
                label.findtext(
                    "text"
                )
            )

            if value_raw is None:
                continue

            normalized_group_raw = (
                normalize_spaces(
                    group_raw
                )
                if group_raw is not None
                else None
            )

            value_raw = (
                value_raw.strip()
            )

            group_key = normalize_group_key(
                normalized_group_raw
            )

            normalized_value = (
                normalize_spaces(
                    value_raw
                )
            )

            labels.append(
                {
                    "group_name_raw":
                        normalized_group_raw,

                    "group_key":
                        group_key,

                    "value_raw":
                        value_raw,

                    "value":
                        normalize_group_value(
                            group_key,
                            normalized_value,
                        ),

                    "label_order":
                        label_order,
                }
            )

        events.append(
            {
                "source_instance_id":
                    int(
                        source_instance_id
                    ),

                "code":
                    code,

                "event_family":
                    mapping[
                        "event_family"
                    ],

                "phase":
                    mapping[
                        "phase"
                    ],

                "start_seconds":
                    float(
                        start_seconds
                    ),

                "end_seconds":
                    float(
                        end_seconds
                    ),

                "labels":
                    labels,
            }
        )

    return events