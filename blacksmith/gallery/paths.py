from pathlib import Path

from blacksmith.audit.paths import user_config_dir

DEFAULT_INDEX_URL = (
    "https://raw.githubusercontent.com/jimididit/blacksmith/main/"
    "blacksmith/gallery/index.json"
)


def bundled_index_path() -> Path:
    return Path(__file__).resolve().parent / "index.json"


def cached_index_path() -> Path:
    return user_config_dir() / "gallery" / "index.json"
