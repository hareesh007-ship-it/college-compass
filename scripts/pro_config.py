"""Pro-path runtime config — secrets from env, settings from config/pro.json."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

from _paths import CONFIG, LOGS, STUDENT_ROOT

DEFAULT_PRO_CONFIG: Dict[str, Any] = {
    "research_backend": "cursor",
    "logging": {
        "enabled": True,
        "path": "data/logs/research_log.jsonl",
        "level": "info",
    },
}

VALID_BACKENDS = frozenset({"cursor", "openai", "anthropic", "local"})
VALID_LOG_LEVELS = frozenset({"debug", "info", "warn", "error"})


def _resolve_path(raw: str) -> Path:
    path = Path(raw)
    if not path.is_absolute():
        path = STUDENT_ROOT / path
    return path


def load_pro_config() -> Dict[str, Any]:
    """Load config/pro.json merged over defaults. Missing file is OK.

    Backend resolution order (highest priority first):
      1. COLLEGE_COMPASS_BACKEND env var  — set by college-compass-free / college-compass-pro entry points
      2. config/pro.json research_backend field
      3. DEFAULT_PRO_CONFIG fallback (cursor)
    """
    cfg: Dict[str, Any] = json.loads(json.dumps(DEFAULT_PRO_CONFIG))
    path = CONFIG / "pro.json"
    if path.is_file():
        with open(path, encoding="utf-8") as f:
            user = json.load(f)
        if isinstance(user, dict):
            if "logging" in user and isinstance(user["logging"], dict):
                cfg["logging"].update(user["logging"])
                user = {k: v for k, v in user.items() if k != "logging"}
            cfg.update(user)

    # Env var override — used by college-compass-free and college-compass-pro entry points
    env_backend = os.environ.get("COLLEGE_COMPASS_BACKEND", "").strip().lower()
    if env_backend in VALID_BACKENDS:
        cfg["research_backend"] = env_backend

    backend = str(cfg.get("research_backend", "cursor")).lower()
    if backend not in VALID_BACKENDS:
        backend = "cursor"
    cfg["research_backend"] = backend
    logging_cfg = cfg.setdefault("logging", {})
    level = str(logging_cfg.get("level", "info")).lower()
    logging_cfg["level"] = level if level in VALID_LOG_LEVELS else "info"
    logging_cfg["enabled"] = bool(logging_cfg.get("enabled", True))
    logging_cfg["path"] = _resolve_path(str(logging_cfg.get("path", str(LOGS / "research_log.jsonl"))))
    return cfg


def api_keys_from_env() -> Dict[str, str]:
    """Return configured API keys from environment (never log these values)."""
    keys: Dict[str, str] = {}
    for env_name in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        value = os.environ.get(env_name, "").strip()
        if value:
            keys[env_name] = value
    return keys
