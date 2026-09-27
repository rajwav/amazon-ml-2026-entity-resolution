"""
Interactive Entity Resolution & Live Inference Demo
Allows interactive evaluation of real or custom business entity pairs.
Extracts the exact 11 features live using features.py and scores them
with the pre-trained LightGBM model_v2.pkl against threshold 0.40.
"""

import os
import sys
import pickle
import streamlit as st
import plotly.graph_objects as go

# Ensure features module can be imported cleanly
SRC_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../code/business_entity_resolution/src"))
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

from features import (
    clean_name, get_tokens, get_digits, get_addr_tokens, get_char_bigrams, extract_features_v2_fast
)

MODEL_PATH = os.path.join(SRC_PATH, "model_v2.pkl")
THRESHOLD_PATH = os.path.join(SRC_PATH, "threshold_v2.txt")

@st.cache_resource
def load_production_model():
    """Loads the trained Model V2 and calibrated decision threshold."""
    with open(MODEL_PATH, "rb") as f:
        model = pickle.load(f)
    with open(THRESHOLD_PATH, "r") as f:
        threshold = float(f.read().strip())
    return model, threshold

# Realistic preset entity pairs representing common real-world resolution scenarios
BENCHMARK_PRESETS = {
    "Scenario 1: True Match (Corporate Suffix & Address Variations)": {
        "s1_name": "Apex Healthcare Solutions Pvt Ltd",
        "s1_addr": "Plot 45, Sector 18, Electronic City, Bangalore",
        "t_name": "Apex Healthcare Solutions Private Limited",
        "t_addr": "45, Sector 18, Electronic City Phase 1, Bangalore, Karnataka",
        "scenario_type": "True Match (High Confidence)"
    },
    "Scenario 2: True Match (Spelling Typo & OCR Noise)": {
        "s1_name": "Kalyan Jewellers India Limited",
        "s1_addr": "Shop 12, Ground Floor, MG Road, Pune, Maharashtra",
        "t_name": "Kalyan Jewelers India Ltd",
        "t_addr": "Shop No 12, Gr Flr, Mahatma Gandhi Rd, Pune",
        "scenario_type": "True Match (Lexical Perturbation)"
    },
    "Scenario 3: Hard Negative (Identical Name, Different City/Location)": {
        "s1_name": "Metro Cash & Carry India",
        "s1_addr": "Survey No 24, Yeshwanthpur, Bangalore, Karnataka",
        "t_name": "Metro Cash & Carry India",
        "t_addr": "Plot 88, Moosapet, Kukatpally, Hyderabad, Telangana",
        "scenario_type": "Hard Negative (Location Divergence)"
    },
    "Scenario 4: Hard Negative (Conflicting Branch / Unit Numbers)": {
        "s1_name": "Federal Bank Branch 104",
        "s1_addr": "Building 5, Commercial Complex, Sector 22, Chandigarh",
        "t_name": "Federal Bank Branch 208",
        "t_addr": "Building 5, Commercial Complex, Sector 22, Chandigarh",
        "scenario_type": "Hard Negative (Conflicting Branch Digits)"
    },
    "Scenario 5: Complete Negative (Unrelated Entities)": {
        "s1_name": "Zenith Cloud Systems Technologies",
        "s1_addr": "Tech Park 4, Whitefield, Bangalore",
        "t_name": "Bhartiya Global Logistics Services",
        "t_addr": "Industrial Area Phase 2, Okhla, New Delhi",
        "scenario_type": "True Negative (Disparate Entities)"
    }
}

FEATURE_LABELS = [
    "exact_match",
    "tok_jaccard",
    "has_shared_dig",
    "exact_dig",
    "dig_jaccard",
    "pref4_match",
    "len_diff",
    "len_ratio",
    "addr_tok_jaccard",
    "first_dig_match",
    "char_dice"
]

def render_entity_resolver():
    """Renders the live interactive pairwise entity resolution sandbox."""
    
    st.markdown("### ⚡ Live Entity Resolution Sandbox")
    st.caption("Test the live LightGBM model on real-world entity pairs or supply custom business records.")

    model, threshold = load_production_model()

    # Preset Selection vs Custom Input Mode
    mode = st.radio("Input Mode:", ["Choose Benchmark Scenario", "Enter Custom Business Records"], horizontal=True)

    if mode == "Choose Benchmark Scenario":
        selected_scenario_name = st.selectbox("Select Scenario:", list(BENCHMARK_PRESETS.keys()))
        scenario_data = BENCHMARK_PRESETS[selected_scenario_name]
        default_s1_name = scenario_data["s1_name"]
        default_s1_addr = scenario_data["s1_addr"]
        default_t_name = scenario_data["t_name"]
        default_t_addr = scenario_data["t_addr"]
        st.caption(f"**Scenario Profile**: `{scenario_data['scenario_type']}`")
    else:
        default_s1_name = "Omkar Enterprises Pvt Ltd"
        default_s1_addr = "G-14, MIDC Industrial Area, Andheri East, Mumbai"
        default_t_name = "Omkar Enterprises Private Limited"
        default_t_addr = "Plot G-14, MIDC, Andheri (E), Mumbai, MH"

    col_s1, col_t = st.columns(2)
    with col_s1:
        st.markdown("##### 🏢 Source 1 Query Entity ($S_1$)")
        s1_input_name = st.text_input("S1 Business Name:", value=default_s1_name, key="s1_name_input")
        s1_input_addr = st.text_area("S1 Address:", value=default_s1_addr, height=75, key="s1_addr_input")

    with col_t:
        st.markdown("##### 🎯 Target Candidate Entity ($S_2 / S_3$)")
        t_input_name = st.text_input("Target Business Name:", value=default_t_name, key="t_name_input")
        t_input_addr = st.text_area("Target Address:", value=default_t_addr, height=75, key="t_addr_input")

    # Live Preprocessing & Feature Extraction
    s1_clean = clean_name(s1_input_name)
    s1_toks = get_tokens(s1_input_name)
    s1_digs = get_digits(s1_input_name)
    s1_atoks = get_addr_tokens(s1_input_addr)
    s1_bg = get_char_bigrams(s1_clean)

    t_clean = clean_name(t_input_name)
    t_toks = get_tokens(t_input_name)
    t_digs = get_digits(t_input_name)
    t_atoks = get_addr_tokens(t_input_addr)
    t_bg = get_char_bigrams(t_clean)

    # Compute exact 11 features
    features_11d = extract_features_v2_fast(
        s1_clean, s1_toks, s1_digs, s1_atoks, s1_bg,
        t_clean, t_toks, t_digs, t_atoks, t_bg
    )

    # Execute Model V2 Inference
    prob = float(model.predict_proba([features_11d])[0, 1])
    is_match = (prob >= threshold)

    st.markdown("---")
    st.markdown("#### 🧠 Model Decision & Inference Telemetry")

    col_res1, col_res2 = st.columns([2, 3])

    with col_res1:
        if is_match:
            decision_badge = """
            <div style="background: rgba(16, 185, 129, 0.15); border: 2px solid #10b981; border-radius: 12px; padding: 20px; text-align: center; box-shadow: 0 0 20px rgba(16, 185, 129, 0.25);">
                <div style="font-size: 0.8rem; font-weight: 700; color: #34d399; text-transform: uppercase; letter-spacing: 0.08em;">Final Model Classification</div>
                <div style="font-size: 2.3rem; font-weight: 900; color: #10b981; margin: 8px 0;">MATCH</div>
                <div style="font-size: 0.85rem; color: #cbd5e1;">Resolved as identical real-world business</div>
            </div>
            """
        else:
            decision_badge = """
            <div style="background: rgba(244, 63, 94, 0.12); border: 2px solid #f43f5e; border-radius: 12px; padding: 20px; text-align: center; box-shadow: 0 0 20px rgba(244, 63, 94, 0.2);">
                <div style="font-size: 0.8rem; font-weight: 700; color: #fb7185; text-transform: uppercase; letter-spacing: 0.08em;">Final Model Classification</div>
                <div style="font-size: 2.3rem; font-weight: 900; color: #f43f5e; margin: 8px 0;">REJECT</div>
                <div style="font-size: 0.85rem; color: #cbd5e1;">Filtered out below decision threshold</div>
            </div>
            """
        st.markdown(decision_badge, unsafe_allow_html=True)

        st.markdown(
            f"""
            <div class="glass-card" style="margin-top: 14px; padding: 14px;">
                <div style="font-size: 0.75rem; color: #94a3b8; text-transform: uppercase;">Match Probability P(y=1)</div>
                <div style="font-size: 1.8rem; font-weight: 800; font-family: monospace; color: {'#34d399' if is_match else '#f87171'};">
                    {prob:.4f}
                </div>
                <div style="font-size: 0.78rem; color: #94a3b8; margin-top: 4px;">
                    Calibrated Threshold: <strong style="color: #f8fafc;">{threshold:.2f}</strong>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col_res2:
        # Radar or Horizontal Bar of the 11 feature signals
        fig_feat = go.Figure(go.Bar(
            x=features_11d,
            y=FEATURE_LABELS,
            orientation='h',
            marker=dict(
                color=features_11d,
                colorscale='Tealgrn' if is_match else 'Burg',
                line=dict(color='rgba(255,255,255,0.2)', width=1)
            ),
            text=[f"{v:.3f}" if isinstance(v, float) else f"{v}" for v in features_11d],
            textposition='auto',
            textfont=dict(color='#ffffff', family='JetBrains Mono')
        ))

        fig_feat.update_layout(
            title=dict(text="<b>Pairwise 11-Feature Vector</b>", font=dict(color="#f8fafc", size=13)),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(15, 23, 42, 0.4)',
            xaxis=dict(gridcolor='rgba(255,255,255,0.06)', tickfont=dict(color='#cbd5e1'), range=[0, max(1.1, max(features_11d) + 0.1)]),
            yaxis=dict(tickfont=dict(color='#cbd5e1', family='JetBrains Mono')),
            margin=dict(l=10, r=20, t=35, b=10),
            height=280
        )
        st.plotly_chart(fig_feat, use_container_width=True)

    # Token and String Inspector
    with st.expander("🔬 Inspect Normalized Substring Tokens"):
        tcol1, tcol2 = st.columns(2)
        with tcol1:
            st.markdown(f"**S1 Clean Core Name**: `{s1_clean}`")
            st.markdown(f"**S1 Tokens (>=5 chars)**: `{s1_toks}`")
            st.markdown(f"**S1 Address Tokens**: `{s1_atoks}`")
            st.markdown(f"**S1 Digits**: `{s1_digs}`")
        with tcol2:
            st.markdown(f"**Target Clean Core Name**: `{t_clean}`")
            st.markdown(f"**Target Tokens (>=5 chars)**: `{t_toks}`")
            st.markdown(f"**Target Address Tokens**: `{t_atoks}`")
            st.markdown(f"**Target Digits**: `{t_digs}`")
