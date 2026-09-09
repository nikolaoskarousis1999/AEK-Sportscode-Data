from __future__ import annotations

import streamlit as st


REPORT_MODULES = (
    "corner_kick",
    "free_kick",
    "throw_in",
    "final_attempt",
)

REPORT_STATE_KEY = "sportscode_reports"
REPORT_PDF_CACHE_KEY = "sportscode_report_pdf_cache"


def _empty_reports() -> dict[str, list[dict]]:
    return {
        module: []
        for module in REPORT_MODULES
    }


def _empty_pdf_cache() -> dict[str, bytes | None]:
    return {
        module: None
        for module in REPORT_MODULES
    }


def ensure_report_state() -> dict[str, list[dict]]:
    reports = st.session_state.get(
        REPORT_STATE_KEY
    )

    if not isinstance(
        reports,
        dict,
    ):
        reports = _empty_reports()

        st.session_state[
            REPORT_STATE_KEY
        ] = reports

    for module in REPORT_MODULES:
        reports.setdefault(
            module,
            [],
        )

    pdf_cache = st.session_state.get(
        REPORT_PDF_CACHE_KEY
    )

    if not isinstance(
        pdf_cache,
        dict,
    ):
        pdf_cache = _empty_pdf_cache()

        st.session_state[
            REPORT_PDF_CACHE_KEY
        ] = pdf_cache

    for module in REPORT_MODULES:
        pdf_cache.setdefault(
            module,
            None,
        )

    return reports


def _pdf_cache() -> dict[str, bytes | None]:
    ensure_report_state()

    return st.session_state[
        REPORT_PDF_CACHE_KEY
    ]


def invalidate_report_pdf(
    module: str,
) -> None:
    _pdf_cache()[
        module
    ] = None


def get_prepared_report_pdf(
    module: str,
) -> bytes | None:
    return _pdf_cache().get(
        module
    )


def set_prepared_report_pdf(
    module: str,
    pdf_bytes: bytes,
) -> None:
    _pdf_cache()[
        module
    ] = pdf_bytes


def get_report_items(
    module: str,
) -> list[dict]:
    reports = ensure_report_state()

    return reports[
        module
    ]


def get_report_count(
    module: str,
) -> int:
    return len(
        get_report_items(
            module
        )
    )


def is_in_report(
    module: str,
    item_id: str,
) -> bool:
    return any(
        item.get(
            "id"
        )
        == item_id
        for item
        in get_report_items(
            module
        )
    )


def add_report_item(
    module: str,
    item: dict,
) -> bool:
    items = get_report_items(
        module
    )

    item_id = item.get(
        "id"
    )

    if not item_id:
        raise ValueError(
            "Report item must contain an id."
        )

    if is_in_report(
        module,
        item_id,
    ):
        return False

    items.append(
        item
    )

    invalidate_report_pdf(
        module
    )

    return True


def remove_report_item(
    module: str,
    item_id: str,
) -> bool:
    items = get_report_items(
        module
    )

    before = len(
        items
    )

    items[:] = [
        item
        for item in items
        if item.get(
            "id"
        )
        != item_id
    ]

    changed = (
        len(items)
        < before
    )

    if changed:
        invalidate_report_pdf(
            module
        )

    return changed


def clear_report(
    module: str,
) -> None:
    get_report_items(
        module
    ).clear()

    invalidate_report_pdf(
        module
    )


def clear_all_reports() -> None:
    reports = ensure_report_state()

    for module in REPORT_MODULES:
        reports[
            module
        ].clear()

        invalidate_report_pdf(
            module
        )


def move_report_item(
    module: str,
    item_id: str,
    direction: int,
) -> None:
    items = get_report_items(
        module
    )

    current_index = next(
        (
            index
            for index, item
            in enumerate(
                items
            )
            if item.get(
                "id"
            )
            == item_id
        ),
        None,
    )

    if current_index is None:
        return

    new_index = (
        current_index
        + direction
    )

    if not (
        0
        <= new_index
        < len(items)
    ):
        return

    item = items.pop(
        current_index
    )

    items.insert(
        new_index,
        item,
    )

    invalidate_report_pdf(
        module
    )
