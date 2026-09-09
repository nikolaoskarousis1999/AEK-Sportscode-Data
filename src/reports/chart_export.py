from __future__ import annotations

import copy
import importlib.util

import plotly.io as pio


# Match the Streamlit dashboard visual order:
# 1st series = light blue
# 2nd series = dark blue
# 3rd series = light pink
# 4th series = red
DASHBOARD_BAR_PALETTE = [
    "#7DBAF2",
    "#0D76C9",
    "#FFA1A6",
    "#FF2D2D",
]


def _apply_pdf_theme(
    figure,
    *,
    compact: bool,
):
    """
    Create a print-friendly clone of the Streamlit figure while keeping
    the same visible series colour order used in the dashboard.
    """
    fig = copy.deepcopy(
        figure
    )

    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(
            family="Arial Black, Arial, Helvetica, sans-serif",
            color="#111111",
            size=13 if compact else 17,
        ),
        margin=dict(
            l=55 if compact else 70,
            r=70 if compact else 95,
            t=18 if compact else 24,
            b=50 if compact else 65,
        ),
        legend=dict(
            font=dict(
                family="Arial Black, Arial, Helvetica, sans-serif",
                size=11 if compact else 14,
                color="#111111",
            ),
            bgcolor="rgba(255,255,255,0.94)",
            bordercolor="#D7D7D7",
            borderwidth=0.6,
        ),
        uniformtext=dict(
            minsize=10 if compact else 13,
            mode="show",
        ),
    )

    bar_index = 0

    for trace in fig.data:
        trace_type = getattr(
            trace,
            "type",
            "",
        )

        if trace_type == "bar":
            color = DASHBOARD_BAR_PALETTE[
                bar_index
                % len(DASHBOARD_BAR_PALETTE)
            ]
            bar_index += 1

            marker = getattr(
                trace,
                "marker",
                None,
            )

            if marker is not None:
                marker.color = color

                if getattr(
                    marker,
                    "line",
                    None,
                ) is not None:
                    marker.line.color = "#FFFFFF"
                    marker.line.width = 0.7

            if hasattr(
                trace,
                "textfont",
            ):
                # PDF report bars use labels outside the bars.
                # Always use dark text so every percentage/count remains
                # visible against the white PDF background, regardless
                # of the bar colour.
                trace.textfont = dict(
                    family="Arial Black, Arial, Helvetica, sans-serif",
                    size=12 if compact else 15,
                    color="#222222",
                )

        elif trace_type == "scatter":
            # Scatter traces such as the Box Entry line already carry
            # the exact dashboard colour (#FFD54F). Keep it.
            line = getattr(
                trace,
                "line",
                None,
            )

            if (
                line is not None
                and getattr(
                    line,
                    "color",
                    None,
                )
            ):
                line.width = max(
                    getattr(
                        line,
                        "width",
                        0,
                    )
                    or 0,
                    4,
                )

            marker = getattr(
                trace,
                "marker",
                None,
            )

            if marker is not None:
                marker.size = max(
                    getattr(
                        marker,
                        "size",
                        0,
                    )
                    or 0,
                    9,
                )

            if hasattr(
                trace,
                "textfont",
            ):
                trace.textfont = dict(
                    family="Arial Black, Arial, Helvetica, sans-serif",
                    size=12 if compact else 15,
                    color="#333333",
                )

    fig.update_xaxes(
        showline=True,
        linecolor="#777777",
        linewidth=1,
        gridcolor="#E6E6E6",
        tickfont=dict(
            family="Arial Black, Arial, Helvetica, sans-serif",
            size=10 if compact else 13,
            color="#111111",
        ),
        title_font=dict(
            family="Arial Black, Arial, Helvetica, sans-serif",
            size=11 if compact else 14,
            color="#111111",
        ),
        automargin=True,
    )

    fig.update_yaxes(
        showline=False,
        gridcolor="#E6E6E6",
        zerolinecolor="#BFBFBF",
        tickfont=dict(
            family="Arial Black, Arial, Helvetica, sans-serif",
            size=10 if compact else 13,
            color="#111111",
        ),
        title_font=dict(
            family="Arial Black, Arial, Helvetica, sans-serif",
            size=11 if compact else 14,
            color="#111111",
        ),
        automargin=True,
    )

    return fig


def plotly_json_to_png(
    figure_json: str,
    *,
    width: int = 900,
    height: int = 500,
    scale: float = 2.0,
    compact: bool = True,
) -> bytes:
    figure = pio.from_json(
        figure_json
    )

    figure = _apply_pdf_theme(
        figure,
        compact=compact,
    )

    try:
        return figure.to_image(
            format="png",
            width=width,
            height=height,
            scale=scale,
        )

    except Exception as exc:
        # Give a precise error if Kaleido itself is genuinely missing.
        if importlib.util.find_spec(
            "kaleido"
        ) is None:
            raise RuntimeError(
                "Plotly chart export requires Kaleido. "
                "Install it in the project virtual environment "
                "with: pip install -U kaleido"
            ) from exc

        message = str(
            exc
        ).lower()

        chrome_missing = any(
            token in message
            for token in (
                "chrome",
                "chromium",
                "browser",
                "browser_path",
            )
        )

        if not chrome_missing:
            # Do not hide unrelated Plotly/Kaleido errors behind the
            # generic 'install Kaleido' message.
            raise RuntimeError(
                "Plotly chart export failed: "
                f"{exc}"
            ) from exc

        try:
            # Kaleido v1 does not bundle Chrome. On Streamlit Community
            # Cloud there may be no browser available after pip install.
            # Plotly's supported installer downloads a compatible Chrome
            # for Kaleido into its default cache location.
            pio.get_chrome()

            return figure.to_image(
                format="png",
                width=width,
                height=height,
                scale=scale,
            )

        except Exception as retry_exc:
            raise RuntimeError(
                "Plotly chart export failed because Kaleido could not "
                "find or install Chrome/Chromium. "
                f"Original error: {exc}. "
                f"Retry error: {retry_exc}"
            ) from retry_exc
