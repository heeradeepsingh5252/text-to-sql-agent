import os

import httpx
import pandas as pd
import streamlit as st

API_BASE_URL = os.getenv(
    "API_BASE_URL",
    "http://localhost:8000"
).rstrip("/")

st.set_page_config(
    page_title="Pharma Intelligence",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -------------------- DESIGN SYSTEM --------------------

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap');

:root {
    --bg: #080D19;
    --panel: #111B2D;
    --panel2: #152238;
    --border: #263750;
    --text: #F1F5F9;
    --muted: #91A2B9;
    --teal: #55E6C1;
    --blue: #6EA8FE;
}

.stApp {
    background: var(--bg);
    color: var(--text);
    font-family: 'DM Sans', sans-serif;
}

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

.block-container {
    max-width: 1450px;
    padding-top: 2.2rem;
    padding-bottom: 4rem;
}

h1, h2, h3 {
    font-family: 'Space Grotesk', sans-serif !important;
    color: var(--text);
}

[data-testid="stSidebar"] {
    background: #0D1626;
    border-right: 1px solid var(--border);
}

[data-testid="stSidebar"] > div {
    padding-top: 2rem;
}

.brand {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.2rem;
    font-weight: 700;
    letter-spacing: -0.5px;
    color: white;
}

.brand span {
    color: var(--teal);
}

.sidebar-caption {
    color: var(--muted);
    font-size: 0.82rem;
    line-height: 1.5;
}

.hero {
    position: relative;
    overflow: hidden;
    padding: 34px 36px;
    border-radius: 22px;
    border: 1px solid #263D5B;
    background:
        radial-gradient(circle at 85% 20%, #164B58 0%, transparent 35%),
        linear-gradient(120deg, #14294A, #101A2C 75%);
    margin-bottom: 28px;
}

.eyebrow {
    color: var(--teal);
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 2px;
    text-transform: uppercase;
}

.hero-title {
    font-family: 'Space Grotesk', sans-serif;
    color: #FFFFFF;
    font-size: clamp(2rem, 4vw, 3.1rem);
    font-weight: 700;
    letter-spacing: -1.8px;
    line-height: 1.12;
    margin: 13px 0;
}

.hero-description {
    color: #B8C8DB;
    max-width: 680px;
    font-size: 1rem;
    line-height: 1.7;
}

.section-heading {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.35rem;
    font-weight: 600;
    color: #F1F5F9;
    margin: 12px 0 18px;
}

.kpi {
    background: linear-gradient(145deg, #15243A, #101A2A);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 19px 20px;
    min-height: 112px;
}

.kpi-label {
    color: var(--muted);
    font-size: 0.78rem;
    font-weight: 600;
    margin-bottom: 10px;
}

.kpi-value {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.65rem;
    font-weight: 700;
    color: #FFFFFF;
}

.kpi-accent {
    color: var(--teal);
}

.status-pill {
    display: inline-block;
    color: var(--teal);
    background: #123B3A;
    border: 1px solid #24645D;
    border-radius: 30px;
    padding: 6px 12px;
    font-size: 0.73rem;
    font-weight: 700;
    letter-spacing: 0.5px;
}

.panel {
    background: #111B2D;
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 22px;
    margin: 14px 0;
}

.answer-panel {
    background: linear-gradient(120deg, #10332F, #112A30);
    border: 1px solid #24645D;
    border-radius: 14px;
    padding: 20px 22px;
    color: #C9F8E9;
    line-height: 1.7;
}

.answer-label {
    color: var(--teal);
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 1.5px;
    margin-bottom: 8px;
}

div.stButton > button {
    border-radius: 10px;
    border: 1px solid #30445F;
    background: #142238;
    color: #DCE7F5;
    font-weight: 500;
    transition: all 0.2s ease;
}

div.stButton > button:hover {
    border-color: var(--teal);
    color: var(--teal);
    background: #193044;
}

[data-testid="stChatInput"] {
    border: 1px solid #35516C;
    border-radius: 14px;
    background: #111B2D;
}

[data-testid="stChatInput"] textarea {
    color: white !important;
}

[data-testid="stDataFrame"] {
    border: 1px solid var(--border);
    border-radius: 12px;
}

[data-testid="stExpander"] {
    border: 1px solid var(--border);
    border-radius: 12px;
    background: #111B2D;
}

[data-testid="stMetric"] {
    background: #152238;
    border: 1px solid var(--border);
    padding: 14px;
    border-radius: 12px;
}

hr {
    border-color: var(--border);
}

footer {
    visibility: hidden;
}
</style>
""", unsafe_allow_html=True)


# -------------------- API FUNCTIONS --------------------

def check_api():
    try:
        response = httpx.get(
            f"{API_BASE_URL}/health",
            timeout=5,
        )
        response.raise_for_status()
        return True, response.json()
    except httpx.HTTPError as exc:
        return False, {"error": str(exc)}


def ask_agent(question):
    response = httpx.post(
        f"{API_BASE_URL}/ask",
        json={"question": question},
        timeout=120,
    )
    response.raise_for_status()
    return response.json()


# -------------------- SESSION STATE --------------------

if "messages" not in st.session_state:
    st.session_state.messages = []

if "pending_question" not in st.session_state:
    st.session_state.pending_question = None

api_online, health = check_api()


# -------------------- SIDEBAR --------------------

with st.sidebar:
    st.markdown(
        '<div class="brand">💊 PHARMA <span>INTELLIGENCE</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="sidebar-caption">AI-powered business intelligence workspace</p>',
        unsafe_allow_html=True,
    )

    st.divider()

    st.markdown("### System status")

    if api_online:
        st.markdown(
            '<span class="status-pill">● SYSTEM ONLINE</span>',
            unsafe_allow_html=True,
        )
        st.caption(f"LLM provider: {health.get('provider', 'Unknown')}")
        db_status = (
            "Available" if health.get("database_exists") else "Unavailable"
        )
        st.caption(f"Database: {db_status}")
    else:
        st.error("Backend disconnected")
        st.caption(health.get("error", "API unavailable"))

    st.divider()

    st.markdown("### Suggested queries")

    examples = [
        "Which region generated the highest total revenue?",
        "Which products have the highest total sales?",
        "List inventory records flagged for reorder in Hyderabad.",
    ]

    for index, example in enumerate(examples, start=1):
        if st.button(
            f"0{index}  ·  {example}",
            key=f"example_{index}",
            use_container_width=True,
        ):
            st.session_state.pending_question = example
            st.rerun()

    st.divider()

    if st.button("＋  New conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.pending_question = None
        st.rerun()

    st.markdown(
        '<p class="sidebar-caption">Pharma Intelligence · Text-to-SQL Agent</p>',
        unsafe_allow_html=True,
    )


# -------------------- MAIN HEADER --------------------

st.markdown("""
<div class="hero">
    <div class="eyebrow">INTELLIGENCE · AUTOMATION · INSIGHTS</div>
    <div class="hero-title">Your data.<br>One question away.</div>
    <div class="hero-description">
        Explore pharmaceutical sales and inventory using natural language.
        Generate SQL, execute queries and turn business data into clear answers.
    </div>
</div>
""", unsafe_allow_html=True)


# -------------------- TOP METRICS --------------------

total_queries = len([
    message for message in st.session_state.messages
    if message["role"] == "user"
])

metric1, metric2, metric3 = st.columns(3)

with metric1:
    st.markdown(f"""
    <div class="kpi">
        <div class="kpi-label">WORKSPACE STATUS</div>
        <div class="kpi-value kpi-accent">
            {"Online" if api_online else "Offline"}
        </div>
    </div>
    """, unsafe_allow_html=True)

with metric2:
    st.markdown(f"""
    <div class="kpi">
        <div class="kpi-label">QUESTIONS ASKED</div>
        <div class="kpi-value">{total_queries}</div>
    </div>
    """, unsafe_allow_html=True)

with metric3:
    st.markdown(f"""
    <div class="kpi">
        <div class="kpi-label">AI PROVIDER</div>
        <div class="kpi-value">{"Groq" if api_online else "Unavailable"}</div>
    </div>
    """, unsafe_allow_html=True)


# -------------------- QUERY WORKSPACE --------------------

st.markdown(
    '<div class="section-heading">AI Query Workspace</div>',
    unsafe_allow_html=True,
)

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message["role"] == "user":
            st.write(message["content"])
        else:
            result = message["content"]

            st.markdown(
                '<div class="answer-label">AI GENERATED ANSWER</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<div class="answer-panel">{result.get("answer", "No answer returned.")}</div>',
                unsafe_allow_html=True,
            )

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Rows returned", result.get("row_count", 0))
            with col2:
                st.metric("Retries", result.get("retries", 0))
            with col3:
                st.metric("Truncated", str(result.get("truncated", False)))

            with st.expander("View generated SQL"):
                st.code(result.get("sql", ""), language="sql")

            rows = result.get("rows", [])
            if rows:
                st.markdown("#### Query results")
                st.dataframe(
                    pd.DataFrame(rows),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("No records returned.")


question = st.chat_input(
    "Ask about revenue, products, inventory or business performance..."
)

if st.session_state.pending_question:
    question = st.session_state.pending_question
    st.session_state.pending_question = None

if question:
    st.session_state.messages.append({
        "role": "user",
        "content": question,
    })

    with st.chat_message("user"):
        st.write(question)

    with st.chat_message("assistant"):
        if not api_online:
            st.error("Backend is offline. Start FastAPI on port 8000.")
        else:
            with st.spinner("Understanding your question and generating SQL..."):
                try:
                    result = ask_agent(question)

                    st.markdown(
                        '<div class="answer-label">AI GENERATED ANSWER</div>',
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f'<div class="answer-panel">{result.get("answer", "No answer returned.")}</div>',
                        unsafe_allow_html=True,
                    )

                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.metric("Rows returned", result.get("row_count", 0))
                    with col2:
                        st.metric("Retries", result.get("retries", 0))
                    with col3:
                        st.metric(
                            "Truncated",
                            str(result.get("truncated", False)),
                        )

                    with st.expander("View generated SQL", expanded=True):
                        st.code(result.get("sql", ""), language="sql")

                    rows = result.get("rows", [])
                    if rows:
                        st.markdown("#### Query results")
                        st.dataframe(
                            pd.DataFrame(rows),
                            use_container_width=True,
                            hide_index=True,
                        )
                    else:
                        st.info("No records returned.")

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": result,
                    })

                except httpx.HTTPStatusError as exc:
                    st.error(
                        f"API error {exc.response.status_code}: "
                        f"{exc.response.text}"
                    )
                except httpx.HTTPError as exc:
                    st.error(f"Could not connect to the API: {exc}")
                except (ValueError, KeyError, TypeError) as exc:
                    st.error(f"Unexpected API response: {exc}")


st.markdown(
    '<p style="text-align:center;color:#64748B;font-size:0.75rem;margin-top:45px;">'
    'POWERED BY FASTAPI · GROQ · SQLITE · STREAMLIT</p>',
    unsafe_allow_html=True,
)
