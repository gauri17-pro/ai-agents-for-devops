"""
AWS EC2 Strands Agent — Streamlit UI
Requires: streamlit>=1.43.0, boto3, strands-agents
Python 3.14+ compatible — no deprecated stdlib usage, no type annotation hacks.
"""

from __future__ import annotations

import json
import io
import os
import sys
from datetime import datetime
from typing import Any

# ── Bootstrap: set OpenAI env vars BEFORE strands/openai are imported ────────
# strands initialises the openai client at import time and reads OPENAI_API_KEY
# and OPENAI_BASE_URL from the environment at that moment. Setting them later
# inside a function is too late — the client is already frozen.
_groq_key = os.environ.get("GROQ_API_KEY", "").strip()
if _groq_key:
    os.environ["OPENAI_API_KEY"]  = _groq_key
    os.environ["OPENAI_BASE_URL"] = "https://api.groq.com/openai/v1"

import boto3
import streamlit as st

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AWS EC2 Agent",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;600;700&family=JetBrains+Mono:wght@400;700&display=swap');

:root {
    --bg:       #06070a;
    --surface:  #0e1117;
    --card:     #131720;
    --border:   #1e2635;
    --accent:   #00e5a0;
    --orange:   #ff6b35;
    --blue:     #5b9cf6;
    --text:     #e2e8f0;
    --muted:    #64748b;
    --danger:   #f87171;
    --mono:     'JetBrains Mono', monospace;
    --sans:     'Space Grotesk', sans-serif;
}

html, body, [class*="css"] {
    font-family: var(--sans) !important;
    background-color: var(--bg) !important;
    color: var(--text);
}

[data-testid="stSidebar"] {
    background: var(--surface) !important;
    border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] label {
    color: var(--muted) !important;
    font-size: 0.78rem !important;
    font-family: var(--mono) !important;
    text-transform: uppercase;
    letter-spacing: 0.07em;
}

[data-testid="stTextInput"] input,
[data-testid="stSelectbox"] > div > div {
    background: var(--card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 6px !important;
    color: var(--text) !important;
    font-family: var(--mono) !important;
    font-size: 0.88rem !important;
}
[data-testid="stTextInput"] input:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 2px rgba(0,229,160,0.15) !important;
}

.stButton > button {
    background: transparent !important;
    border: 1px solid var(--accent) !important;
    color: var(--accent) !important;
    border-radius: 6px !important;
    font-family: var(--mono) !important;
    font-size: 0.8rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.04em !important;
    padding: 7px 18px !important;
    transition: background 0.15s, color 0.15s !important;
}
.stButton > button:hover {
    background: var(--accent) !important;
    color: #06070a !important;
}

.hero {
    position: relative;
    overflow: hidden;
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 32px 36px 28px;
    margin-bottom: 24px;
    background: linear-gradient(135deg, #0e1117 0%, #111827 100%);
}
.hero::before {
    content: "";
    position: absolute;
    inset: 0;
    background: radial-gradient(ellipse at 10% 50%, rgba(0,229,160,0.07) 0%, transparent 60%),
                radial-gradient(ellipse at 90% 20%, rgba(91,156,246,0.06) 0%, transparent 55%);
    pointer-events: none;
}
.hero-eyebrow {
    font-family: var(--mono);
    font-size: 0.7rem;
    color: var(--accent);
    letter-spacing: 0.15em;
    text-transform: uppercase;
    margin-bottom: 8px;
}
.hero h1 {
    font-size: 1.8rem;
    font-weight: 700;
    color: var(--text);
    margin: 0 0 6px 0;
    letter-spacing: -0.03em;
}
.hero p { color: var(--muted); font-size: 0.88rem; margin: 0; }

.status-bar { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; margin-bottom: 20px; }
.chip {
    display: inline-flex; align-items: center; gap: 5px;
    font-family: var(--mono); font-size: 0.72rem; font-weight: 700;
    padding: 4px 12px; border-radius: 20px; letter-spacing: 0.05em;
}
.chip-on   { background: rgba(0,229,160,0.1);  color: var(--accent); border: 1px solid rgba(0,229,160,0.3); }
.chip-off  { background: rgba(248,113,113,0.1); color: var(--danger); border: 1px solid rgba(248,113,113,0.3); }
.chip-warn { background: rgba(255,107,53,0.1);  color: var(--orange); border: 1px solid rgba(255,107,53,0.3); }
.chip-info { background: rgba(91,156,246,0.1);  color: var(--blue);   border: 1px solid rgba(91,156,246,0.3); }

.bubble {
    border-radius: 10px; padding: 14px 18px; margin-bottom: 14px;
    line-height: 1.7; font-size: 0.92rem;
    animation: rise 0.25s ease;
}
@keyframes rise {
    from { opacity: 0; transform: translateY(8px); }
    to   { opacity: 1; transform: translateY(0); }
}
.bubble-user  { background: #101820; border: 1px solid #1e2d45; border-left: 3px solid var(--blue); }
.bubble-agent { background: var(--card); border: 1px solid var(--border); border-left: 3px solid var(--accent); }
.bubble-label {
    font-family: var(--mono); font-size: 0.68rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 6px;
}
.lbl-user  { color: var(--blue); }
.lbl-agent { color: var(--accent); }
.lbl-ts    { color: var(--muted); font-weight: 400; margin-left: 8px; }

.tool-card {
    margin-top: 12px; background: #09111a;
    border: 1px solid #1a2436; border-top: 2px solid var(--orange);
    border-radius: 8px; padding: 12px 16px;
    font-family: var(--mono); font-size: 0.78rem;
}
.tool-card-header {
    display: flex; align-items: center;
    justify-content: space-between; margin-bottom: 8px;
}
.tool-name {
    color: var(--orange); font-weight: 700;
    font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.08em;
}
.tool-card pre {
    margin: 0; color: #94a3b8; white-space: pre-wrap;
    word-break: break-word; background: transparent;
    font-size: 0.78rem; line-height: 1.55;
}

.metric-box { background: var(--bg); border: 1px solid var(--border); border-radius: 8px; padding: 14px 16px; margin-bottom: 8px; }
.metric-val { font-family: var(--mono); font-size: 1.4rem; font-weight: 700; color: var(--accent); line-height: 1; margin-bottom: 4px; }
.metric-lbl { font-size: 0.72rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.06em; }

.env-banner {
    background: rgba(255,107,53,0.08);
    border: 1px solid rgba(255,107,53,0.3);
    border-radius: 8px;
    padding: 12px 16px;
    font-family: var(--mono);
    font-size: 0.78rem;
    color: var(--orange);
    margin-bottom: 16px;
    line-height: 1.6;
}

hr { border-color: var(--border) !important; }

.qa-row .stButton > button {
    border-color: var(--border) !important;
    color: var(--muted) !important;
    font-size: 0.73rem !important;
    padding: 5px 10px !important;
}
.qa-row .stButton > button:hover {
    background: var(--card) !important;
    color: var(--text) !important;
    border-color: var(--accent) !important;
}

.input-row [data-testid="stTextInput"] input {
    font-size: 0.95rem !important;
    padding: 10px 14px !important;
}

#MainMenu, footer, [data-testid="stToolbar"] { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ── Session state ──────────────────────────────────────────────────────────────
def _init_state() -> None:
    defaults: dict[str, Any] = {
        "messages": [],
        "agent": None,
        "agent_ready": False,
        "total_instances": 0,
        "last_instance_id": "—",
        "model_label": "—",
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

_init_state()


# ── Helpers ────────────────────────────────────────────────────────────────────
def _ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


def _get_groq_api_key() -> str:
    """Read Groq API key from environment variable GROQ_API_KEY."""
    key = os.environ.get("GROQ_API_KEY", "").strip()
    return key


def _extract_agent_text(result: Any) -> str:
    if result is None:
        return "Done."
    if hasattr(result, "message") and result.message:
        content = result.message.get("content", [])
        parts = [
            block["text"]
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        ]
        if parts:
            return "\n".join(parts)
    text = str(result).strip()
    return text if text else "Done."


def _extract_tool_result(result: Any) -> str:
    try:
        if hasattr(result, "tool_results") and result.tool_results:
            for tr in result.tool_results:
                content = getattr(tr, "content", None) or []
                for block in content:
                    if hasattr(block, "text") and block.text:
                        return block.text
    except Exception:
        pass
    return ""


# ── _build_agent uses OpenAIModel + Groq ──────────────────────────────────────
def _build_agent(
    model_id: str,
    region: str,
    ami: str,
    itype: str,
    iname: str,
) -> Any:
    from strands import Agent, tool
    from strands.models.openai import OpenAIModel

    # Read API key from environment — never from user input
    api_key = _get_groq_api_key()
    if not api_key:
        raise EnvironmentError(
            "GROQ_API_KEY environment variable is not set. "
            "Please set it before starting the app:\n"
            "  export GROQ_API_KEY=gsk_your_full_key_here"
        )

    # strands' OpenAIModel internally initialises the openai client which
    # reads OPENAI_API_KEY and OPENAI_BASE_URL from the environment,
    # ignoring the kwargs we pass. Set both so requests route to Groq.
    os.environ["OPENAI_API_KEY"] = api_key
    os.environ["OPENAI_BASE_URL"] = "https://api.groq.com/openai/v1"

    _region = region
    _ami    = ami
    _itype  = itype
    _iname  = iname

    @tool
    def create_ec2_instance(
        instance_type: str = _itype,
        ami_id: str        = _ami,
        instance_name: str = _iname,
        region: str        = _region,
    ) -> str:
        """Creates an EC2 instance on AWS using the configured defaults."""
        try:
            ec2 = boto3.client("ec2", region_name=region)
            response = ec2.run_instances(
                ImageId=ami_id,
                InstanceType=instance_type,
                MinCount=1,
                MaxCount=1,
                TagSpecifications=[{
                    "ResourceType": "instance",
                    "Tags": [{"Key": "Name", "Value": instance_name}],
                }],
            )
            inst = response["Instances"][0]
            iid  = inst["InstanceId"]
            return json.dumps({
                "status":        "success",
                "instance_id":   iid,
                "instance_type": inst["InstanceType"],
                "state":         inst["State"]["Name"],
                "region":        region,
            })
        except Exception as exc:
            return json.dumps({"status": "error", "message": str(exc)})

    mdl = OpenAIModel(
        model_id=model_id,
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1",
    )

    return Agent(
        model=mdl,
        tools=[create_ec2_instance],
        system_prompt=(
            "You are an AWS automation agent. When calling create_ec2_instance, "
            "NEVER pass any arguments. Always call it with zero arguments so that "
            "the function's own default values are used. Do not infer, assume, or "
            "supply any parameter values yourself."
        ),
    )


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙ Config")
    st.divider()

    # Show API key status (from env) — no user input needed
    groq_key_present = bool(_get_groq_api_key())
    if groq_key_present:
        st.markdown(
            '<div style="background:rgba(0,229,160,0.08);border:1px solid '
            'rgba(0,229,160,0.3);border-radius:6px;padding:8px 12px;'
            'font-family:\'JetBrains Mono\',monospace;font-size:0.75rem;'
            'color:#00e5a0;margin-bottom:12px;">● GROQ_API_KEY detected</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="env-banner">⚠ GROQ_API_KEY not set<br>'
            'Run: export GROQ_API_KEY=gsk_…</div>',
            unsafe_allow_html=True,
        )

    model_id = st.text_input(
        "Model ID",
        value="openai/gpt-oss-120b",
        help="Groq model identifier",
    )

    st.markdown("**EC2 Defaults**")
    region_opt = st.selectbox("Region",
                              ["ap-south-1", "us-east-1", "us-west-2", "eu-west-1"])
    ami_id     = st.text_input("AMI ID",        value="ami-0f58b397bc5c1f2e8")
    inst_type  = st.selectbox("Instance Type",
                              ["t2.micro", "t3.micro", "t3.small", "t3.medium"])
    inst_name  = st.text_input("Instance Name", value="MyStrandsInstance")

    st.divider()

    init_disabled = not groq_key_present
    if st.button("🔌  Initialise Agent", disabled=init_disabled):
        with st.spinner("Connecting…"):
            try:
                st.session_state.agent = _build_agent(
                    model_id, region_opt,
                    ami_id, inst_type, inst_name,
                )
                st.session_state.agent_ready = True
                st.session_state.model_label = model_id
                st.success("Agent ready ✓")
            except Exception as exc:
                st.error(f"Failed: {exc}")

    st.divider()
    st.markdown("## 📊 Session")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            f'<div class="metric-box">'
            f'<div class="metric-val">{st.session_state.total_instances}</div>'
            f'<div class="metric-lbl">Launched</div></div>',
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f'<div class="metric-box">'
            f'<div class="metric-val">{len(st.session_state.messages)}</div>'
            f'<div class="metric-lbl">Messages</div></div>',
            unsafe_allow_html=True,
        )

    last_id = st.session_state.last_instance_id
    st.markdown(
        f'<div class="metric-box">'
        f'<div class="metric-lbl">Last Instance ID</div>'
        f'<div style="font-family:var(--mono);font-size:0.78rem;'
        f'color:#94a3b8;margin-top:6px;word-break:break-all">{last_id}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    if st.button("🗑  Clear Chat"):
        st.session_state.messages = []
        st.rerun()


# ── Main area ──────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <div class="hero-eyebrow">◈ Strands Agent Interface</div>
    <h1>⚡ AWS EC2 Agent</h1>
    <p>Conversational AWS automation — powered by openai/gpt-oss-120b via Groq</p>
</div>
""", unsafe_allow_html=True)

if st.session_state.agent_ready:
    st.markdown(
        f'<div class="status-bar">'
        f'<span class="chip chip-on">● Agent Online</span>'
        f'<span class="chip chip-info">◈ {st.session_state.model_label}</span>'
        f'<span class="chip chip-info">⬡ groq.com</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
elif not groq_key_present:
    st.markdown(
        '<div class="status-bar">'
        '<span class="chip chip-warn">⚠ GROQ_API_KEY not set — see sidebar</span>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="env-banner">'
        'Set your Groq API key before starting:<br><br>'
        '<code>export GROQ_API_KEY=gsk_your_full_key_here</code><br><br>'
        'Then restart the app: <code>streamlit run app.py</code>'
        '</div>',
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        '<div class="status-bar">'
        '<span class="chip chip-off">○ Agent Offline — initialise in the sidebar</span>'
        '</div>',
        unsafe_allow_html=True,
    )

# ── Chat history ───────────────────────────────────────────────────────────────
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(
            f'<div class="bubble bubble-user">'
            f'<div class="bubble-label lbl-user">▸ You'
            f'<span class="lbl-ts">{msg["ts"]}</span></div>'
            f'{msg["content"]}</div>',
            unsafe_allow_html=True,
        )
    else:
        tool_html = ""
        if msg.get("tool_result"):
            raw = msg["tool_result"]
            try:
                pretty = json.dumps(json.loads(raw), indent=2)
            except Exception:
                pretty = raw
            is_ok    = '"success"' in raw
            chip_cls = "chip-on" if is_ok else "chip-off"
            chip_txt = "SUCCESS" if is_ok else "ERROR"
            tool_html = (
                f'<div class="tool-card">'
                f'<div class="tool-card-header">'
                f'<span class="tool-name">⚙ create_ec2_instance</span>'
                f'<span class="chip {chip_cls}">{chip_txt}</span>'
                f'</div><pre>{pretty}</pre></div>'
            )
        st.markdown(
            f'<div class="bubble bubble-agent">'
            f'<div class="bubble-label lbl-agent">⚡ Agent'
            f'<span class="lbl-ts">{msg["ts"]}</span></div>'
            f'{msg["content"]}{tool_html}</div>',
            unsafe_allow_html=True,
        )

# ── Input ──────────────────────────────────────────────────────────────────────
st.divider()
st.markdown('<div class="input-row">', unsafe_allow_html=True)
inp_col, btn_col = st.columns([6, 1])
with inp_col:
    user_input = st.text_input(
        "message",
        placeholder="e.g.  Launch a new EC2 instance…",
        label_visibility="collapsed",
        key="chat_input",
    )
with btn_col:
    send = st.button("Send →", use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

# Quick-action row
qa_labels = [
    "Launch an EC2 instance",
    "Create t2.micro instance",
    "Spin up a new server",
    "Deploy EC2 now",
]
st.markdown('<div class="qa-row">', unsafe_allow_html=True)
qa_cols = st.columns(len(qa_labels))
for i, label in enumerate(qa_labels):
    if qa_cols[i].button(label, key=f"qa_{i}"):
        user_input = label
        send = True
st.markdown("</div>", unsafe_allow_html=True)

# ── Process ────────────────────────────────────────────────────────────────────
if send and user_input and user_input.strip():
    if not st.session_state.agent_ready:
        st.error("Please initialise the agent in the sidebar first.")
    else:
        prompt = user_input.strip()
        st.session_state.messages.append(
            {"role": "user", "content": prompt, "ts": _ts()}
        )

        err_msg = ""
        with st.spinner("Agent is thinking…"):
            old_out, sys.stdout = sys.stdout, io.StringIO()
            try:
                result = st.session_state.agent(prompt)
            except Exception as exc:
                result  = None
                err_msg = str(exc)
            finally:
                sys.stdout = old_out

        if result is not None:
            agent_text  = _extract_agent_text(result)
            tool_result = _extract_tool_result(result)
            if tool_result:
                try:
                    _data = json.loads(tool_result)
                    if _data.get("status") == "success":
                        st.session_state.total_instances += 1
                        st.session_state.last_instance_id = _data.get("instance_id", "—")
                except Exception:
                    pass
        else:
            agent_text  = f"⚠ Error: {err_msg}"
            tool_result = ""

        st.session_state.messages.append({
            "role":        "agent",
            "content":     agent_text,
            "tool_result": tool_result,
            "ts":          _ts(),
        })
        st.rerun()