"""College Scorecard API client (api.data.gov).

Requires SCORECARD_API_KEY in .env for reliable discovery (see docs/DELIVERY_CHANNEL.md §8).
Falls back to shared DEMO_KEY when unset — heavily rate-limited.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

BASE_URL = "https://api.data.gov/ed/collegescorecard/v1/schools"

DEFAULT_FIELDS = [
    "id",
    "school.name",
    "school.city",
    "school.state",
    "school.school_url",
    "latest.school.ownership",
    "latest.cost.tuition.in_state",
    "latest.cost.tuition.out_of_state",
    "latest.cost.avg_net_price.public",
    "latest.cost.avg_net_price.private",
    "latest.admissions.admission_rate.overall",
    "latest.admissions.sat_scores.average.overall",
    "latest.admissions.act_scores.midpoint.cumulative",
    "latest.academics.program_available.assoc_or_bachelors",
    "latest.student.size",
    "latest.academics.program_percentage.bachelors.business_marketing",
]


def api_key() -> str:
    return (
        os.environ.get("SCORECARD_API_KEY", "").strip()
        or os.environ.get("COLLEGE_SCORECARD_API_KEY", "").strip()
        or "DEMO_KEY"
    )


def _get(params: Dict[str, Any], *, timeout: int = 15, retries: int = 3) -> Dict[str, Any]:
    items: List[tuple] = []
    for key, value in params.items():
        if value is None or value == "":
            continue
        if key == "school.state" and isinstance(value, list):
            for state in value:
                items.append(("school.state", state))
        else:
            items.append((key, value))
    items.append(("api_key", api_key()))
    url = f"{BASE_URL}?{urllib.parse.urlencode(items)}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    last_exc: Exception = RuntimeError("No attempts made")
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"College Scorecard HTTP {exc.code}: {body[:400]}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_exc = exc
            if attempt < retries - 1:
                wait = 2 ** attempt  # 1s, 2s
                print(f"  [scorecard] Attempt {attempt + 1} failed ({exc}), retrying in {wait}s…")
                time.sleep(wait)
    raise RuntimeError(f"College Scorecard unavailable after {retries} attempts: {last_exc}") from last_exc


def fetch_school_by_id(scorecard_id: int, *, fields: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
    payload = _get({
        "fields": ",".join(fields or DEFAULT_FIELDS),
        "id": int(scorecard_id),
    })
    results = payload.get("results") or []
    if not results:
        return None
    return parse_row(results[0])


def search_schools(
    *,
    states: Optional[List[str]] = None,
    name: Optional[str] = None,
    per_page: int = 100,
    page: int = 0,
    fields: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    params: Dict[str, Any] = {
        "fields": ",".join(fields or DEFAULT_FIELDS),
        "per_page": per_page,
        "page": page,
        "school.degrees_awarded.predominant": 3,
    }
    if name:
        params["school.name"] = name
    if states:
        params["school.state"] = states

    payload = _get(params)
    return payload.get("results") or []


def ownership_label(code: Any) -> str:
    mapping = {1: "Public", 2: "Private", 3: "Private"}
    try:
        return mapping.get(int(code), "Private")
    except (TypeError, ValueError):
        return "Private"


def parse_row(row: Dict[str, Any]) -> Dict[str, Any]:
    biz_raw = row.get("latest.academics.program_percentage.bachelors.business_marketing")
    biz_pct = float(biz_raw) if biz_raw is not None else 0.0
    ownership = row.get("latest.school.ownership")
    pub_net = _int_or_none(row.get("latest.cost.avg_net_price.public"))
    priv_net = _int_or_none(row.get("latest.cost.avg_net_price.private"))
    avg_net_price = pub_net if ownership == 1 else (priv_net if ownership in (2, 3) else (pub_net or priv_net))
    return {
        "scorecard_id": row.get("id"),
        "scorecard_name": row.get("school.name") or "",
        "city": row.get("school.city") or "",
        "state": row.get("school.state") or "",
        "school_url": row.get("school.school_url") or "",
        "public_private": ownership_label(ownership),
        "tuition_in_state": _int_or_none(row.get("latest.cost.tuition.in_state")),
        "tuition_out_of_state": _int_or_none(row.get("latest.cost.tuition.out_of_state")),
        "avg_net_price": avg_net_price,
        "admission_rate": _float_or_none(row.get("latest.admissions.admission_rate.overall")),
        "avg_admit_sat": _int_or_none(row.get("latest.admissions.sat_scores.average.overall")),
        "avg_admit_act": _int_or_none(row.get("latest.admissions.act_scores.midpoint.cumulative")),
        "offers_bachelors": bool(row.get("latest.academics.program_available.assoc_or_bachelors")),
        "student_size": _int_or_none(row.get("latest.student.size")),
        "business_program_pct": biz_pct,
    }


def _int_or_none(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return None


def _float_or_none(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
