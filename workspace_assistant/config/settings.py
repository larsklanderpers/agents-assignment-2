"""
Configuration management.

Loads settings from environment variables.
Students should not need to modify this file.
"""

import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv


@dataclass
class Settings:
    """Application settings."""

    model_name: str = "gemini-3.5-flash"
    google_credentials_path: Optional[Path] = None
    debug_mode: bool = False
    enable_retry: bool = True
    max_retries: int = 3
    retry_delay: float = 1.0
    calendar_max_results: int = 50

    def __init__(self):
        load_dotenv()

        self.model_name = os.getenv("MODEL_NAME", "gemini-3.5-flash")
        creds_path = os.getenv("GOOGLE_CREDENTIALS_PATH")
        if creds_path:
            self.google_credentials_path = Path(creds_path)
        else:
            self.google_credentials_path = (
                Path(__file__).parent / "credentials" / "credentials.json"
            )

        self.debug_mode = os.getenv("DEBUG", "false").lower() == "true"
        self.enable_retry = os.getenv("ENABLE_RETRY", "true").lower() == "true"
        self.max_retries = int(os.getenv("MAX_RETRIES", "3"))
        self.retry_delay = float(os.getenv("RETRY_DELAY", "1.0"))
        self.calendar_max_results = int(os.getenv("CALENDAR_MAX_RESULTS", "50"))

    def validate(self) -> bool:
        """Check if configuration is valid."""
        if not self.google_credentials_path.exists():
            print(f"Warning: Credentials not found at {self.google_credentials_path}")
            return False
        return True
