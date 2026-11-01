"""Pure bounded public evidence history; no private text, writes or authority.

Apply docs/AUTOMATED_ENGINEERING.md. Digests identify local evidence records;
neither a digest nor a role name authenticates a worker or external provider.
"""

import hashlib
import json
import re
from datetime import UTC, datetime, timedelta

MAX_BYTES = 24576
MAX_RECORDS = 48
MAX_INPUT_EVENTS = 512
WORKERS = (
    "sug",
    "reinhardt",
    "hoffmann",
    "weber",
    "schneider",
    "vogel",
    "fischer",
    "johanna",
    "braun",
    "hartmann",
    "krueger",
    "mueller",
    "adler",
    "richter",
    "bergmann",
)
COUNTS = ("results", "controller_results", "reviews_received", "no_change")
EVENT_KEYS = {
    "event_id",
    "kind",
    "employee_id",
    "attribution_basis",
    "observed_at",
    "task_reference",
    "result_reference",
    "evidence_reference",
    "source_revision",
    "stage",
    "summary_code",
    "public_reference",
    "subject_employee_id",
    "change_code",
    "repository_code",
    "release_target",
}
ACTIVITY_KEYS = {
    "schema_version",
    "scope",
    "window_from",
    "window_until",
    "collected_at",
    "coverage",
    "truncated",
    "hours",
    "events",
}
KINDS = {
    "result": {"recorded": "result_recorded", "no_change": "explicit_no_change"},
    "controller_result": {
        "recorded": "controller_result_recorded",
        "no_change": "explicit_no_change",
    },
    "review": {
        key: "review_" + key for key in ("accepted", "rejected", "inconclusive")
    },
    "engineering": {"pushed": "code_pushed", "deployed": "site_deployed"},
}
PUBLIC_REPO = "https://github.com/FussballSug/blitzwerk-quant-site/"
CHANGES = {
    "hourly_activity_and_team_flow": "Added hourly worker evidence and the interactive team flow view",
    "static_public_report": "Added the independently hosted public reporting view",
    "reporting_reliability": "Improved reporting reliability",
    "reporting_reliability_and_team_flow": "Improved reporting reliability and retained the team flow and hourly views",
    "bounded_performance": "Improved measured performance within existing limits",
    "evidence_validation": "Improved evidence validation and regression coverage",
}
CONTROLLER_SUMMARIES = (
    "status_check_recorded",
    "incident_diagnosis_recorded",
    "snapshot_prepared",
)


def require(value):
    if not value:
        raise ValueError("Exact bounded public activity required")


def encoded(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def timestamp(value):
    require(
        type(value) is str
        and re.fullmatch(
            r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,6})?(?:Z|\+00:00)", value
        )
    )
    parsed = datetime.fromisoformat(value)
    require(parsed.year >= 1970 and parsed.utcoffset() == timedelta(0))
    return parsed


def _hex(value, length=64):
    return (
        type(value) is str
        and re.fullmatch("[a-f0-9]{" + str(length) + "}", value) is not None
    )


def _event(value, *, first, last):
    require(type(value) is dict and set(value) == EVENT_KEYS)
    require(
        _hex(value["event_id"])
        and value["event_id"]
        == digest({k: v for k, v in value.items() if k != "event_id"})
    )
    kind, stage = value["kind"], value["stage"]
    require(
        type(kind) is str
        and kind in KINDS
        and type(stage) is str
        and stage in KINDS[kind]
    )
    employee, basis = value["employee_id"], value["attribution_basis"]
    require(employee is None or type(employee) is str and employee in WORKERS)
    subject = value["subject_employee_id"]
    if kind == "review":
        require(
            employee is None
            and basis == "unknown"
            and (subject is None or type(subject) is str and subject in WORKERS)
        )
    else:
        require(subject is None)
        require(
            basis
            == ("unknown" if kind == "engineering" else "historical_role_unmapped")
            if employee is None
            else basis
            == (
                "controller_responsibility"
                if kind == "controller_result"
                else "assigned_role"
            )
        )
    summary = value["summary_code"]
    historical = employee is None and kind in {"result", "controller_result"}
    if historical:
        require(stage == "recorded" and summary == "historical_" + kind + "_recorded")
    else:
        require(
            summary == KINDS[kind][stage]
            or kind == "controller_result"
            and stage == "recorded"
            and summary in CONTROLLER_SUMMARIES
        )
    at = timestamp(value["observed_at"])
    require(first <= at <= last and value["observed_at"] == at.isoformat())
    require(
        all(
            _hex(value[key])
            for key in ("task_reference", "result_reference", "evidence_reference")
        )
    )
    revision = value["source_revision"]
    require(revision is None or _hex(revision, 40))
    link = value["public_reference"]
    if kind == "engineering":
        require(employee is None and basis == "unknown")
        require(
            _hex(revision, 40)
            and type(value["change_code"]) is str
            and value["change_code"] in CHANGES
        )
        require(value["repository_code"] in ("platform", "website"))
        if value["repository_code"] == "platform":
            require(
                link is None
                and stage == "pushed"
                and value["release_target"] == "branch"
            )
        else:
            require(type(link) is str and len(link) <= 200)
            require(
                link == PUBLIC_REPO + "commit/" + revision
                and value["release_target"] in ("branch", "default_branch")
                if stage == "pushed"
                else re.fullmatch(
                    re.escape(PUBLIC_REPO) + r"actions/runs/[1-9][0-9]{0,19}", link
                )
                and value["release_target"] == "website"
            )
    else:
        require(
            link is None
            and value["change_code"] is None
            and value["repository_code"] is None
            and value["release_target"] is None
        )
    return value


def make_event(**fields):
    fields.setdefault("subject_employee_id", None)
    fields.setdefault("change_code", None)
    fields.setdefault("repository_code", None)
    fields.setdefault("release_target", None)
    require(set(fields) == EVENT_KEYS - {"event_id"})
    fields["observed_at"] = timestamp(fields["observed_at"]).isoformat()
    value = {"event_id": digest(fields), **fields}
    at = timestamp(value["observed_at"])
    return json.loads(encoded(_event(value, first=at, last=at)))


def validate_activity(value, *, now=None):
    require(type(value) is dict and set(value) == ACTIVITY_KEYS)
    require(
        type(value["schema_version"]) is int
        and value["schema_version"] == 1
        and value["scope"] == "public_activity_projection"
    )
    first, last = timestamp(value["window_from"]), timestamp(value["window_until"])
    collected = timestamp(value["collected_at"])
    require(
        first == last.replace(minute=0, second=0, microsecond=0) - timedelta(hours=23)
        and first <= last == collected
    )
    if now is not None:
        require(now.tzinfo is not None and collected <= now)
    require(
        type(value["coverage"]) is str
        and value["coverage"] in {"complete_query", "partial", "unavailable"}
        and type(value["truncated"]) is bool
    )
    hours, events = value["hours"], value["events"]
    require(
        type(hours) is list
        and type(events) is list
        and len(hours) <= 24
        and len(hours) + len(events) <= MAX_RECORDS
    )
    if value["coverage"] == "unavailable":
        require(not hours and not events)
    elif not value["truncated"]:
        require(len(hours) == 24)
    seen = set()
    for hour in hours:
        require(
            type(hour) is dict
            and set(hour) == {"hour_start", "evidence_reference", *COUNTS}
        )
        at = timestamp(hour["hour_start"])
        require(
            first <= at <= last
            and at == at.replace(minute=0, second=0, microsecond=0)
            and at not in seen
            and _hex(hour["evidence_reference"])
        )
        seen.add(at)
        for key in COUNTS:
            require(
                type(hour[key]) is list
                and len(hour[key]) == len(WORKERS)
                and all(
                    type(n) is int and 0 <= n <= MAX_INPUT_EVENTS for n in hour[key]
                )
            )
        require(
            all(
                hour["no_change"][i]
                <= hour["results"][i] + hour["controller_results"][i]
                for i in range(len(WORKERS))
            )
        )
    require(
        hours == sorted(hours, key=lambda h: timestamp(h["hour_start"]), reverse=True)
    )
    require(
        sum(sum(hour[key]) for hour in hours for key in COUNTS if key != "no_change")
        <= MAX_INPUT_EVENTS
    )
    seen = set()
    for item in events:
        _event(item, first=first, last=last)
        require(item["event_id"] not in seen)
        seen.add(item["event_id"])
    require(
        events
        == sorted(
            events,
            key=lambda e: (timestamp(e["observed_at"]), e["event_id"]),
            reverse=True,
        )
    )
    buckets = {timestamp(hour["hour_start"]) for hour in hours}
    require(
        all(
            timestamp(e["observed_at"]).replace(minute=0, second=0, microsecond=0)
            in buckets
            for e in events
        )
    )
    for hour in hours:
        start = timestamp(hour["hour_start"])
        subset = [
            e
            for e in events
            if start <= timestamp(e["observed_at"]) < start + timedelta(hours=1)
        ]
        lower = _counts(subset)
        for key in COUNTS:
            require(
                all(
                    hour[key][i] >= lower[key][i]
                    if value["truncated"]
                    else hour[key][i] == lower[key][i]
                    for i in range(len(WORKERS))
                )
            )
        if not value["truncated"]:
            require(
                hour["evidence_reference"]
                == digest(sorted(e["event_id"] for e in subset))
            )
    require(len(encoded(value)) <= MAX_BYTES)
    return json.loads(encoded(value))


def _trim(value, fits):
    while not fits(value):
        value["truncated"] = True
        if value["events"]:
            value["events"].pop()
        elif value["hours"]:
            value["hours"].pop()
        else:
            raise ValueError("No space for the minimal public activity envelope")
    return value


def _counts(events):
    counts = {key: [0] * len(WORKERS) for key in COUNTS}
    for event in events:
        worker = (
            event["subject_employee_id"]
            if event["kind"] == "review"
            else event["employee_id"]
        )
        if worker is None:
            continue
        position = WORKERS.index(worker)
        key = {
            "result": "results",
            "controller_result": "controller_results",
            "review": "reviews_received",
        }.get(event["kind"])
        if key:
            counts[key][position] += 1
        if event["stage"] == "no_change":
            counts["no_change"][position] += 1
    return counts


def project_activity(events, *, now, coverage="complete_query", truncated=False):
    require(type(events) is list and len(events) <= MAX_INPUT_EVENTS)
    require(now.tzinfo is not None and now.utcoffset() == timedelta(0))
    last = now.astimezone(UTC)
    first = last.replace(minute=0, second=0, microsecond=0) - timedelta(hours=23)
    require(
        type(coverage) is str
        and coverage in {"complete_query", "partial", "unavailable"}
    )
    require(type(truncated) is bool)
    require(coverage != "unavailable" or not events)
    retained, seen = [], set()
    for value in events:
        at = timestamp(value["observed_at"])
        _event(value, first=datetime(1970, 1, 1, tzinfo=UTC), last=last)
        require(value["event_id"] not in seen)
        seen.add(value["event_id"])
        if at >= first:
            retained.append(json.loads(encoded(value)))
    retained.sort(
        key=lambda e: (timestamp(e["observed_at"]), e["event_id"]), reverse=True
    )
    hours = []
    if coverage != "unavailable":
        for i in range(24):
            start = first + timedelta(hours=i)
            subset = [
                e
                for e in retained
                if start <= timestamp(e["observed_at"]) < start + timedelta(hours=1)
            ]
            hours.append(
                {
                    "hour_start": start.isoformat(),
                    "evidence_reference": digest(sorted(e["event_id"] for e in subset)),
                    **_counts(subset),
                }
            )
    value = {
        "schema_version": 1,
        "scope": "public_activity_projection",
        "window_from": first.isoformat(),
        "window_until": last.isoformat(),
        "collected_at": last.isoformat(),
        "coverage": coverage,
        "truncated": truncated,
        "hours": list(reversed(hours)),
        "events": retained,
    }
    _trim(
        value,
        lambda v: (
            len(v["hours"]) + len(v["events"]) <= MAX_RECORDS
            and len(encoded(v)) <= MAX_BYTES
        ),
    )
    return validate_activity(value, now=now)


def fit_snapshot_activity(snapshot, activity):
    """Do not trim, restamp, or reinterpret any pre-existing operational field."""
    require(
        type(snapshot) is dict
        and type(snapshot.get("schema_version")) is int
        and snapshot["schema_version"] == 2
        and "activity" not in snapshot
    )
    out = json.loads(encoded(snapshot))
    out["schema_version"] = 3
    out["activity"] = validate_activity(activity)
    _trim(out["activity"], lambda _: len(encoded(out)) <= 65536)
    validate_activity(out["activity"])
    return out
