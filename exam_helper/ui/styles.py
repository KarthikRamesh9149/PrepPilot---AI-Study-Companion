from __future__ import annotations

import streamlit as st


def apply_global_styles() -> None:
    st.markdown(
        """
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=Space+Grotesk:wght@500;600;700&display=swap');

:root {
  --bg-a: #f7fafc;
  --bg-b: #edf4ff;
  --bg-c: #e8fbf7;
  --surface: #ffffff;
  --surface-soft: #f6f9ff;
  --text-strong: #0f1b36;
  --text-muted: #50627e;
  --brand: #005fe5;
  --brand-2: #0ac5a9;
  --brand-soft: #deecff;
  --ok: #149b6f;
  --warn: #af6a00;
  --danger: #c23a3a;
  --border: #d9e4f2;
  --shadow-soft: 0 10px 28px rgba(15, 36, 73, 0.08);
  --shadow-focus: 0 0 0 3px rgba(0, 95, 229, 0.15);
  --space-1: 0.25rem;
  --space-2: 0.5rem;
  --space-3: 0.75rem;
  --space-4: 1rem;
  --space-5: 1.25rem;
  --space-6: 1.5rem;
  --space-7: 2rem;
  --space-8: 2.5rem;
  --radius-s: 10px;
  --radius-m: 14px;
  --radius-l: 18px;
}

.stApp {
  background:
    radial-gradient(1200px 560px at 5% -15%, #dfeaff 0%, transparent 56%),
    radial-gradient(920px 420px at 100% -5%, #dffcf4 0%, transparent 48%),
    linear-gradient(170deg, var(--bg-a) 0%, var(--bg-b) 62%, var(--bg-c) 100%);
}

.block-container {
  max-width: 1220px;
  padding-top: var(--space-6);
  padding-bottom: var(--space-8);
}

html, body, [class*="css"], [data-testid="stAppViewContainer"] {
  font-family: "Manrope", "Segoe UI", sans-serif;
  font-size: 17px;
  line-height: 1.6;
}

h1, h2, h3 {
  color: var(--text-strong);
  letter-spacing: -0.02em;
  font-family: "Space Grotesk", "Manrope", "Segoe UI", sans-serif;
}

p, li, .stMarkdown, .stCaption {
  color: var(--text-muted);
}

.stMarkdown p,
.stMarkdown li,
.stText,
.stCaption {
  font-size: 1rem;
}

label, [data-testid="stWidgetLabel"] {
  color: #1d2f4f !important;
  font-weight: 600;
}

.eh-hero,
.eh-card,
.eh-status-strip,
.eh-section-intro {
  animation: none;
}

.eh-hero {
  background: linear-gradient(112deg, #0b1938 0%, #0e408d 55%, #097cae 100%);
  border-radius: 22px;
  padding: var(--space-7);
  margin-bottom: var(--space-5);
  box-shadow: 0 10px 24px rgba(12, 35, 82, 0.22);
  position: relative;
  overflow: hidden;
}

.eh-hero::after {
  content: "";
  position: absolute;
  width: 250px;
  height: 250px;
  right: -86px;
  top: -96px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.28), rgba(255, 255, 255, 0));
}

.eh-hero::before {
  content: "";
  position: absolute;
  width: 330px;
  height: 8px;
  left: -20px;
  bottom: 0;
  background: linear-gradient(90deg, rgba(255, 255, 255, 0.66), rgba(255, 255, 255, 0));
}

.eh-hero-head {
  display: flex;
  align-items: flex-start;
  gap: var(--space-5);
}

.eh-hero-icon {
  width: 44px;
  height: 44px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.28);
  display: grid;
  place-items: center;
  flex-shrink: 0;
}

.eh-hero-icon svg {
  width: 24px;
  height: 24px;
  stroke: #e6f3ff;
}

.eh-hero h2 {
  margin: 0;
  color: #ffffff;
  font-size: clamp(1.45rem, 2.2vw, 1.85rem);
}

.eh-hero p {
  margin: var(--space-2) 0 0;
  color: #d7e7ff;
  font-size: 1rem;
  max-width: 760px;
}

.eh-status-strip {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-3);
  margin-bottom: var(--space-5);
}

.eh-status-card {
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.95) 0%, rgba(244, 249, 255, 0.9) 100%);
  border: 1px solid #d7e3f3;
  border-radius: var(--radius-l);
  padding: var(--space-4) var(--space-5);
  box-shadow: var(--shadow-soft);
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.eh-status-label {
  color: #5b6f8f;
  font-size: 0.82rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.eh-status-value {
  color: #132549;
  font-size: 1.08rem;
  font-weight: 800;
  letter-spacing: -0.01em;
}

.eh-section-intro {
  margin-bottom: var(--space-3);
}

.eh-section-intro h3 {
  margin: 0;
  font-size: 1.2rem;
}

.eh-section-intro p {
  margin: var(--space-1) 0 0;
  font-size: 1.03rem;
  color: #33496d;
}

.eh-card {
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(247, 250, 255, 0.96) 100%);
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: var(--space-5) var(--space-6);
  box-shadow: 0 6px 16px rgba(15, 36, 73, 0.07);
  margin-bottom: var(--space-4);
  position: relative;
  overflow: hidden;
}

.eh-card::before {
  content: "";
  position: absolute;
  left: 0;
  top: 0;
  width: 100%;
  height: 4px;
  background: linear-gradient(90deg, var(--brand) 0%, var(--brand-2) 100%);
  opacity: 0.9;
}

.eh-pill-wrap {
  margin-top: var(--space-2);
}

.eh-pill {
  display: inline-block;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.01em;
  padding: 5px 12px;
  border-radius: 999px;
  margin-right: var(--space-2);
  margin-bottom: var(--space-2);
  border: 1px solid var(--border);
  background: var(--surface-soft);
  color: var(--text-muted);
}

.eh-pill.brand {
  background: var(--brand-soft);
  border-color: #c2d8ff;
  color: #1a4da8;
}

.eh-pill.ok {
  background: #e7fff5;
  border-color: #b3f1d9;
  color: #0f6d4e;
}

.eh-pill.warn {
  background: #fff5e6;
  border-color: #f0d2a2;
  color: #8b5904;
}

.eh-evidence-weak {
  margin-top: var(--space-2);
  background: #fff9eb;
  border: 1px solid #f1d7a8;
  border-radius: var(--radius-s);
  padding: var(--space-3) var(--space-4);
  color: #885200;
  font-weight: 600;
}

.eh-topic-row {
  background: #ffffff;
  border: 1px solid var(--border);
  border-radius: var(--radius-m);
  padding: var(--space-4);
  margin-bottom: var(--space-3);
  color: #1e3357;
  font-size: 1rem;
  line-height: 1.65;
}

.eh-topic-title {
  color: var(--text-strong);
  display: block;
  margin-bottom: var(--space-1);
}

.eh-empty {
  border: 1px dashed #c2d3eb;
  background: rgba(248, 252, 255, 0.86);
  border-radius: var(--radius-m);
  padding: var(--space-4) var(--space-5);
  margin: var(--space-3) 0;
}

.eh-empty strong {
  color: #1a2d53;
  font-size: 0.98rem;
}

.eh-empty p {
  margin: var(--space-1) 0 0;
  font-size: 0.92rem;
}

section[data-testid="stSidebar"] {
  background: rgba(249, 252, 255, 0.95);
  border-right: 1px solid var(--border);
}

section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
  padding-top: var(--space-4);
}

section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {
  font-family: "Space Grotesk", "Manrope", sans-serif;
  letter-spacing: -0.01em;
}

.stTabs [data-baseweb="tab-list"] {
  gap: var(--space-2);
  margin-bottom: var(--space-4);
}

.stTabs [data-baseweb="tab"] {
  background: rgba(255, 255, 255, 0.78);
  border: 1px solid #d6e3f4;
  border-radius: 12px;
  padding: var(--space-2) var(--space-5);
  color: #223a5e;
  font-weight: 700;
  font-size: 1rem;
}

.stTabs [aria-selected="true"] {
  background: linear-gradient(90deg, #d8e8ff 0%, #d8f9f2 100%);
  color: #0f468f;
  border-color: #b9d6ff;
}

.stSelectbox > div > div,
.stDateInput > div > div,
.stTextInput > div > div,
.stTextArea > div > div {
  border-radius: 12px !important;
  border-color: #d3e0f3 !important;
}

.stRadio > div[role="radiogroup"] > label {
  background: #ffffff;
  border: 1px solid #d8e3f4;
  border-radius: 10px;
  margin-bottom: 0.45rem;
  padding: 0.45rem 0.6rem;
  color: #1d2f4f !important;
}

.stButton button,
.stDownloadButton button {
  border-radius: 12px !important;
  border: 1px solid #1f66e2 !important;
  background: linear-gradient(180deg, #1f6af0 0%, #0f56d5 100%) !important;
  color: #ffffff !important;
  font-weight: 700 !important;
  padding-top: var(--space-2) !important;
  padding-bottom: var(--space-2) !important;
  box-shadow: 0 10px 18px rgba(15, 73, 179, 0.22) !important;
  transition: transform 120ms ease, box-shadow 120ms ease;
  font-size: 1.04rem !important;
  line-height: 1.25 !important;
  min-height: 46px !important;
}

.stButton button span,
.stButton button p,
.stDownloadButton button span,
.stDownloadButton button p {
  color: #ffffff !important;
  opacity: 1 !important;
}

.stButton button:hover,
.stDownloadButton button:hover {
  transform: none;
  box-shadow: 0 10px 18px rgba(15, 73, 179, 0.22) !important;
}

.stButton button:focus-visible,
.stDownloadButton button:focus-visible,
[data-baseweb="select"] input:focus,
[data-baseweb="input"] input:focus {
  box-shadow: var(--shadow-focus) !important;
  outline: none !important;
}

.stSlider [data-baseweb="slider"] [role="slider"] {
  box-shadow: 0 0 0 3px rgba(0, 95, 229, 0.14);
}

.stCaption {
  font-size: 0.96rem !important;
  color: #3f587f !important;
}

@media (max-width: 1000px) {
  .block-container {
    padding-top: var(--space-4);
    padding-left: var(--space-3);
    padding-right: var(--space-3);
  }

  .eh-status-strip {
    grid-template-columns: 1fr;
  }

  .eh-hero {
    padding: var(--space-5);
  }

  .eh-hero-head {
    gap: var(--space-3);
  }

  .eh-card {
    padding: var(--space-4);
  }
}
</style>
""",
        unsafe_allow_html=True,
    )
