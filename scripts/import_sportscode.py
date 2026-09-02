import sys
from pathlib import Path


BASE_DIR = Path(
    __file__
).resolve().parent.parent

sys.path.insert(
    0,
    str(BASE_DIR),
)


from src.sportscode.importer import (  # noqa: E402
    import_sportscode_drive,
)


if __name__ == "__main__":
    import_sportscode_drive()