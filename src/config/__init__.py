import os
import yaml
from pathlib import Path
from typing import Any, Dict

# Global cache so we only read the file once
_CONFIG: Dict[str, Any] | None = None

_DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "defaults.yaml"
_ENV_VAR = "DART_CONFIG_PATH"


def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_config() -> Dict[str, Any]:
    """Return the global configuration dictionary.

    Loading precedence:
    1. Environment variable `DART_CONFIG_PATH`
    2. `config/defaults.yaml` shipped with the repository
    """
    global _CONFIG  # noqa: PLW0603
    if _CONFIG is not None:
        return _CONFIG

    path_value = os.getenv(_ENV_VAR)
    config_path = Path(path_value) if path_value else _DEFAULT_CONFIG_PATH
    _CONFIG = _load_yaml(config_path)
    return _CONFIG


# Convenience helpers ---------------------------------------------------------------------------

def get_safety_limits() -> Dict[str, Any]:
    cfg = get_config()
    return cfg.get("safety_limits", {})


def get_controller_params(name: str | None = None) -> Dict[str, Any]:
    cfg = get_config().get("controller", {})
    return cfg if name is None else cfg.get(name, {}) 