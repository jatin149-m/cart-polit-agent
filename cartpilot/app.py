import json

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from cartpilot.agent import run_agent  # noqa: E402
from cartpilot import payments  # noqa: E402

st.set_page_config(page_title="CartPilot", page_icon="🛒", layout="centered")

st.title("🛒 CartPilot")
st.caption("An AI checkout agent for Razorpay merchants — Track: AI Growth & Agentic Commerce")

mode = "🟢 LIVE — Razorpay test-mode" if payments.is_live_mode() else "🟡 MOCK payment mode"
st.info(f"Payment mode: **{mode}**")

buyer_intent = st.text_input(
    "What does the buyer want?",
    placeholder="e.g. get me wireless earbuds under 2000 rupees, apply any discount you can",
)

if st.button("Run agent", type="primary") and buyer_intent:
    with st.spinner("Agent is thinking..."):
        result = run_agent(buyer_intent)

    st.subheader("Agent trace")
    for i, step in enumerate(result["trace"], start=1):
        with st.expander(f"Step {i}: {step['tool']}({', '.join(f'{k}={v}' for k, v in step['args'].items())})"):
            st.json(step["result"])

    st.subheader("Final answer")
    st.write(result["answer"])

    st.subheader("Audit trail (session)")
    from cartpilot import audit

    events = audit.read_session(result["session_id"])
    st.code(json.dumps(events, indent=2), language="json")

st.divider()
st.caption(
    "Guardrails active: hard spend cap, action whitelist, full audit log. "
    "See guardrails.py / audit.py in the repo."
)
