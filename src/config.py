"""
config.py
=========
Central configuration for Pune Convex Mirror Atlas.

Loads environment variables from .env (via python-dotenv),
validates required credentials, and exposes a single AppConfig
dataclass to the rest of the application.

Usage
-----
    from src.config import get_config
    cfg = get_config()
    print(cfg.google_maps_api_key)

Fails fast if a required credential is missing.
NEVER prints or logs API key values.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# ── Paths ────────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
RESULTS_DIR = DATA_DIR / "results"


def _ensure_dirs() -> None:
    for d in (RAW_DIR, PROCESSED_DIR, RESULTS_DIR):
        d.mkdir(parents=True, exist_ok=True)


# ── Config dataclass ─────────────────────────────────────────────────────────

@dataclass
class AppConfig:
    # ── API credentials ───────────────────────────────────────────────────
    google_maps_api_key: str = ""
    google_street_view_api_key: str = ""  # falls back to google_maps_api_key

    # ── Safety / cost limits ──────────────────────────────────────────────
    max_candidate_points: int = 10
    max_panoramas: int = 10
    max_images: int = 80
    max_api_requests: int = 100

    # ── Street View image settings ────────────────────────────────────────
    image_width: int = 640
    image_height: int = 640
    headings: list[int] = field(default_factory=lambda: [0, 45, 90, 135, 180, 225, 270, 315])
    pitch: int = 0          # degrees; 0 = horizontal
    fov: int = 90           # field of view in degrees

    # ── Geographic area ───────────────────────────────────────────────────
    area_name: str = "Ganga Dham"
    area_city: str = "Pune"
    area_state: str = "Maharashtra"
    area_country: str = "India"

    # Approximate center of Ganga Dham, Bibwewadi
    center_lat: float = 18.4739
    center_lon: float = 73.8601

    # Candidate sampling distance in meters
    sampling_distance_m: int = 40

    # ── Logging ───────────────────────────────────────────────────────────
    log_level: str = "INFO"

    # ── Paths ─────────────────────────────────────────────────────────────
    project_root: Path = field(default_factory=lambda: PROJECT_ROOT)
    raw_dir: Path = field(default_factory=lambda: RAW_DIR)
    processed_dir: Path = field(default_factory=lambda: PROCESSED_DIR)
    results_dir: Path = field(default_factory=lambda: RESULTS_DIR)

    @property
    def effective_street_view_key(self) -> str:
        """Return the Street View API key, falling back to the Maps key."""
        return self.google_street_view_api_key or self.google_maps_api_key

    def has_api_key(self) -> bool:
        return bool(self.google_maps_api_key)

    def validate(self) -> None:
        """Raise EnvironmentError if required credentials are missing."""
        missing = []
        if not self.google_maps_api_key:
            missing.append("GOOGLE_MAPS_API_KEY")
        if missing:
            raise EnvironmentError(
                f"Missing required environment variable(s): {', '.join(missing)}\n"
                f"Copy .env.example to .env and fill in your Google Maps API key.\n"
                f"See README.md -> 'API Configuration' for setup instructions."
            )


# ── Factory ───────────────────────────────────────────────────────────────────

_config: Optional[AppConfig] = None


def get_config(env_file: Optional[Path] = None, validate: bool = False) -> AppConfig:
    """
    Return the singleton AppConfig.

    Parameters
    ----------
    env_file:
        Path to the .env file. Defaults to PROJECT_ROOT/.env.
    validate:
        If True, raises EnvironmentError when API keys are missing.
        Set to False during testing and project scaffolding.
    """
    global _config

    if _config is not None:
        return _config

    # Load .env file (does not override already-set environment variables)
    env_path = env_file or (PROJECT_ROOT / ".env")
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=False)

    _config = AppConfig(
        google_maps_api_key=os.getenv("GOOGLE_MAPS_API_KEY", ""),
        google_street_view_api_key=os.getenv("GOOGLE_STREET_VIEW_API_KEY", ""),
        max_candidate_points=int(os.getenv("MAX_CANDIDATE_POINTS", "10")),
        max_panoramas=int(os.getenv("MAX_PANORAMAS", "10")),
        max_images=int(os.getenv("MAX_IMAGES", "80")),
        max_api_requests=int(os.getenv("MAX_API_REQUESTS", "100")),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
    )

    _ensure_dirs()

    if validate:
        _config.validate()

    return _config


def reset_config() -> None:
    """Reset the singleton — used in tests."""
    global _config
    _config = None
