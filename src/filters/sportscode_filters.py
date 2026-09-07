def record_matches_value(
    record: dict,
    key: str,
    selected_value,
) -> bool:
    if selected_value is None:
        return True

    value = record.get(key)

    if value is None:
        return False

    # Multiselect filter
    if isinstance(selected_value, list):

        if not selected_value:
            return True

        if isinstance(value, list):
            return any(
                item in selected_value
                for item in value
            )

        return value in selected_value

    # Single-value filter
    if isinstance(value, list):
        return selected_value in value

    return value == selected_value


def filter_records(
    records: list[dict],
    filters: dict,
) -> list[dict]:
    filtered_records = records

    for key, selected_value in filters.items():

        if selected_value is None:
            continue

        if (
            isinstance(selected_value, list)
            and not selected_value
        ):
            continue

        filtered_records = [
            record
            for record in filtered_records
            if record_matches_value(
                record=record,
                key=key,
                selected_value=selected_value,
            )
        ]

    return filtered_records


def get_filter_options(
    records: list[dict],
    key: str,
) -> list[str]:
    values = set()

    for record in records:

        value = record.get(key)

        if value is None:
            continue

        if isinstance(value, list):
            values.update(value)

        else:
            values.add(value)

    return sorted(values)