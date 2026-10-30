"""Public rendering-only cadence clarification; no service or network calls."""
import json
from datetime import UTC, datetime, timedelta

import pytest

import streamlit_app as renderer


@pytest.mark.parametrize("page", ["home", "team", "desk", "processes"])
@pytest.mark.parametrize("age,expected", [(600, "current"), (601, "stale"), (None, "unverified")])
def test_notice_preserves_observation_and_operational_freshness(page, age, expected):
    observed = datetime(2026, 10, 30, 23, tzinfo=UTC)
    receipt = None if age is None else {"checked_at": observed.isoformat(), "state": "stopped", "health": "attention"}
    original = renderer.build_public_snapshot(receipt, now=observed)
    snapshot = renderer.refresh_public_snapshot(original, now=observed + timedelta(seconds=age or 0))
    document = renderer.render_document(snapshot, page=page)
    assert 'id="reporting-cadence"' in document
    assert "Public reports are scheduled hourly." in document
    assert "Operational status can become stale between reports." in document
    assert "REPORT AS OF" in document
    assert document.index('id="reporting-cadence"') < document.index('id="offline-warning"')
    received = json.loads(document.split("window.BLITZWERK_DATA=", 1)[1].split(";</script>", 1)[0])
    assert received == snapshot
    assert received["snapshot_at"] == original["snapshot_at"]
    assert received["freshness"] == expected
    if age == 601:
        assert received["desk_state"] == "status delayed"
