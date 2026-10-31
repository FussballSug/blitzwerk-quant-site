import json
import sys
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

import streamlit_app


@pytest.mark.parametrize("current_slot_available", [True, False])
def test_hosted_entry_reads_fixed_status_feed_without_environment(monkeypatch, current_slot_available):
    class FixedDateTime(datetime):
        @classmethod
        def now(cls, zone=None):
            return cls(2026, 10, 30, 23, 2, tzinfo=UTC)
    now = FixedDateTime.now(UTC)
    observed = now - timedelta(seconds=90)
    snapshot = streamlit_app.build_public_snapshot(
        {"checked_at": observed.isoformat(), "state": "stopped", "health": "attention"},
        now=observed,
    )
    current_url = streamlit_app.current_slot_url(streamlit_app.STATUS_URL_TEMPLATE, now=now)
    requests, rendered = [], []

    def fetch(url, *, timeout):
        requests.append(url)
        assert 0 < timeout <= streamlit_app.FETCH_TIMEOUT_SECONDS
        if url == current_url and not current_slot_available:
            raise OSError("current slot missing")
        assert url in (current_url, streamlit_app.STATUS_LATEST_URL)
        return json.dumps(snapshot).encode()

    fake_streamlit = SimpleNamespace(
        set_page_config=lambda **kwargs: None,
        markdown=lambda *args, **kwargs: None,
        fragment=lambda **kwargs: lambda function: function,
        warning=lambda *args: None,
        iframe=lambda document, **kwargs: rendered.append(document),
        session_state={}, query_params={},
    )
    monkeypatch.delenv("PUBLIC_STATUS_URL", raising=False)
    monkeypatch.delenv("PUBLIC_STATUS_URL_TEMPLATE", raising=False)
    monkeypatch.setitem(sys.modules, "streamlit", fake_streamlit)
    monkeypatch.setattr(streamlit_app, "datetime", FixedDateTime)
    monkeypatch.setattr(streamlit_app, "fetch_public_snapshot", fetch)
    streamlit_app.main()
    assert requests == ([current_url] if current_slot_available else [current_url, streamlit_app.STATUS_LATEST_URL])
    received = json.loads(rendered[0].split("window.BLITZWERK_DATA=", 1)[1].split(";</script>", 1)[0])
    assert received["snapshot_at"] == observed.isoformat()
    assert received["freshness"] == ("current" if current_slot_available else "stale")
    assert received["desk_state"] == ("stopped for review" if current_slot_available else "status delayed")


def test_feed_default_does_not_replace_explicit_settings():
    assert streamlit_app.configured_public_feed({}) == (streamlit_app.STATUS_LATEST_URL, streamlit_app.STATUS_URL_TEMPLATE)
    assert streamlit_app.configured_public_feed({"PUBLIC_STATUS_URL": ""}) == ("", None)
    assert streamlit_app.configured_public_feed({"PUBLIC_STATUS_URL_TEMPLATE": ""}) == (None, "")
    assert streamlit_app.configured_public_feed({"PUBLIC_STATUS_URL": "https://status.example.org/snapshot.json"}) == ("https://status.example.org/snapshot.json", None)


def test_exact_public_schema_and_no_private_terms():
    snapshot = streamlit_app.load_local_snapshot()
    assert set(snapshot) == streamlit_app.PUBLIC_KEYS
    document = streamlit_app.render_document(snapshot)
    assert "BLITZWERK_DATA" in document
    for forbidden in ("account_id", "account number", "secret_key", "buying_power", "order_id"):
        assert forbidden not in document
    for required in ("WHAT WE DO", "WHAT WE AIM TO ACHIEVE", "Sug", "not human staff"):
        assert required in document
    json.dumps(snapshot)


def test_public_copy_is_us_english():
    document = streamlit_app.render_document(streamlit_app.load_local_snapshot())
    for required in (
        "Precision.",
        "Control.",
        "Progress.",
        "OUR MISSION",
        "OPERATIONS CENTER",
        "THREE AI RESEARCH TRADERS",
        "AI EMPLOYEES",
        "OPERATING PRINCIPLES",
        "US AI QUANTITATIVE TRADING",
        "THREE AI RESEARCH TRADERS",
        "software trader roles",
        "screened universe of eligible US stocks",
        "PAPER / SIMULATED",
        "liquidity, spread, price, data quality, volatility, and risk",
        "No trade is proposed when no candidate qualifies",
        "Specialized AI roles use quantitative research",
        "We use AI to turn quantitative market research",
        "human-governed",
    ):
        assert required in document
    for obsolete in ("assigned to F", "assigned to BAC", "assigned to SOFI"):
        assert obsolete not in document
    for german_copy in (
        "Präzision",
        "Kontrolle",
        "Fortschritt",
        "UNSER AUFTRAG",
        "PROZESSLEITSTAND",
        "DREI FORSCHUNGSLINIEN",
        "AI MITARBEITER",
        "BETRIEBSPRINZIPIEN",
        "LETZTER IMPULS",
        "STATUS WIRD GELADEN",
    ):
        assert german_copy not in document


def test_navigation_targets_populated_sections():
    document = streamlit_app.render_document(streamlit_app.load_local_snapshot(), page="home")
    for target in ("mission", "processes", "desk", "team", "principles"):
        assert f'href="#{target}"' in document
        assert f'id="{target}"' in document
    assert 'target="_top"' not in document
    assert "event.preventDefault()" in document
    assert "showPage(link.getAttribute" in document
    assert '[hidden]{display:none!important}' in document
    assert 'id==="home"' in document
    assert document.count('class="section-label"') == 6


def test_each_public_page_selects_its_populated_section():
    snapshot = streamlit_app.load_local_snapshot()
    expected = {
        "mission": "WHAT WE AIM TO ACHIEVE",
        "processes": "From signal to safe experiment.",
        "desk": "THREE AI RESEARCH TRADERS",
        "team": "Sug",
        "principles": "Evidence before action.",
    }
    for page, content in expected.items():
        document = streamlit_app.render_document(snapshot, page=page)
        assert f'data-page="{page}"' in document
        assert content in document


def test_unknown_page_falls_back_to_home():
    document = streamlit_app.render_document(streamlit_app.load_local_snapshot(), page="private")
    assert 'data-page="home"' in document


def test_company_identity_is_quantitative_trading_technology():
    document = streamlit_app.render_document(streamlit_app.load_local_snapshot(), page="mission")
    assert "US AI quantitative trading technology company" in document
    assert "Current systems remain in validation with simulated broker orders" in document
    assert "PAPER RESEARCH PLATFORM" not in document


@pytest.mark.parametrize('fault',[None,'authority','mode','kind'])
def test_finite_canary_view_retains_only_exact_non_authorizing_public_contract(fault):
    row={'run_id':'public-canary-view','kind':'improvement','version':3,'status':'waiting',
        'node':'paper_canary','updated_at':1,'deadline_at':2,'history':[],'artifact_digests':[],
        'mode':'finite_closed_session_canary','execution_authorized':False}
    if fault=='authority':row['execution_authorized']=True
    elif fault=='mode':row['mode']='unverified'
    elif fault=='kind':row['kind']='incident'
    value=streamlit_app.sanitize_operations({'workflows':[row]},now=1)
    if fault:assert value['workflows']==[]
    else:
        assert value['workflows'][0]['mode']=='finite_closed_session_canary'
        assert value['workflows'][0]['execution_authorized'] is False
        snapshot=streamlit_app.load_local_snapshot();snapshot.update(value)
        snapshot["traders"]=streamlit_app._traders(snapshot["employees"])
        assert streamlit_app.validate_snapshot(snapshot)==snapshot
        document=streamlit_app.render_document(snapshot)
        assert 'Controlled PAPER canary' in document
