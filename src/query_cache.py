from __future__ import annotations

import json
from collections import defaultdict
from threading import Lock
from typing import Any

DOMAIN_ATHLETES = "athletes"
DOMAIN_EVENTS = "events"
DOMAIN_MATCHES = "matches"
DOMAIN_FORMULAS = "formulas"

_VERSIONS: defaultdict[str, int] = defaultdict(int)
_VERSIONS_LOCK = Lock()


def get_cache_version(domain: str) -> int:
    return int(_VERSIONS[domain])


def bump_cache_version(*domains: str) -> None:
    if not domains:
        return

    with _VERSIONS_LOCK:
        for domain in domains:
            _VERSIONS[domain] += 1


def build_signature(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=True,
        default=str,
        separators=(",", ":"),
    )
