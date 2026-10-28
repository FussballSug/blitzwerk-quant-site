import json
import streamlit_app


def test_exact_public_schema_and_no_private_terms():
    snapshot = streamlit_app.public_snapshot()
    assert set(snapshot) == streamlit_app.PUBLIC_KEYS
    document = streamlit_app.render_document(snapshot)
    assert "BLITZWERK_DATA" in document
    for forbidden in ("account_id", "account number", "secret_key", "buying_power", "order_id"):
        assert forbidden not in document
    for required in ("WHAT WE DO", "WHAT WE AIM TO ACHIEVE", "Alexander von Stein", "not human staff"):
        assert required in document
    json.dumps(snapshot)


def test_public_copy_is_us_english():
    document = streamlit_app.render_document(streamlit_app.public_snapshot())
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
        "Implemented paper workflow",
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
    document = streamlit_app.render_document(streamlit_app.public_snapshot(), page="home")
    for target in ("mission", "processes", "desk", "team", "principles"):
        assert f'href="#{target}"' in document
        assert f'id="{target}"' in document
    assert 'target="_top"' not in document
    assert "event.preventDefault()" in document
    assert "showPage(link.getAttribute" in document
    assert '[hidden]{display:none!important}' in document
    assert 'id==="home"' in document
    assert document.count('class="section-label"') == 5


def test_each_public_page_selects_its_populated_section():
    snapshot = streamlit_app.public_snapshot()
    expected = {
        "mission": "WHAT WE AIM TO ACHIEVE",
        "processes": "From signal to safe experiment.",
        "desk": "THREE AI RESEARCH TRADERS",
        "team": "Alexander von Stein",
        "principles": "Evidence before action.",
    }
    for page, content in expected.items():
        document = streamlit_app.render_document(snapshot, page=page)
        assert f'data-page="{page}"' in document
        assert content in document


def test_unknown_page_falls_back_to_home():
    document = streamlit_app.render_document(streamlit_app.public_snapshot(), page="private")
    assert 'data-page="home"' in document


def test_company_identity_is_quantitative_trading_technology():
    document = streamlit_app.render_document(streamlit_app.public_snapshot(), page="mission")
    assert "US AI quantitative trading technology company" in document
    assert "Current systems remain in validation with simulated broker orders" in document
    assert "PAPER RESEARCH PLATFORM" not in document


def test_dated_paper_milestone_is_not_live_telemetry():
    document = streamlit_app.render_document(streamlit_app.public_snapshot())
    for required in ('DEPLOYMENT MILESTONE', 'October 28, 2026', 'Three-strategy paper desk deployed',
                     'This dated milestone is not a live service-status feed', 'Daily readiness checks still gate each session',
                     'PAPER WORKFLOW IMPLEMENTED'):
        assert required in document
    for private in ('Michael Williams', 'michaelwilliams', '/Users/', 'service_pid', 'authority_reference'):
        assert private not in document
    snapshot = streamlit_app.public_snapshot()
    assert snapshot['freshness'] == 'unverified'
    assert snapshot['desk_state'] == 'status unavailable'


def test_hero_deployment_animation_is_illustrative():
    document = streamlit_app.render_document(streamlit_app.public_snapshot())
    hero = document.split('<section class="hero">')[1].split('</section>')[0]
    assert 'class="deployment-milestone"' in hero
    assert 'class="desk-animation"' in hero
    assert 'PAPER DESK' in hero and 'DEPLOYED' in hero
    assert 'Illustrative workflow, not live trading activity' in hero
    assert 'prefers-reduced-motion' in document
