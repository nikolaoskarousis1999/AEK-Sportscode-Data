from __future__ import annotations

from io import BytesIO

from playwright.sync_api import sync_playwright


from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from src.reports.chart_export import plotly_json_to_png


PAGE_WIDTH, PAGE_HEIGHT = A4

PAGE_MARGIN_X = 12 * mm
PAGE_MARGIN_TOP = 11 * mm
PAGE_MARGIN_BOTTOM = 12 * mm

CONTENT_WIDTH = PAGE_WIDTH - (2 * PAGE_MARGIN_X)

AEK_YELLOW = colors.HexColor("#F2C300")
INK = colors.HexColor("#111111")
MUTED = colors.HexColor("#666666")
LIGHT_BORDER = colors.HexColor("#D7D7D7")
SOFT_BG = colors.HexColor("#F7F7F7")
HEADER_BG = colors.HexColor("#F1F1F1")


# ============================================================
# STYLES
# ============================================================

def _styles():
    styles = getSampleStyleSheet()

    styles.add(
        ParagraphStyle(
            name="ReportTitle",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=18,
            textColor=INK,
            spaceAfter=0,
        )
    )

    styles.add(
        ParagraphStyle(
            name="ReportMeta",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=MUTED,
            spaceAfter=0,
        )
    )

    styles.add(
        ParagraphStyle(
            name="SectionNumber",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=11,
            textColor=AEK_YELLOW,
            spaceAfter=0,
        )
    )

    styles.add(
        ParagraphStyle(
            name="SectionTitle",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=17,
            textColor=INK,
            spaceAfter=0,
        )
    )

    styles.add(
        ParagraphStyle(
            name="SectionNote",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=7,
            leading=9,
            textColor=MUTED,
            spaceBefore=2 * mm,
            spaceAfter=0,
        )
    )

    return styles


# ============================================================
# CONTEXT
# ============================================================

def _format_value(value) -> str:
    if isinstance(value, list):
        return ", ".join(
            str(item)
            for item in value
        )

    return str(value)


def _top_context_text(
    context: dict,
) -> str:
    """
    The report header is intentionally minimal.

    Show the selected match(es) only. If the user has actually applied
    filters, show those once here as well. Scope / phase / competition are
    not repeated through the report.
    """
    parts = []

    match = context.get(
        "match"
    )

    matches = (
        context.get(
            "matches"
        )
        or []
    )

    if match:
        parts.append(
            str(match)
        )

    elif matches:
        parts.append(
            ", ".join(
                str(value)
                for value in matches
            )
        )

    phase = context.get(
        "phase"
    )

    if phase:
        parts.append(
            str(phase)
            .replace(
                "_",
                " ",
            )
            .title()
        )

    filters = (
        context.get(
            "filters"
        )
        or {}
    )

    if filters:
        filter_text = " | ".join(
            f"{label}: {_format_value(value)}"
            for label, value
            in filters.items()
        )

        parts.append(
            f"Filters - {filter_text}"
        )

    return "  •  ".join(
        parts
    )


# ============================================================
# HEADER
# ============================================================

def _build_report_header(
    items: list[dict],
    styles,
):
    first_item = items[0]

    module_title = str(
        first_item.get(
            "module_title",
            "Analysis",
        )
    ).upper()

    context_text = _top_context_text(
        first_item.get(
            "context",
            {},
        )
    )

    rows = [
        [
            Paragraph(
                f"{module_title} ANALYSIS REPORT",
                styles["ReportTitle"],
            )
        ]
    ]

    if context_text:
        rows.append(
            [
                Paragraph(
                    context_text,
                    styles["ReportMeta"],
                )
            ]
        )

    table = Table(
        rows,
        colWidths=[
            CONTENT_WIDTH
        ],
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    HEADER_BG,
                ),
                (
                    "LINEBELOW",
                    (0, -1),
                    (-1, -1),
                    2,
                    AEK_YELLOW,
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    5 * mm,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    5 * mm,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, 0),
                    4 * mm,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, 0),
                    1.5 * mm,
                ),
                (
                    "TOPPADDING",
                    (0, 1),
                    (-1, -1),
                    0,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 1),
                    (-1, -1),
                    4 * mm,
                ),
            ]
        )
    )

    return table


# ============================================================
# SECTION HEADER
# ============================================================

def _build_section_header(
    item: dict,
    *,
    number: int,
    styles,
):
    table = Table(
        [
            [
                Paragraph(
                    f"{number:02d}",
                    styles["SectionNumber"],
                ),
                Paragraph(
                    str(
                        item.get(
                            "section_title",
                            "",
                        )
                    ),
                    styles["SectionTitle"],
                ),
            ]
        ],
        colWidths=[
            10 * mm,
            CONTENT_WIDTH - 10 * mm,
        ],
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    0,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    0,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    0,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    0,
                ),
            ]
        )
    )

    return table


# ============================================================
# KPI GRID
# ============================================================

def _build_kpi_grid(
    item: dict,
):
    kpis = (
        item.get(
            "payload",
            {},
        )
        .get(
            "kpis",
            [],
        )
    )

    if not kpis:
        return None

    columns = 4
    rows = []

    for start in range(
        0,
        len(kpis),
        columns,
    ):
        chunk = kpis[
            start:start + columns
        ]

        row = []

        for kpi in chunk:
            label = str(
                kpi.get(
                    "label",
                    "",
                )
            )

            value = str(
                kpi.get(
                    "value",
                    "",
                )
            )

            row.append(
                Paragraph(
                    (
                        "<font size='7.5' color='#666666'>"
                        f"{label}"
                        "</font>"
                        "<br/>"
                        "<font size='12'>"
                        f"<b>{value}</b>"
                        "</font>"
                    ),
                    ParagraphStyle(
                        "KPICell",
                        fontName="Helvetica",
                        alignment=TA_CENTER,
                        leading=12,
                    ),
                )
            )

        while len(row) < columns:
            row.append("")

        rows.append(row)

    col_width = (
        CONTENT_WIDTH
        / columns
    )

    table = Table(
        rows,
        colWidths=[
            col_width
        ] * columns,
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    SOFT_BG,
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.6,
                    LIGHT_BORDER,
                ),
                (
                    "INNERGRID",
                    (0, 0),
                    (-1, -1),
                    0.35,
                    LIGHT_BORDER,
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "ALIGN",
                    (0, 0),
                    (-1, -1),
                    "CENTER",
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
            ]
        )
    )

    return table


# ============================================================
# PLOTLY
# ============================================================

def _build_plotly_image(
    item: dict,
    *,
    target_height_mm: float = 155,
):
    """
    Build a large print-friendly chart.

    target_height_mm is chosen by the pagination logic:
    - larger when a chart has most of a page to itself
    - slightly smaller when sharing a page with a compact table/KPI block
    """
    figure_json = (
        item.get(
            "payload",
            {},
        )
        .get(
            "figure_json"
        )
    )

    if not figure_json:
        return None

    target_height = (
        target_height_mm
        * mm
    )

    export_width = 1700

    export_height = max(
        850,
        int(
            export_width
            * target_height
            / CONTENT_WIDTH
        ),
    )

    png_bytes = (
        plotly_json_to_png(
            figure_json,
            width=export_width,
            height=export_height,
            scale=2.2,
            compact=False,
        )
    )

    image = Image(
        BytesIO(
            png_bytes
        )
    )

    image.drawWidth = (
        CONTENT_WIDTH
    )

    image.drawHeight = (
        target_height
    )

    return image


# ============================================================
# PLAYWRIGHT / BROWSER LAUNCH
# ============================================================

def _launch_browser(playwright):
    """
    Launch a browser for rendering Streamlit HTML visualisations.

    Order:
    1. Playwright-managed Chromium, if already installed.
    2. System Google Chrome.
    3. System Microsoft Edge.

    Report generation must never try to download or install a browser.
    This keeps PDF creation reliable on local Windows environments and
    avoids failing halfway through a large report.
    """
    errors = []

    try:
        return playwright.chromium.launch(
            headless=True,
        )
    except Exception as exc:
        errors.append(
            f"Playwright Chromium: {exc}"
        )

    try:
        return playwright.chromium.launch(
            channel="chrome",
            headless=True,
        )
    except Exception as exc:
        errors.append(
            f"Google Chrome: {exc}"
        )

    try:
        return playwright.chromium.launch(
            channel="msedge",
            headless=True,
        )
    except Exception as exc:
        errors.append(
            f"Microsoft Edge: {exc}"
        )

    raise RuntimeError(
        "Could not launch a browser for the report visualisation.\n\n"
        + "\n\n".join(errors)
    )


# ============================================================
# EXACT STREAMLIT HTML VISUALISATION IMAGE
# ============================================================

def _build_html_visual_image(
    item: dict,
):
    """
    Render the exact HTML/CSS used by the Streamlit iframe in Chromium
    and insert the resulting screenshot into the PDF.

    This intentionally does not recreate the pitch with Pillow or
    ReportLab. The browser renders the same HTML that Streamlit shows.
    """
    payload = item.get(
        "payload",
        {},
    )

    html = payload.get(
        "html",
    )

    if not html:
        return None

    width_px = int(
        payload.get(
            "width_px",
            1400,
        )
    )

    height_px = int(
        payload.get(
            "height_px",
            455,
        )
    )

    # Chromium-compatible screenshot of the same iframe content.
    # Prefer Playwright Chromium when available, then fall back to the
    # system Chrome or Edge installation. No browser is installed here.
    # device_scale_factor=2 keeps text/lines sharp in the PDF.
    with sync_playwright() as playwright:
        browser = _launch_browser(
            playwright
        )

        try:
            page = browser.new_page(
                viewport={
                    "width": width_px,
                    "height": height_px,
                },
                device_scale_factor=2,
            )

            page.set_content(
                html,
                wait_until="load",
            )

            # Give CSS/layout a moment to settle.
            page.wait_for_timeout(
                80,
            )

            png_bytes = page.screenshot(
                type="png",
                full_page=False,
            )

        finally:
            browser.close()

    image = Image(
        BytesIO(
            png_bytes
        )
    )

    # Zone visualisations are intentionally allowed to extend beyond
    # the normal report content frame so the exact Streamlit capture
    # is easier to read in the PDF. Other report items are unchanged.
    zone_visual_width = (
        PAGE_WIDTH
        - (4 * mm)
    )

    image.drawWidth = (
        zone_visual_width
    )
    image.drawHeight = (
        zone_visual_width
        * height_px
        / width_px
    )

    # Centre the wider image on the A4 page.
    image.hAlign = "CENTER"

    return image


# ============================================================
# TABLE
# ============================================================

def _build_data_table(
    item: dict,
):
    payload = item.get(
        "payload",
        {},
    )

    columns = payload.get(
        "columns",
        [],
    )

    rows = payload.get(
        "rows",
        [],
    )

    if not columns:
        return None

    table_rows = [
        [
            Paragraph(
                f"<b>{column}</b>",
                ParagraphStyle(
                    "TableHeader",
                    fontName="Helvetica-Bold",
                    fontSize=7,
                    leading=8,
                    alignment=TA_CENTER,
                    textColor=colors.white,
                ),
            )
            for column in columns
        ]
    ]

    for row in rows:
        table_rows.append(
            [
                Paragraph(
                    _format_value(
                        row.get(
                            column,
                            "",
                        )
                    ),
                    ParagraphStyle(
                        "TableBody",
                        fontName="Helvetica",
                        fontSize=6.5,
                        leading=8,
                        alignment=TA_CENTER,
                    ),
                )
                for column in columns
            ]
        )

    col_width = (
        CONTENT_WIDTH
        / max(
            1,
            len(columns),
        )
    )

    table = Table(
        table_rows,
        colWidths=[
            col_width
        ] * len(columns),
        repeatRows=1,
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor(
                        "#222222"
                    ),
                ),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [
                        colors.white,
                        SOFT_BG,
                    ],
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.35,
                    LIGHT_BORDER,
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    3,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    3,
                ),
            ]
        )
    )

    return table


# ============================================================
# NOTES
# ============================================================

def _build_notes(
    item: dict,
    styles,
):
    notes = (
        item.get(
            "notes",
            [],
        )
    )

    if not notes:
        return None

    return Paragraph(
        " ".join(
            str(note)
            for note in notes
        ),
        styles[
            "SectionNote"
        ],
    )


# ============================================================
# PAGE FOOTER
# ============================================================

def _draw_footer(
    canvas,
    doc,
):
    canvas.saveState()

    canvas.setStrokeColor(
        LIGHT_BORDER
    )
    canvas.setLineWidth(
        0.4
    )

    canvas.line(
        PAGE_MARGIN_X,
        8 * mm,
        PAGE_WIDTH
        - PAGE_MARGIN_X,
        8 * mm,
    )

    canvas.setFont(
        "Helvetica",
        6.5,
    )

    canvas.setFillColor(
        MUTED
    )

    canvas.drawString(
        PAGE_MARGIN_X,
        5 * mm,
        "AEK Sportscode Data",
    )

    canvas.drawRightString(
        PAGE_WIDTH
        - PAGE_MARGIN_X,
        5 * mm,
        f"Page {doc.page}",
    )

    canvas.restoreState()


# ============================================================
# ITEM RENDERING
# ============================================================

def _append_item(
    story,
    item: dict,
    *,
    number: int,
    styles,
    chart_height_mm: float | None = None,
):
    item_type = (
        item.get(
            "item_type"
        )
    )

    section_flowables = [
        _build_section_header(
            item,
            number=number,
            styles=styles,
        ),
        Spacer(
            1,
            3 * mm,
        ),
    ]

    if (
        item_type
        == "kpi_group"
    ):
        content = (
            _build_kpi_grid(
                item
            )
        )

    elif (
        item_type
        == "plotly_chart"
    ):
        content = (
            _build_plotly_image(
                item,
                target_height_mm=(
                    chart_height_mm
                    if chart_height_mm is not None
                    else 155
                ),
            )
        )

    elif (
        item_type
        == "table"
    ):
        content = (
            _build_data_table(
                item
            )
        )

    elif (
        item_type
        == "image"
    ):
        content = (
            _build_html_visual_image(
                item
            )
        )

    else:
        content = None

    if content is not None:
        section_flowables.append(
            content
        )

    # Keep PDF charts visually clean.
    # Dashboard captions/label explanations are intentionally not
    # repeated underneath Plotly charts in the generated report.
    if item_type not in {
        "plotly_chart",
        "image",
    }:
        notes = (
            _build_notes(
                item,
                styles,
            )
        )

        if notes is not None:
            section_flowables.append(
                notes
            )

    # Compact tables must stay as one complete section:
    # section title + table header + all rows.
    # If there is not enough room, ReportLab moves the whole section
    # to the next page instead of leaving the final row by itself.
    if (
        item_type == "table"
        and _table_row_count(
            item
        ) <= 8
    ):
        story.append(
            KeepTogether(
                section_flowables
            )
        )

    else:
        story.extend(
            section_flowables
        )


# ============================================================
# LAYOUT HELPERS
# ============================================================

def _table_row_count(
    item: dict,
) -> int:
    return len(
        item.get(
            "payload",
            {},
        ).get(
            "rows",
            [],
        )
    )


def _is_compact_table(
    item: dict,
) -> bool:
    """
    Compact tables are allowed to share a page with the following chart.
    """
    return (
        item.get(
            "item_type"
        )
        == "table"
        and _table_row_count(
            item
        )
        <= 6
    )


# ============================================================
# PDF BUILDER
# ============================================================

def build_report_pdf(
    items: list[dict],
) -> bytes:
    if not items:
        raise ValueError(
            "No report items selected."
        )

    styles = _styles()
    output = BytesIO()

    doc = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=PAGE_MARGIN_X,
        leftMargin=PAGE_MARGIN_X,
        topMargin=PAGE_MARGIN_TOP,
        bottomMargin=PAGE_MARGIN_BOTTOM,
    )

    story = [
        _build_report_header(
            items,
            styles,
        ),
        Spacer(
            1,
            5 * mm,
        ),
    ]

    first_content_written = False
    previous_content_type = None
    previous_item = None

    # Approximate table load on the current page.
    # A chart can share a page with one genuinely small table,
    # but not after several tables have already consumed the page.
    table_rows_on_current_page = 0

    for index, item in enumerate(
        items
    ):
        number = (
            index
            + 1
        )

        item_type = (
            item.get(
                "item_type"
            )
        )

        next_item = (
            items[
                index + 1
            ]
            if index + 1 < len(items)
            else None
        )

        next_type = (
            next_item.get(
                "item_type"
            )
            if next_item
            else None
        )

        # KPIs remain compact at the top of page 1.
        if (
            item_type
            == "kpi_group"
        ):
            _append_item(
                story,
                item,
                number=number,
                styles=styles,
            )

            story.append(
                Spacer(
                    1,
                    5 * mm,
                )
            )

            previous_item = item
            previous_content_type = item_type

            continue

        needs_new_page = False
        chart_height_mm = None

        if item_type in {
            "plotly_chart",
            "image",
        }:
            # First chart after KPIs can use the rest of page 1.
            if not first_content_written:
                chart_height_mm = 145

            # A chart after another chart gets a fresh page and can grow.
            elif previous_content_type in {
                "plotly_chart",
                "image",
            }:
                needs_new_page = True
                chart_height_mm = 180

            # A chart after a compact amount of table content can
            # share the same page. If several tables are already on
            # the page, start the chart section on a fresh page so
            # its title can never be orphaned from the chart.
            elif previous_content_type == "table":
                if (
                    previous_item is not None
                    and _is_compact_table(
                        previous_item
                    )
                    and table_rows_on_current_page <= 6
                ):
                    chart_height_mm = 132
                else:
                    needs_new_page = True
                    chart_height_mm = 180

            else:
                chart_height_mm = 165

        elif item_type == "table":
            # Plotly charts normally consume most of the page, so a
            # following table starts on a fresh page.
            if (
                first_content_written
                and previous_content_type == "plotly_chart"
            ):
                needs_new_page = True

            # Zone Visualisation images are wide but relatively short.
            # Keep compact tables directly underneath them when there
            # is room, instead of forcing a mostly-empty first page.
            elif (
                first_content_written
                and previous_content_type == "image"
            ):
                story.append(
                    Spacer(
                        1,
                        6 * mm,
                    )
                )

            elif (
                first_content_written
                and previous_content_type == "table"
            ):
                story.append(
                    Spacer(
                        1,
                        7 * mm,
                    )
                )

        if needs_new_page:
            story.append(
                PageBreak()
            )

            story.append(
                _build_report_header(
                    items,
                    styles,
                )
            )

            story.append(
                Spacer(
                    1,
                    5 * mm,
                )
            )

            table_rows_on_current_page = 0

        _append_item(
            story,
            item,
            number=number,
            styles=styles,
            chart_height_mm=chart_height_mm,
        )

        # When a compact table is immediately followed by a chart,
        # use only a small gap so both make effective use of the page.
        if (
            item_type == "table"
            and next_type in {
                "plotly_chart",
                "image",
            }
            and _is_compact_table(
                item
            )
        ):
            story.append(
                Spacer(
                    1,
                    4 * mm,
                )
            )

        if item_type == "table":
            # Include one extra unit for the table header row.
            table_rows_on_current_page += (
                _table_row_count(
                    item
                )
                + 1
            )

        elif item_type in {
            "plotly_chart",
            "image",
        }:
            # A chart effectively consumes the rest of the page for
            # our packing decisions.
            table_rows_on_current_page = 99

        first_content_written = True
        previous_content_type = item_type
        previous_item = item

    doc.build(
        story,
        onFirstPage=_draw_footer,
        onLaterPages=_draw_footer,
    )

    return output.getvalue()
