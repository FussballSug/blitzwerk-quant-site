"""Public, account-free Streamlit information site for Blitzwerk Kapital."""
import json
from pathlib import Path

ASSETS = Path(__file__).parent / "assets"
PUBLIC_KEYS = {"schema_version", "snapshot_at", "freshness", "mode", "desk_state", "traders", "stages"}


def public_snapshot():
    data = json.loads((ASSETS / "snapshot.json").read_text())
    if set(data) != PUBLIC_KEYS:
        raise ValueError("Unexpected public snapshot schema")
    return data


PAGES = {"home", "mission", "processes", "desk", "team", "principles"}


def render_document(snapshot, page="home"):
    if set(snapshot) != PUBLIC_KEYS:
        raise ValueError("Unexpected public snapshot schema")
    page = page if page in PAGES else "home"
    html = (ASSETS / "index.html").read_text()
    css = (ASSETS / "styles.css").read_text()
    script = (ASSETS / "app.js").read_text()
    payload = json.dumps(snapshot, sort_keys=True).replace("</", "<\\/")
    html = html.replace('data-page="__PAGE__"', f'data-page="{page}"')
    html = html.replace('<link rel="stylesheet" href="styles.css">', f"<style>{css}</style>")
    return html.replace('<script src="app.js"></script>', f"<script>window.BLITZWERK_DATA={payload};</script><script>{script}</script>")


def main():
    import streamlit as st
    import streamlit.components.v1 as components

    st.set_page_config(page_title="Blitzwerk Kapital", page_icon="⚡", layout="wide", initial_sidebar_state="collapsed")
    st.markdown("<style>#MainMenu,header,footer{visibility:hidden}.block-container{padding:0;max-width:none}</style>", unsafe_allow_html=True)
    requested_page = st.query_params.get("page", "home")
    components.html(render_document(public_snapshot(), page=requested_page), height=4300, scrolling=False)


if __name__ == "__main__":
    main()
