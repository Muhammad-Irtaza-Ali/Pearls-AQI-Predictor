from __future__ import annotations

from typing import Any

import streamlit as st


def render_page_header(title: str, subtitle: str, *, eyebrow: str | None = None) -> None:
    if eyebrow:
        st.caption(eyebrow)
    st.title(title)
    st.caption(subtitle)


def render_kpis(items: list[tuple[str, str, str | None]]) -> None:
    columns = st.columns(len(items), vertical_alignment="center")
    for column, (label, value, help_text) in zip(columns, items):
        with column:
            st.metric(label, value, help=help_text, border=True)


def render_section_title(title: str, subtitle: str | None = None) -> None:
    st.subheader(title)
    if subtitle:
        st.caption(subtitle)

