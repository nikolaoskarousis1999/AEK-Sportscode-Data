from __future__ import annotations

import streamlit as st

from src.reports.pdf_builder import (
    build_report_pdf,
)

from src.reports.report_state import (
    add_report_item,
    clear_report,
    get_prepared_report_pdf,
    get_report_count,
    get_report_items,
    is_in_report,
    move_report_item,
    remove_report_item,
    set_prepared_report_pdf,
)


MODULE_TITLES = {
    "corner_kick":
        "Corner Kicks",

    "free_kick":
        "Free Kicks",

    "throw_in":
        "Throw-Ins",

    "final_attempt":
        "Final Attempts",
}


DOWNLOAD_COMPLETE_KEY = (
    "_sportscode_report_download_complete"
)


def _fragment_rerun():
    try:
        st.rerun(
            scope="fragment"
        )

    except TypeError:
        st.rerun()


def render_add_to_report_button(
    item: dict,
    *,
    key: str,
) -> None:
    module = item[
        "module"
    ]

    item_id = item[
        "id"
    ]

    already_added = (
        is_in_report(
            module,
            item_id,
        )
    )

    label = (
        "✓ Added"
        if already_added
        else "Add to Report"
    )

    if st.button(
        label,
        key=key,
        disabled=already_added,
        use_container_width=False,
    ):
        add_report_item(
            module,
            item,
        )

        st.rerun()


def _context_summary(
    item: dict,
) -> list[str]:
    context = item.get(
        "context",
        {},
    )

    lines = []

    scope = context.get(
        "scope"
    )

    phase = context.get(
        "phase"
    )

    if (
        scope
        and phase
    ):
        lines.append(
            f"{scope} | {phase}"
        )

    elif scope:
        lines.append(
            str(scope)
        )

    if context.get(
        "match"
    ):
        lines.append(
            f"Match: "
            f"{context['match']}"
        )

    if context.get(
        "matches"
    ):
        lines.append(
            "Matches: "
            + ", ".join(
                context[
                    "matches"
                ]
            )
        )

    if context.get(
        "competition"
    ):
        lines.append(
            f"Competition: "
            f"{context['competition']}"
        )

    filters = context.get(
        "filters",
        {},
    )

    if filters:
        text = "; ".join(
            f"{label}: "
            + (
                ", ".join(
                    value
                )
                if isinstance(
                    value,
                    list,
                )
                else str(
                    value
                )
            )
            for label, value
            in filters.items()
        )

        lines.append(
            f"Filters: {text}"
        )

    return lines


def _clear_after_download(
    module: str,
) -> None:
    """
    The browser already has the PDF bytes when the download button
    is clicked. Clear the report immediately afterwards.
    """
    clear_report(
        module
    )

    st.session_state[
        DOWNLOAD_COMPLETE_KEY
    ] = module


@st.dialog(
    "Create Report",
    width="large",
)
def render_report_dialog(
    module: str,
):
    # A download click clears the basket in its callback.
    # On the following dialog rerun, force one full-page rerun
    # so the Create Report count outside the dialog becomes 0.
    if (
        st.session_state.get(
            DOWNLOAD_COMPLETE_KEY
        )
        == module
    ):
        st.session_state.pop(
            DOWNLOAD_COMPLETE_KEY,
            None,
        )

        st.rerun()

    items = get_report_items(
        module
    )

    module_title = (
        MODULE_TITLES.get(
            module,
            module,
        )
    )

    st.markdown(
        f"### {module_title} Report"
    )

    st.caption(
        f"{len(items)} selected item"
        f"{'s' if len(items) != 1 else ''}"
    )

    if not items:
        st.info(
            "Nothing has been added "
            "to this report yet."
        )

        return

    for index, item in enumerate(
        items,
        start=1,
    ):
        with st.container(
            border=True
        ):
            st.markdown(
                f"**{index}. "
                f"{item.get('section_title', '')}**"
            )

            for line in (
                _context_summary(
                    item
                )
            ):
                st.caption(
                    line
                )

            (
                col_up,
                col_down,
                col_remove,
            ) = st.columns(
                [
                    1,
                    1,
                    1.6,
                ]
            )

            with col_up:
                if st.button(
                    "↑ Up",
                    key=(
                        f"report_up_"
                        f"{module}_"
                        f"{item['id']}"
                    ),
                    disabled=(
                        index
                        == 1
                    ),
                    use_container_width=True,
                ):
                    move_report_item(
                        module,
                        item[
                            "id"
                        ],
                        -1,
                    )

                    _fragment_rerun()

            with col_down:
                if st.button(
                    "↓ Down",
                    key=(
                        f"report_down_"
                        f"{module}_"
                        f"{item['id']}"
                    ),
                    disabled=(
                        index
                        == len(
                            items
                        )
                    ),
                    use_container_width=True,
                ):
                    move_report_item(
                        module,
                        item[
                            "id"
                        ],
                        1,
                    )

                    _fragment_rerun()

            with col_remove:
                if st.button(
                    "Remove",
                    key=(
                        f"report_remove_"
                        f"{module}_"
                        f"{item['id']}"
                    ),
                    use_container_width=True,
                ):
                    remove_report_item(
                        module,
                        item[
                            "id"
                        ],
                    )

                    _fragment_rerun()

    st.divider()

    clear_col, action_col = (
        st.columns(
            [
                1,
                2,
            ]
        )
    )

    with clear_col:
        if st.button(
            "Clear Report",
            key=(
                f"clear_report_"
                f"{module}"
            ),
            use_container_width=True,
        ):
            clear_report(
                module
            )

            # Full rerun, not fragment rerun.
            # This immediately refreshes Create Report (0)
            # on the main dashboard.
            st.rerun()

    with action_col:
        prepared_pdf = (
            get_prepared_report_pdf(
                module
            )
        )

        # Do NOT build the PDF just because the dialog opened.
        # This keeps the popup responsive.
        if prepared_pdf is None:
            if st.button(
                "Prepare PDF",
                key=(
                    f"prepare_report_"
                    f"{module}"
                ),
                type="primary",
                use_container_width=True,
            ):
                try:
                    with st.spinner(
                        "Preparing PDF..."
                    ):
                        pdf_bytes = (
                            build_report_pdf(
                                items
                            )
                        )

                    set_prepared_report_pdf(
                        module,
                        pdf_bytes,
                    )

                    _fragment_rerun()

                except Exception as exc:
                    st.error(
                        str(exc)
                    )

        else:
            st.download_button(
                "Download Report",
                data=prepared_pdf,
                file_name=(
                    f"AEK_"
                    f"{module_title.replace(' ', '_')}"
                    f"_Report.pdf"
                ),
                mime="application/pdf",
                key=(
                    f"download_report_"
                    f"{module}"
                ),
                use_container_width=True,
                on_click=(
                    _clear_after_download
                ),
                args=(
                    module,
                ),
            )


def render_create_report_button(
    module: str,
    *,
    key: str | None = None,
) -> None:
    count = (
        get_report_count(
            module
        )
    )

    clicked = st.button(
        f"Create Report ({count})",
        key=(
            key
            or f"create_report_{module}"
        ),
        type="primary",
    )

    if clicked:
        render_report_dialog(
            module
        )
