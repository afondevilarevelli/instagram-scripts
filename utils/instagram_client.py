import json
import logging
import time
from pathlib import Path

from instagrapi import Client
from instagrapi.exceptions import LoginRequired, RateLimitError

from utils.config import Settings

logger = logging.getLogger(__name__)

RETRY_DELAY = 60
MAX_RETRIES = 3


class InstagramClient:
    def __init__(self, settings: Settings, load_session: bool = True):
        self.settings = settings
        self.client = Client()
        if load_session:
            self._load_session()

    def _load_session(self) -> None:
        session_file = self.settings.session_file
        if session_file.exists():
            with open(session_file) as f:
                self.client.set_settings(json.load(f))
            logger.info("Loaded saved session")

    def _save_session(self) -> None:
        session_file = self.settings.session_file
        session_file.parent.mkdir(parents=True, exist_ok=True)
        with open(session_file, "w") as f:
            json.dump(self.client.get_settings(), f, indent=2)
        logger.info("Session saved")

    def login(self) -> None:
        try:
            self.client.login(self.settings.username, self.settings.password)
            self._save_session()
            logger.info("Logged in successfully")
        except LoginRequired:
            logger.warning("Session expired, relogging in")
            self.client.set_settings({})
            self.client.login(self.settings.username, self.settings.password)
            self._save_session()

    def get_following(self) -> list[dict]:
        return self.client.user_following(self.client.user_id)

    def get_user_medias(self, user_id: int, amount: int = 1) -> list[dict]:
        return self.client.user_medias(user_id, amount)

    def unfollow(self, user_id: int) -> bool:
        return self.client.user_unfollow(user_id)

    def rate_limited_call(self, func, *args, **kwargs):
        for attempt in range(MAX_RETRIES):
            try:
                return func(*args, **kwargs)
            except RateLimitError:
                wait = RETRY_DELAY * (attempt + 1)
                logger.warning(
                    "Rate limited. Waiting %s seconds (attempt %s/%s)...",
                    wait, attempt + 1, MAX_RETRIES,
                )
                time.sleep(wait)
        raise RuntimeError(f"Failed after {MAX_RETRIES} retries due to rate limiting")
