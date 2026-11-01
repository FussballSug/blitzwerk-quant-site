"""Pure bounded operational display with explicit omitted-history coverage.

Apply docs/AUTOMATED_ENGINEERING.md. Full private history is never modified.
This module changes display selection, not health, authority or source facts.
"""

import json
import math

KINDS = ("trading", "improvement", "incident", "publishing")
MAX_COUNT = 1_000_000_000
MAX_QUERIED = 1000
MAX_BASE_BYTES = 40000
MAX_PER_KIND = 4
MAX_HISTORY = 4
MAX_REFERENCES = 4
MAX_INCIDENTS = 16
COVERAGE_KEYS = {
    "schema_version",
    "scope",
    "selection",
    "source_counts",
    "queried_counts",
    "displayed_counts",
    "workflow_kinds",
    "history_counts",
    "artifact_reference_counts",
    "query_truncated",
    "display_truncated",
    "partial",
}


def _need(value):
    if not value:
        raise ValueError("Exact bounded public operations coverage required")


def _count(value, *, unknown=False):
    _need(unknown and value is None or type(value) is int and 0 <= value <= MAX_COUNT)
    return value


def _rows(operations, key):
    value = operations.get(key, [])
    if type(value) is not list:
        return []
    _need(len(value) <= MAX_QUERIED)
    return value


def _sequence(row, key):
    value = row.get(key, [])
    return value if type(value) is list else []


def _recent(row, key="updated_at"):
    value = row.get(key)
    at = (
        value
        if type(value) in (int, float) and math.isfinite(value) and value >= 0
        else -1
    )
    name = row.get("run_id", row.get("incident_id", ""))
    return at, name if type(name) is str else ""


def select_public_operations(operations):
    """Select before the legacy sanitizer's first200 cap can starve a kind."""
    operations = operations if type(operations) is dict else {}
    selected = dict(operations)
    workflows = []
    for kind in KINDS:
        candidates = [
            r
            for r in _rows(operations, "workflows")
            if type(r) is dict and r.get("kind") == kind
        ]
        for row in sorted(candidates, key=_recent, reverse=True)[:MAX_PER_KIND]:
            workflows.append(
                {
                    **row,
                    "history": _sequence(row, "history")[-MAX_HISTORY:],
                    "artifact_digests": _sequence(row, "artifact_digests")[
                        -MAX_REFERENCES:
                    ],
                }
            )
    selected["workflows"] = workflows
    selected["incidents"] = sorted(
        (r for r in _rows(operations, "incidents") if type(r) is dict),
        key=lambda r: _recent(r, "last_seen"),
        reverse=True,
    )[:MAX_INCIDENTS]
    return selected


def _totals(rows):
    kinds = {
        kind: sum(type(r) is dict and r.get("kind") == kind for r in rows)
        for kind in KINDS
    }
    history = sum(len(_sequence(r, "history")) for r in rows if type(r) is dict)
    refs = sum(len(_sequence(r, "artifact_digests")) for r in rows if type(r) is dict)
    return kinds, history, refs


def _coverage(raw, snapshot):
    rows, incidents = _rows(raw, "workflows"), _rows(raw, "incidents")
    queried_kinds, history, references = _totals(rows)
    shown_kinds, shown_history, shown_refs = _totals(snapshot["workflows"])
    counts = raw.get("counts") if type(raw.get("counts")) is dict else {}
    source = {
        key: _count(counts.get(key), unknown=True) for key in ("workflows", "incidents")
    }
    sources = raw.get("source_workflow_counts")
    if sources is None:
        sources = dict.fromkeys(KINDS)
    _need(type(sources) is dict and set(sources) == set(KINDS))
    kinds = {
        kind: {
            "source": _count(sources[kind], unknown=True),
            "queried": queried_kinds[kind],
            "displayed": shown_kinds[kind],
        }
        for kind in KINDS
    }
    queried = {"workflows": len(rows), "incidents": len(incidents)}
    displayed = {
        "workflows": len(snapshot["workflows"]),
        "incidents": len(snapshot["incidents"]),
    }
    query_truncated = (
        raw.get("truncated") is True
        or any(source[k] is not None and source[k] > queried[k] for k in source)
        or any(
            r["source"] is not None and r["source"] > r["queried"]
            for r in kinds.values()
        )
    )
    display_truncated = (
        any(displayed[k] < queried[k] for k in queried)
        or any(r["displayed"] < r["queried"] for r in kinds.values())
        or shown_history < history
        or shown_refs < references
    )
    return {
        "schema_version": 1,
        "scope": "bounded_public_operations",
        "selection": "latest_per_kind_then_recent",
        "source_counts": source,
        "queried_counts": queried,
        "displayed_counts": displayed,
        "workflow_kinds": kinds,
        "history_counts": {"queried": history, "displayed": shown_history},
        "artifact_reference_counts": {"queried": references, "displayed": shown_refs},
        "query_truncated": query_truncated,
        "display_truncated": display_truncated,
        "partial": (
            query_truncated
            or display_truncated
            or any(v is None for v in source.values())
            or any(r["source"] is None for r in kinds.values())
        ),
    }


def validate_operations_coverage(snapshot):
    """Validate counts against the actual displayed arrays, not an inferred history."""
    value = snapshot.get("operations_coverage")
    _need(
        type(value) is dict
        and set(value) == COVERAGE_KEYS
        and type(value["schema_version"]) is int
        and value["schema_version"] == 1
        and value["scope"] == "bounded_public_operations"
        and value["selection"] == "latest_per_kind_then_recent"
    )
    source, queried, shown = (
        value[k] for k in ("source_counts", "queried_counts", "displayed_counts")
    )
    for item in (source, queried, shown):
        _need(type(item) is dict and set(item) == {"workflows", "incidents"})
    for key in source:
        _count(source[key], unknown=True)
        _count(queried[key])
        _count(shown[key])
        _need(
            type(snapshot.get(key)) is list
            and shown[key] == len(snapshot[key]) <= queried[key] <= MAX_QUERIED
            and (source[key] is None or queried[key] <= source[key])
        )
    kinds, history, refs = _totals(snapshot["workflows"])
    recorded = value["workflow_kinds"]
    _need(type(recorded) is dict and set(recorded) == set(KINDS))
    for kind, item in recorded.items():
        _need(type(item) is dict and set(item) == {"source", "queried", "displayed"})
        _count(item["source"], unknown=True)
        _count(item["queried"])
        _count(item["displayed"])
        _need(
            item["displayed"] == kinds[kind] <= item["queried"]
            and (item["source"] is None or item["queried"] <= item["source"])
        )
    _need(
        sum(kinds.values()) == shown["workflows"]
        and sum(r["queried"] for r in recorded.values()) <= queried["workflows"]
    )
    if source["workflows"] is not None:
        known_sources = sum(
            r["source"] for r in recorded.values() if r["source"] is not None
        )
        _need(known_sources <= source["workflows"])
        if all(r["source"] is not None for r in recorded.values()):
            _need(known_sources == source["workflows"])
    for key, count in (
        ("history_counts", history),
        ("artifact_reference_counts", refs),
    ):
        item = value[key]
        _need(type(item) is dict and set(item) == {"queried", "displayed"})
        _count(item["queried"])
        _count(item["displayed"])
        _need(count == item["displayed"] <= item["queried"])
    for key in ("partial", "query_truncated", "display_truncated"):
        _need(type(value[key]) is bool)
    known_query_gap = any(
        source[k] is not None and source[k] > queried[k] for k in source
    ) or any(
        r["source"] is not None and r["source"] > r["queried"]
        for r in recorded.values()
    )
    _need(not known_query_gap or value["query_truncated"])
    display_gap = (
        any(shown[k] < queried[k] for k in queried)
        or any(r["displayed"] < r["queried"] for r in recorded.values())
        or any(
            value[k]["displayed"] < value[k]["queried"]
            for k in ("history_counts", "artifact_reference_counts")
        )
    )
    _need(value["display_truncated"] == display_gap)
    unknown = any(v is None for v in source.values()) or any(
        r["source"] is None for r in recorded.values()
    )
    _need(value["partial"] == (unknown or value["query_truncated"] or display_gap))
    _need(
        snapshot.get("improvements")
        == [r for r in snapshot["workflows"] if r.get("kind") == "improvement"]
    )
    return value


def fit_public_operations(snapshot, operations, activity):
    """Fit only selected history; preserve employee/core fields and activity exactly."""
    from public_activity_projection import encoded, fit_snapshot_activity

    _need(
        type(snapshot) is dict
        and type(snapshot.get("schema_version")) is int
        and snapshot["schema_version"] == 2
    )
    raw = operations if type(operations) is dict else {}
    out = json.loads(encoded(snapshot))
    while True:
        out["improvements"] = [
            r for r in out["workflows"] if r["kind"] == "improvement"
        ]
        out["operations_coverage"] = _coverage(raw, out)
        validate_operations_coverage(out)
        if len(encoded(out)) <= MAX_BASE_BYTES:
            break
        kinds, _, _ = _totals(out["workflows"])
        extra = [r for r in out["workflows"] if kinds[r["kind"]] > 1]
        if extra:
            out["workflows"].remove(min(extra, key=_recent))
        elif out["incidents"]:
            out["incidents"].pop()
        else:
            raise ValueError(
                "Core public operations exceed the fixed display allowance"
            )
    result = fit_snapshot_activity(out, activity)
    _need(result["activity"] == activity and len(encoded(result)) <= 65536)
    result["schema_version"] = 4
    validate_operations_coverage(result)
    return result
