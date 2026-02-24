from __future__ import annotations

from html import escape

import streamlit as st


def hero(title: str, subtitle: str) -> None:
    safe_title = escape(title)
    safe_subtitle = escape(subtitle)
    st.markdown(
        f"""
<div class="eh-hero">
  <div class="eh-hero-head">
    <div class="eh-hero-icon" aria-hidden="true">
      <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8">
        <path d="M12 3l8 4.5v9L12 21l-8-4.5v-9L12 3z"></path>
        <path d="M8 11.5l2.5 2.5L16 9"></path>
      </svg>
    </div>
    <div>
      <h2>{safe_title}</h2>
      <p>{safe_subtitle}</p>
    </div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def status_strip(module_ready: bool, days_remaining: int, hours_per_day: int) -> None:
    module_text = "Module Ready" if module_ready else "Module Not Ready"
    countdown = f"{max(0, days_remaining)} days"
    target = f"{hours_per_day} hrs today"
    st.markdown(
        f"""
<div class="eh-status-strip">
  <div class="eh-status-card">
    <span class="eh-status-label">Status</span>
    <span class="eh-status-value">{escape(module_text)}</span>
  </div>
  <div class="eh-status-card">
    <span class="eh-status-label">Exam Countdown</span>
    <span class="eh-status-value">{escape(countdown)}</span>
  </div>
  <div class="eh-status-card">
    <span class="eh-status-label">Study Target</span>
    <span class="eh-status-value">{escape(target)}</span>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def section_intro(title: str, subtitle: str) -> None:
    st.markdown(
        f"""
<div class="eh-section-intro">
  <h3>{escape(title)}</h3>
  <p>{escape(subtitle)}</p>
</div>
""",
        unsafe_allow_html=True,
    )


def empty_state(title: str, message: str) -> None:
    st.markdown(
        f"""
<div class="eh-empty">
  <strong>{escape(title)}</strong>
  <p>{escape(message)}</p>
</div>
""",
        unsafe_allow_html=True,
    )


def card_start() -> None:
    st.markdown('<div class="eh-card">', unsafe_allow_html=True)


def card_end() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


def coverage_pills(items: list[str], tone: str = "brand") -> None:
    if not items:
        return
    safe_tone = escape(tone).strip()
    html = "".join(
        [f'<span class="eh-pill {safe_tone}">{escape(item)}</span>' for item in items if item]
    )
    st.markdown(f"<div class='eh-pill-wrap'>{html}</div>", unsafe_allow_html=True)


def evidence_warning(message: str) -> None:
    st.markdown(f'<div class="eh-evidence-weak">{escape(message)}</div>', unsafe_allow_html=True)


def topic_row(title: str, detail: str) -> None:
    safe_title = escape(title)
    safe_detail = escape(detail).replace("\n", "<br>")
    st.markdown(
        f"<div class='eh-topic-row'><span class='eh-topic-title'><strong>{safe_title}</strong></span>{safe_detail}</div>",
        unsafe_allow_html=True,
    )


def diagnostics_line(label: str, value: str) -> None:
    st.caption(f"{label}: {value}")
