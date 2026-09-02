import os

import streamlit as st
from dotenv import load_dotenv
from supabase import Client, create_client


ENV_FILE = os.getenv(
    "ENV_FILE",
    ".env",
)

load_dotenv(
    dotenv_path=ENV_FILE,
    override=True,
)


def _get_setting(name: str) -> str | None:
    value = os.getenv(name)

    if value:
        return value

    try:
        return st.secrets[name]
    except (
        KeyError,
        FileNotFoundError,
    ):
        return None


def get_supabase_client() -> Client:
    url = _get_setting(
        "SUPABASE_URL"
    )

    key = _get_setting(
        "SUPABASE_SERVICE_ROLE_KEY"
    )

    if not url:
        raise ValueError(
            "SUPABASE_URL is missing."
        )

    if not key:
        raise ValueError(
            "SUPABASE_SERVICE_ROLE_KEY is missing."
        )

    return create_client(
        url,
        key,
    )