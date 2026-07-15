THEMES = {
    "mechanical": {
        "primary": "#b91c1c",
        "primary_dark": "#7f1d1d",
        "primary_light": "#fee2e2",
        "accent": "#ef4444",
        "label": "Mechanical Engineering",
        "emoji": "⚙️",
    },
    "cse": {
        "primary": "#15803d",
        "primary_dark": "#14532d",
        "primary_light": "#dcfce7",
        "accent": "#22c55e",
        "label": "Computer Science & Engineering",
        "emoji": "\U0001f4bb",
    },
}

TEXT_DARK = "#1f2937"
TEXT_MUTED = "#374151"


def inject_theme(st, department):
    t = THEMES.get(department, THEMES["cse"])
    st.markdown(
        f"""
        <style>
        :root {{
            --primary: {t['primary']};
            --primary-dark: {t['primary_dark']};
            --primary-light: {t['primary_light']};
            --accent: {t['accent']};
            color-scheme: light;
        }}

        /* Force a light, high-contrast surface regardless of the browser/OS theme */
        .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {{
            background: linear-gradient(180deg, {t['primary_light']} 0%, #ffffff 260px) !important;
        }}
        [data-testid="stMain"], .block-container {{
            color: {TEXT_DARK} !important;
        }}

        /* Generic text: headings, paragraphs, labels, captions, list items */
        h1, h2, h3, h4, h5, h6,
        p, span, li, label,
        .stMarkdown, .stMarkdown p, .stMarkdown li,
        [data-testid="stCaptionContainer"],
        [data-testid="stWidgetLabel"] label,
        [data-testid="stMetricLabel"] {{
            color: {TEXT_DARK} !important;
        }}
        h1, h2, h3 {{
            color: {t['primary_dark']} !important;
        }}
        [data-testid="stCaptionContainer"] {{
            color: {TEXT_MUTED} !important;
        }}

        /* Text inputs */
        .stTextInput input {{
            color: {TEXT_DARK} !important;
            background: #ffffff !important;
            border: 1px solid #cbd5e1 !important;
        }}
        .stTextInput input::placeholder {{
            color: #9ca3af !important;
        }}

        /* Radio buttons (subject picker + quiz options) */
        .stRadio label p, .stRadio div[role="radiogroup"] label span {{
            color: {TEXT_DARK} !important;
        }}

        .stButton>button {{
            background: {t['primary']};
            color: white !important;
            border: none;
            border-radius: 8px;
            padding: 0.55em 1.4em;
            font-weight: 600;
            transition: background 0.15s ease-in-out;
        }}
        .stButton>button:hover {{
            background: {t['primary_dark']};
            color: white !important;
        }}
        .stButton>button p {{
            color: white !important;
        }}

        .quiz-banner {{
            background: {t['primary']};
            color: white !important;
            padding: 14px 20px;
            border-radius: 10px;
            font-size: 1.15em;
            font-weight: 700;
            margin-bottom: 14px;
        }}
        .question-card {{
            border: 1px solid {t['primary_light']};
            border-left: 6px solid {t['primary']};
            border-radius: 10px;
            padding: 14px 18px;
            margin-bottom: 12px;
            background: #ffffff;
            color: {TEXT_DARK} !important;
        }}
        .question-card p, .question-card span, .question-card div {{
            color: {TEXT_DARK} !important;
        }}
        .correct-pill {{
            background: #dcfce7; color: #166534 !important; padding: 3px 10px;
            border-radius: 999px; font-weight: 600; font-size: 0.85em;
        }}
        .wrong-pill {{
            background: #fee2e2; color: #991b1b !important; padding: 3px 10px;
            border-radius: 999px; font-weight: 600; font-size: 0.85em;
        }}
        .flag-banner {{
            background: #fef3c7; color: #92400e !important; border: 1px solid #f59e0b;
            padding: 12px 16px; border-radius: 8px; font-weight: 600;
        }}

        /* st.warning / st.info / st.error boxes */
        [data-testid="stAlertContentWarning"], [data-testid="stAlertContentWarning"] p {{
            color: #92400e !important;
        }}
        [data-testid="stAlertContentInfo"], [data-testid="stAlertContentInfo"] p {{
            color: #1e3a8a !important;
        }}
        [data-testid="stAlertContentError"], [data-testid="stAlertContentError"] p {{
            color: #991b1b !important;
        }}

        /* Progress bar caption + metrics */
        [data-testid="stMetricValue"] {{
            color: {t['primary_dark']} !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
    return t
