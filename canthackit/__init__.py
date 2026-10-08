import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
USER_AGENT = "canthackit/0.1 (open-source event notifier)"


def load_config() -> dict:
    """Settings in config.toml that contributors edit, like which calendars to follow."""
    with open(ROOT / "config.toml", "rb") as f:
        return tomllib.load(f)
