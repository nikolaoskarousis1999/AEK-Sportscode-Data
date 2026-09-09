from __future__ import annotations

import hashlib
import json

import pandas as pd


MODULE_TITLES = {
    "corner_kick": "Corner Kicks",
    "free_kick": "Free Kicks",
    "throw_in": "Throw-Ins",
    "final_attempt": "Final Attempts",
}


def _json_default(value):
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass

    return str(value)


def _fingerprint(
    payload: dict,
) -> str:
    serialized = json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False,
        default=_json_default,
    )

    return hashlib.sha1(
        serialized.encode(
            "utf-8"
        )
    ).hexdigest()[:16]


def _base_item(
    *,
    module: str,
    section_title: str,
    item_type: str,
    context: dict,
    payload: dict,
    notes: list[str] | None = None,
) -> dict:
    identity = {
        "module": module,
        "section_title": section_title,
        "item_type": item_type,
        "context": context,
        "payload": payload,
    }

    return {
        "id": _fingerprint(
            identity
        ),
        "module": module,
        "module_title": MODULE_TITLES.get(
            module,
            module,
        ),
        "section_title": section_title,
        "item_type": item_type,
        "context": context,
        "payload": payload,
        "notes": list(
            notes
            or []
        ),
    }


def create_plotly_report_item(
    *,
    module: str,
    section_title: str,
    figure,
    context: dict,
    notes: list[str] | None = None,
) -> dict:
    payload = {
        "figure_json": figure.to_json(),
    }

    return _base_item(
        module=module,
        section_title=section_title,
        item_type="plotly_chart",
        context=context,
        payload=payload,
        notes=notes,
    )


def create_table_report_item(
    *,
    module: str,
    section_title: str,
    dataframe: pd.DataFrame,
    context: dict,
    notes: list[str] | None = None,
) -> dict:
    safe_df = dataframe.copy()
    safe_df = safe_df.where(
        pd.notnull(safe_df),
        None,
    )

    payload = {
        "columns": [
            str(column)
            for column
            in safe_df.columns
        ],
        "rows": safe_df.to_dict(
            orient="records"
        ),
    }

    return _base_item(
        module=module,
        section_title=section_title,
        item_type="table",
        context=context,
        payload=payload,
        notes=notes,
    )


def create_kpi_report_item(
    *,
    module: str,
    section_title: str,
    kpis: list[dict],
    context: dict,
    notes: list[str] | None = None,
) -> dict:
    payload = {
        "kpis": kpis,
    }

    return _base_item(
        module=module,
        section_title=section_title,
        item_type="kpi_group",
        context=context,
        payload=payload,
        notes=notes,
    )


def create_image_report_item(
    *,
    module: str,
    section_title: str,
    html: str,
    context: dict,
    width_px: int,
    height_px: int,
    notes: list[str] | None = None,
) -> dict:
    """
    Store the exact HTML/CSS used by the Streamlit visualisation.

    The PDF builder opens this same HTML in Chromium and screenshots
    it, so the report receives the browser-rendered visual rather
    than a separately reconstructed version.
    """
    payload = {
        "html": html,
        "width_px": int(width_px),
        "height_px": int(height_px),
    }

    return _base_item(
        module=module,
        section_title=section_title,
        item_type="image",
        context=context,
        payload=payload,
        notes=notes,
    )
