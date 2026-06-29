"""Append-only JSONL audit log for Pro-path research and pipeline runs."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from pro_config import load_pro_config

SECRET_KEY_RE = re.compile(
    r"(api[_-]?key|secret|token|password|authorization|credential)",
    re.IGNORECASE,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _sanitize_fields(fields: Dict[str, Any]) -> Dict[str, Any]:
    clean: Dict[str, Any] = {}
    for key, value in fields.items():
        if SECRET_KEY_RE.search(key):
            continue
        if isinstance(value, str) and SECRET_KEY_RE.search(value):
            clean[key] = "[redacted]"
            continue
        clean[key] = value
    return clean


def log_path() -> Optional[Path]:
    cfg = load_pro_config()
    logging_cfg = cfg.get("logging", {})
    if not logging_cfg.get("enabled", True):
        return None
    return Path(logging_cfg["path"])


def log_event(event: str, **fields: Any) -> None:
    """Append one JSON line. No-op when logging disabled or on I/O error."""
    path = log_path()
    if path is None:
        return
    record = {
        "ts": _utc_now(),
        "event": event,
        **_sanitize_fields(fields),
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        pass


def log_research(
    *,
    backend: str,
    school: str,
    scope: str,
    source_urls: Optional[list] = None,
    validator_ok: Optional[bool] = None,
    validator_errors: Optional[int] = None,
    validator_warnings: Optional[int] = None,
    notes: Optional[str] = None,
) -> None:
    log_event(
        "research",
        backend=backend,
        school=school,
        scope=scope,
        source_urls=source_urls or [],
        validator_ok=validator_ok,
        validator_errors=validator_errors,
        validator_warnings=validator_warnings,
        notes=notes,
    )


def log_validate(*, ok: bool, errors: int, warnings: int, cache_path: str) -> None:
    cfg = load_pro_config()
    log_event(
        "validate",
        backend=cfg.get("research_backend", "cursor"),
        ok=ok,
        errors=errors,
        warnings=warnings,
        cache_path=cache_path,
    )


def log_matcher_run(*, profile_path: str, summary: Dict[str, Any]) -> None:
    cfg = load_pro_config()
    log_event(
        "matcher_run",
        backend=cfg.get("research_backend", "cursor"),
        profile_path=profile_path,
        safety=len(summary.get("safety", [])),
        target=len(summary.get("target", [])),
        reach=len(summary.get("reach", [])),
        excluded=summary.get("excluded_count", 0),
    )


def log_sheet_build(*, profile_path: str, rows: int, outputs: list) -> None:
    cfg = load_pro_config()
    log_event(
        "sheet_build",
        backend=cfg.get("research_backend", "cursor"),
        profile_path=profile_path,
        rows=rows,
        outputs=outputs,
    )
