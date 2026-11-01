"""Synthetic dual-schema cases; no real activity or deployment claims."""

import copy
import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import public_activity_projection as activity
import streamlit_app as renderer

NOW = datetime(2026, 11, 1, 7, 30, tzinfo=UTC)


def sample():
    base = json.loads(Path("test_fixtures/observed_public_snapshot.json").read_bytes())
    event = activity.make_event(
        kind="engineering",
        employee_id=None,
        attribution_basis="unknown",
        observed_at=NOW.isoformat(),
        task_reference="a" * 64,
        result_reference="b" * 64,
        evidence_reference="c" * 64,
        source_revision="d" * 40,
        stage="pushed",
        summary_code="code_pushed",
        public_reference=None,
        change_code="reporting_reliability",
        repository_code="platform",
        release_target="branch",
    )
    return activity.fit_snapshot_activity(
        base, activity.project_activity([event], now=NOW)
    )


def cases():
    value = sample()
    out = [
        {
            "input": value,
            "now": NOW.timestamp() * 1000,
            "expected": renderer.refresh_public_snapshot(value, now=NOW),
        }
    ]
    mutations = {
        "event_digest": lambda v: v["activity"]["events"][0].update(event_id="f" * 64),
        "private": lambda v: v["activity"]["events"][0].update(account="private"),
        "missing_hour": lambda v: v["activity"]["hours"].pop(),
        "count_bool": lambda v: v["activity"]["hours"][0]["results"].__setitem__(
            0, True
        ),
        "no_change": lambda v: v["activity"]["hours"][0]["no_change"].__setitem__(0, 1),
        "count": lambda v: v["activity"]["hours"][0]["results"].__setitem__(0, 1),
        "hour_digest": lambda v: v["activity"]["hours"][0].update(
            evidence_reference="f" * 64
        ),
        "future": lambda v: v["activity"]["events"][0].update(
            observed_at="2026-11-02T07:30:00+00:00"
        ),
        "legacy_with_activity": lambda v: v.update(schema_version=2),
        "unknown_version": lambda v: v.update(schema_version=4),
    }
    for name, mutate in mutations.items():
        bad = copy.deepcopy(value)
        mutate(bad)
        try:
            renderer.validate_public_snapshot(bad)
        except ValueError:
            out.append({"input": bad, "reject": True, "name": name})
        else:
            raise AssertionError(name)
    return out


def test_schema3_browser_python_strict_parity():
    import build_static

    rows = cases()
    result = subprocess.run(
        [
            os.environ.get("NODE", "node"),
            "-e",
            """
const {createStaticReader}=require('./static_feed.js');
const assert=require('node:assert/strict'),x=JSON.parse(require('node:fs').readFileSync(0,'utf8'));
const r=createStaticReader({schema:x.schema,initial:x.initial,now:()=>x.now});
for(const row of x.cases){if(row.reject)assert.throws(()=>r.validate(row.input),row.name);else assert.deepEqual(r.refresh(row.input),row.expected);}
console.log(x.cases.length);
""",
        ],
        input=json.dumps(
            {
                "schema": json.loads(build_static.encoded(build_static.schema())),
                "initial": json.loads(
                    Path("test_fixtures/observed_public_snapshot.json").read_bytes()
                ),
                "now": NOW.timestamp() * 1000,
                "cases": rows,
            }
        ),
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == str(len(rows))


def test_activity_variants_and_forged_content_have_browser_parity():
    import build_static

    base = sample()
    rows = []
    for kind, worker, basis, stage, summary, subject in [
        ("result", "hoffmann", "assigned_role", "recorded", "result_recorded", None),
        (
            "controller_result",
            "hoffmann",
            "controller_responsibility",
            "recorded",
            "status_check_recorded",
            None,
        ),
        ("review", None, "unknown", "accepted", "review_accepted", "hoffmann"),
        (
            "result",
            None,
            "historical_role_unmapped",
            "recorded",
            "historical_result_recorded",
            None,
        ),
    ]:
        e = activity.make_event(
            kind=kind,
            employee_id=worker,
            attribution_basis=basis,
            stage=stage,
            summary_code=summary,
            subject_employee_id=subject,
            observed_at=NOW.isoformat(),
            task_reference="a" * 64,
            result_reference="b" * 64,
            evidence_reference="c" * 64,
            source_revision=None,
            public_reference=None,
        )
        good = copy.deepcopy(base)
        good["activity"] = activity.project_activity([e], now=NOW)
        rows.append(
            {"input": good, "expected": renderer.refresh_public_snapshot(good, now=NOW)}
        )
    many = []
    for i in range(100):
        e = copy.deepcopy(rows[0]["input"]["activity"]["events"][0])
        e.pop("event_id")
        e["task_reference"] = f"{i:064x}"
        many.append(activity.make_event(**e))
    rich = copy.deepcopy(base)
    rich["activity"] = activity.project_activity(many, now=NOW)
    rows.append(
        {"input": rich, "expected": renderer.refresh_public_snapshot(rich, now=NOW)}
    )
    for key, value in [
        ("repository_code", "private-url"),
        ("release_target", "deployed"),
        ("public_reference", "https://private.example/"),
        ("change_code", "unreviewed"),
        ("employee_id", "hoffmann"),
        ("observed_at", NOW.isoformat().replace("+00:00", "Z")),
    ]:
        bad = copy.deepcopy(base)
        event = bad["activity"]["events"][0]
        event[key] = value
        event["event_id"] = activity.digest(
            {k: v for k, v in event.items() if k != "event_id"}
        )
        bad["activity"]["hours"][0]["evidence_reference"] = activity.digest(
            [event["event_id"]]
        )
        try:
            renderer.validate_public_snapshot(bad)
        except ValueError:
            rows.append({"input": bad, "reject": True})
        else:
            raise AssertionError(key)
    result = subprocess.run(
        [
            os.environ.get("NODE", "node"),
            "-e",
            """
const {createStaticReader}=require('./static_feed.js'),a=require('node:assert/strict'),x=JSON.parse(require('node:fs').readFileSync(0,'utf8'));
const r=createStaticReader({schema:x.schema,initial:x.initial,now:()=>x.now});
for(const row of x.rows){if(row.reject)a.throws(()=>r.validate(row.input));else a.deepEqual(r.refresh(row.input),row.expected);}
""",
        ],
        input=json.dumps(
            {
                "schema": json.loads(build_static.encoded(build_static.schema())),
                "initial": base,
                "now": NOW.timestamp() * 1000,
                "rows": rows,
            }
        ),
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr


def test_cached_activity_never_regresses_while_operational_snapshot_is_unchanged():
    from datetime import timedelta

    original = sample()
    older = copy.deepcopy(original)
    older["activity"] = activity.project_activity([], now=NOW - timedelta(hours=1))
    cache = {"snapshot": copy.deepcopy(original)}
    value, status = renderer.load_public_snapshot(
        renderer.STATUS_LATEST_URL,
        cache=cache,
        fetch=lambda _: json.dumps(older).encode(),
        now=NOW,
    )
    assert (
        status == "remote_unavailable_last_verified"
        and value["activity"] == original["activity"]
    )
    assert cache["snapshot"] == original
    import build_static

    result = subprocess.run(
        [
            os.environ.get("NODE", "node"),
            "-e",
            """
const {createStaticReader}=require('./static_feed.js'),a=require('node:assert/strict'),x=JSON.parse(require('node:fs').readFileSync(0,'utf8'));
(async()=>{const r=createStaticReader({schema:x.schema,initial:x.initial,now:()=>x.now,fetch:async()=>new Response(JSON.stringify(x.older))});const v=await r.load();a.deepEqual(v.activity,x.initial.activity);a.equal(v.freshness,'stale');})();
""",
        ],
        input=json.dumps(
            {
                "schema": json.loads(build_static.encoded(build_static.schema())),
                "initial": original,
                "older": older,
                "now": NOW.timestamp() * 1000,
            }
        ),
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr


def test_browser_clock_regression_hides_future_activity_and_fails_closed():
    import build_static

    original = sample()
    original.update(
        snapshot_at=NOW.isoformat(), freshness="current", desk_state="operational"
    )
    result = subprocess.run(
        [
            os.environ.get("NODE", "node"),
            "-e",
            """
const {createStaticReader}=require('./static_feed.js'),a=require('node:assert/strict'),x=JSON.parse(require('node:fs').readFileSync(0,'utf8'));
(async()=>{const r=createStaticReader({schema:x.schema,initial:x.initial,now:()=>x.now,fetch:async()=>{throw Error('offline')}});const v=await r.load();a.equal(v.freshness,'unverified');a.equal(v.desk_state,'status unavailable');a.equal(v.activity,undefined);})();
""",
        ],
        input=json.dumps(
            {
                "schema": json.loads(build_static.encoded(build_static.schema())),
                "initial": original,
                "now": NOW.timestamp() * 1000 - 1000,
            }
        ),
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
