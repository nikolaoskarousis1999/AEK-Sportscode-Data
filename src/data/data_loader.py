import os

from dotenv import load_dotenv
from supabase import Client, create_client


# ============================================================
# ENVIRONMENT
# ============================================================

ENV_FILE = os.getenv(
    "ENV_FILE",
    ".env",
)

load_dotenv(
    dotenv_path=ENV_FILE,
    override=True,
)


# ============================================================
# SUPABASE CONFIGURATION
# ============================================================

SUPABASE_URL = os.getenv(
    "SUPABASE_URL"
)

SUPABASE_KEY = os.getenv(
    "SUPABASE_SERVICE_ROLE_KEY"
)


# ============================================================
# SUPABASE CLIENT
# ============================================================

def get_supabase_client() -> Client:
    """
    Create and return the Supabase client.
    """

    if not SUPABASE_URL:
        raise ValueError(
            f"SUPABASE_URL is missing from {ENV_FILE}."
        )

    if not SUPABASE_KEY:
        raise ValueError(
            "SUPABASE_SERVICE_ROLE_KEY "
            f"is missing from {ENV_FILE}."
        )

    return create_client(
        SUPABASE_URL,
        SUPABASE_KEY,
    )


# ============================================================
# COMPETITIONS
# ============================================================

def load_competitions() -> list[dict]:
    """
    Load all competitions from Supabase.
    """

    supabase = get_supabase_client()

    response = (
        supabase
        .table("competitions")
        .select(
            "id,name"
        )
        .order(
            "id"
        )
        .execute()
    )

    return response.data