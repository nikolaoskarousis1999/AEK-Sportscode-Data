from io import BytesIO
from pathlib import Path

import streamlit as st
from PIL import Image


BASE_DIR = (
    Path(__file__)
    .resolve()
    .parents[2]
)

LOGO_PATH = (
    BASE_DIR
    / "images"
    / "aek-background.jpeg"
)


@st.cache_data
def load_aek_emblem(
    image_path: str,
) -> bytes:
    """
    Keep only the white AEK emblem.

    Black background -> transparent
    White emblem -> white
    """

    image = Image.open(
        image_path
    ).convert(
        "RGBA"
    )

    pixels = image.load()

    width, height = image.size

    for y in range(height):
        for x in range(width):

            r, g, b, _ = pixels[
                x,
                y,
            ]

            brightness = (
                r + g + b
            ) / 3

            # ----------------------------------------
            # Black / dark background -> transparent
            # ----------------------------------------
            if brightness < 80:
                alpha = 0

            else:
                # ------------------------------------
                # White emblem -> visible
                # ------------------------------------
                alpha = int(
                    min(
                        255,
                        (
                            brightness
                            - 80
                        )
                        / 175
                        * 255
                    )
                )

            pixels[
                x,
                y,
            ] = (
                255,
                255,
                255,
                alpha,
            )

    # -----------------------------------------------
    # Crop transparent margins
    # -----------------------------------------------

    alpha_channel = (
        image.getchannel(
            "A"
        )
    )

    bbox = (
        alpha_channel.getbbox()
    )

    if bbox:
        left, top, right, bottom = bbox

        padding = 12

        image = image.crop(
            (
                max(
                    0,
                    left - padding,
                ),
                max(
                    0,
                    top - padding,
                ),
                min(
                    width,
                    right + padding,
                ),
                min(
                    height,
                    bottom + padding,
                ),
            )
        )

    buffer = BytesIO()

    image.save(
        buffer,
        format="PNG",
    )

    return buffer.getvalue()


def render_header():

    # Hide Streamlit fullscreen icon
    st.markdown(
        """
        <style>
        button[title="View fullscreen"] {
            display: none !important;
        }

        div[data-testid="stImage"] button {
            display: none !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    logo_col, text_col = st.columns(
        [
            1.4,
            4.6,
        ],
        vertical_alignment="center",
    )

    with logo_col:

        if LOGO_PATH.exists():

            emblem = (
                load_aek_emblem(
                    str(
                        LOGO_PATH
                    )
                )
            )

            st.image(
                emblem,
                width=250,
            )

    with text_col:

        st.title(
            "AEK Sportscode Data"
        )

        st.subheader(
            "Match analysis database for AEK's technical staff"
        )

        st.write(
            "Explore match-level Sportscode data across "
            "Super League, Greek Cup, and Champions League."
        )