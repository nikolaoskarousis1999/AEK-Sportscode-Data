import io
import os
from pathlib import Path

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload


SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly"
]

FOLDER_MIME_TYPE = (
    "application/vnd.google-apps.folder"
)

BASE_DIR = Path(
    __file__
).resolve().parents[2]

TOKEN_FILE = (
    BASE_DIR / "token.json"
)

CLIENT_FILE = (
    BASE_DIR / "google-oauth-client.json"
)

ENV_FILE = os.getenv(
    "ENV_FILE",
    ".env",
)

load_dotenv(
    BASE_DIR / ENV_FILE,
    override=True,
)

ROOT_FOLDER_NAME = os.getenv(
    "GOOGLE_DRIVE_ROOT_FOLDER_NAME",
    "AEK Sportscode Data",
)


def get_drive_service():
    credentials = None

    if TOKEN_FILE.exists():
        credentials = (
            Credentials
            .from_authorized_user_file(
                TOKEN_FILE,
                SCOPES,
            )
        )

    if (
        credentials
        and credentials.expired
        and credentials.refresh_token
    ):
        credentials.refresh(
            Request()
        )

        TOKEN_FILE.write_text(
            credentials.to_json(),
            encoding="utf-8",
        )

    if (
        not credentials
        or not credentials.valid
    ):
        flow = (
            InstalledAppFlow
            .from_client_secrets_file(
                CLIENT_FILE,
                SCOPES,
            )
        )

        credentials = (
            flow.run_local_server(
                port=0
            )
        )

        TOKEN_FILE.write_text(
            credentials.to_json(),
            encoding="utf-8",
        )

    return build(
        "drive",
        "v3",
        credentials=credentials,
    )


def find_root_folder(
    drive,
) -> dict:
    response = (
        drive
        .files()
        .list(
            q=(
                f"name = '{ROOT_FOLDER_NAME}' "
                f"and mimeType = "
                f"'{FOLDER_MIME_TYPE}' "
                "and trashed = false"
            ),
            fields=(
                "files("
                "id,"
                "name,"
                "mimeType"
                ")"
            ),
        )
        .execute()
    )

    folders = response.get(
        "files",
        [],
    )

    if not folders:
        raise ValueError(
            f"Google Drive folder "
            f"'{ROOT_FOLDER_NAME}' "
            "was not found."
        )

    if len(folders) > 1:
        raise ValueError(
            f"More than one folder named "
            f"'{ROOT_FOLDER_NAME}' was found."
        )

    return folders[0]


def list_children(
    drive,
    folder_id: str,
) -> list[dict]:
    items = []
    page_token = None

    while True:
        response = (
            drive
            .files()
            .list(
                q=(
                    f"'{folder_id}' "
                    "in parents "
                    "and trashed = false"
                ),
                fields=(
                    "nextPageToken,"
                    "files("
                    "id,"
                    "name,"
                    "mimeType"
                    ")"
                ),
                orderBy="name",
                pageToken=page_token,
            )
            .execute()
        )

        items.extend(
            response.get(
                "files",
                [],
            )
        )

        page_token = response.get(
            "nextPageToken"
        )

        if not page_token:
            break

    return items


def scan_xml_files(
    drive,
    folder_id: str,
    path_parts: list[str] | None = None,
) -> list[dict]:
    if path_parts is None:
        path_parts = []

    found_files = []

    children = list_children(
        drive,
        folder_id,
    )

    for item in children:
        if (
            item["mimeType"]
            == FOLDER_MIME_TYPE
        ):
            found_files.extend(
                scan_xml_files(
                    drive=drive,
                    folder_id=item["id"],
                    path_parts=(
                        path_parts
                        + [item["name"]]
                    ),
                )
            )

        elif (
            item["name"]
            .lower()
            .endswith(".xml")
        ):
            found_files.append(
                {
                    "id": item["id"],
                    "name": item["name"],
                    "path": path_parts,
                }
            )

    return found_files


def download_file(
    drive,
    file_id: str,
) -> bytes:
    request = (
        drive
        .files()
        .get_media(
            fileId=file_id
        )
    )

    buffer = io.BytesIO()

    downloader = MediaIoBaseDownload(
        buffer,
        request,
    )

    done = False

    while not done:
        _, done = (
            downloader.next_chunk()
        )

    return buffer.getvalue()