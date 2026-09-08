"""
test_config.py
==============
Tests for configuration loading, validation, and missing-key behaviour.
All tests run without real API credentials.
"""

import os
import pytest
from pathlib import Path

# Ensure config singleton is reset between tests
import src.config as config_module


@pytest.fixture(autouse=True)
def reset_config():
    """Reset config singleton before each test."""
    config_module.reset_config()
    yield
    config_module.reset_config()


def test_config_loads_without_env_file(tmp_path):
    """Config should load even if .env file doesn't exist."""
    cfg = config_module.get_config(env_file=tmp_path / "nonexistent.env")
    assert cfg is not None


def test_config_defaults():
    """Default values should be set correctly."""
    cfg = config_module.get_config()
    assert cfg.max_candidate_points == 10
    assert cfg.max_panoramas == 10
    assert cfg.max_images == 80
    assert cfg.max_api_requests == 100
    assert cfg.area_name == "Ganga Dham"
    assert cfg.center_lat == pytest.approx(18.4739, abs=0.001)
    assert cfg.center_lon == pytest.approx(73.8601, abs=0.001)


def test_config_singleton():
    """get_config() should return the same object on repeated calls."""
    cfg1 = config_module.get_config()
    cfg2 = config_module.get_config()
    assert cfg1 is cfg2


def test_missing_api_key_raises(monkeypatch):
    """validate() should raise EnvironmentError when API key is missing."""
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)
    cfg = config_module.get_config()
    cfg.google_maps_api_key = ""
    with pytest.raises(EnvironmentError, match="GOOGLE_MAPS_API_KEY"):
        cfg.validate()


def test_has_api_key_false_when_empty():
    cfg = config_module.get_config()
    cfg.google_maps_api_key = ""
    assert not cfg.has_api_key()


def test_has_api_key_true_when_set():
    cfg = config_module.get_config()
    cfg.google_maps_api_key = "fake-key-for-testing"
    assert cfg.has_api_key()


def test_effective_street_view_key_fallback():
    """Should fall back to maps key when SV key is empty."""
    cfg = config_module.get_config()
    cfg.google_maps_api_key = "maps-key"
    cfg.google_street_view_api_key = ""
    assert cfg.effective_street_view_key == "maps-key"


def test_effective_street_view_key_uses_sv_key():
    """Should use SV key when provided."""
    cfg = config_module.get_config()
    cfg.google_maps_api_key = "maps-key"
    cfg.google_street_view_api_key = "sv-key"
    assert cfg.effective_street_view_key == "sv-key"


def test_config_from_env_vars(monkeypatch, tmp_path):
    """Config should pick up environment variables."""
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "test-key-123")
    monkeypatch.setenv("MAX_CANDIDATE_POINTS", "25")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    cfg = config_module.get_config(env_file=tmp_path / "no.env")
    assert cfg.google_maps_api_key == "test-key-123"
    assert cfg.max_candidate_points == 25
    assert cfg.log_level == "DEBUG"
