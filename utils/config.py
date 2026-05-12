import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def get_env(key: str, default: str | None = None) -> str:
    val = os.getenv(key, default)
    if val is None:
        raise ValueError(f"Missing required environment variable: {key}")
    return val


class Settings:
    username: str
    password: str
    settings_dir: Path

    def __init__(self):
        self.username = get_env("INSTAGRAM_USERNAME")
        self.password = get_env("INSTAGRAM_PASSWORD")
        self.settings_dir = Path(__file__).parent.parent / "storage"

    @property
    def session_file(self) -> Path:
        return self.settings_dir / f"{self.username}.json"
