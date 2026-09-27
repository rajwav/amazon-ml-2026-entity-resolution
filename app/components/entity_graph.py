"""
Interactive Entity Resolution Explorer & Real-Time Discovery Demo
Demonstrates how the system takes a single Source 1 reference entity
and searches across noisy Source 2 and Source 3 records to discover,
rank, and classify matching entities using LightGBM Model V2.
"""

import os
import sys
import pickle
import time
import streamlit as st
import plotly.graph_objects as go

# Ensure features module can be imported cleanly
SRC_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../code/business_entity_resolution/src"))
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

from features import (
    clean_name, get_tokens, get_digits, get_addr_tokens, get_char_bigrams, extract_features_v2_fast
)
from components.demo_fixtures import DEMO_CASES

MODEL_PATH = os.path.join(SRC_PATH, "model_v2.pkl")
THRESHOLD_PATH = os.path.join(SRC_PATH, "threshold_v2.txt")

@st.cache_resource
def load_production_model():
    """Loads the pre-trained LightGBM Model V2 and calibrated decision threshold."""
    with open(MODEL_PATH, "rb") as f:
        model = pickle.load(f)
    with open(THRESHOLD_PATH, "r") as f:
        threshold = float(f.read().strip())
    return model, threshold

FEATURE_NAMES = [
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


def score_candidate(model, s1_name, s1_addr, t_name, t_addr):
    """Computes exact 11 features and predicts match probability via Model V2."""
    s1_clean = clean_name(s1_name)
    s1_toks = get_tokens(s1_name)
    s1_digs = get_digits(s1_name)
    s1_atoks = get_addr_tokens(s1_addr)
    s1_bg = get_char_bigrams(s1_clean)

    t_clean = clean_name(t_name)
    t_toks = get_tokens(t_name)
    t_digs = get_digits(t_name)
    t_atoks = get_addr_tokens(t_addr)
    t_bg = get_char_bigrams(t_clean)

    features_11d = extract_features_v2_fast(
        s1_clean, s1_toks, s1_digs, s1_atoks, s1_bg,
        t_clean, t_toks, t_digs, t_atoks, t_bg
    )
    prob = float(model.predict_proba([features_11d])[0, 1])
    return prob, features_11d, {
        "s1_clean": s1_clean,
        "s1_toks": s1_toks,
        "s1_digs": s1_digs,
        "s1_atoks": s1_atoks,
        "t_clean": t_clean,
        "t_toks": t_toks,
        "t_digs": t_digs,
        "t_atoks": t_atoks
    }


def generate_explanation(features, is_match):
    """Generates an honest explanation of contributing signals from feature values."""
    (
        exact_match, tok_jaccard, has_shared_dig, exact_dig, dig_jaccard,
        pref4_match, len_diff, len_ratio, addr_tok_jaccard, first_dig_match, char_dice
    ) = features

    reasons = []
    if is_match:
        if exact_match == 1.0:
            reasons.append("✓ Identical normalized business core name")
        elif char_dice >= 0.6:
            reasons.append(f"✓ Strong character-level similarity (char_dice: {char_dice:.2f}) absorbing typos")
        
        if tok_jaccard >= 0.5:
            reasons.append(f"✓ High name token overlap ({tok_jaccard:.0%} of significant tokens match)")
        
        if pref4_match == 1.0:
            reasons.append("✓ Matching 4-character leading brand prefix")
            
        if exact_dig == 1.0:
            reasons.append("✓ Exact match on all numerical building / branch identifiers")
        elif has_shared_dig == 1.0:
            reasons.append("✓ Shared street / plot digit sequence")
            
        if addr_tok_jaccard >= 0.3:
            reasons.append(f"✓ Consistent geographic address locality ({addr_tok_jaccard:.0%} address token overlap)")
            
        if len_ratio >= 0.7:
            reasons.append(f"✓ Balanced name length ratio ({len_ratio:.2f}) preventing false acronym matches")
            
        if not reasons:
            reasons.append("✓ Composite multi-feature score comfortably exceeded the 0.40 decision threshold")
    else:
        if exact_match == 0.0 and char_dice < 0.4:
            reasons.append(f"✗ Low character similarity (char_dice: {char_dice:.2f})")
        if tok_jaccard < 0.2:
            reasons.append("✗ Minimal token overlap in company title")
        if addr_tok_jaccard < 0.2:
            reasons.append("✗ Divergent physical addresses / different metropolitan areas")
        if has_shared_dig == 0.0 and (len(features) > 2 and features[2] == 0.0):
            reasons.append("✗ Conflicting or unshared numerical branch / address identifiers")
        if not reasons:
            reasons.append("✗ Composite signals remained below the calibrated 0.40 precision threshold")

    return reasons


def render_entity_resolver():
    """Renders the realistic S1 -> S2/S3 entity resolution discovery demo."""
    
    try:
        model, threshold = load_production_model()
    except Exception as e:
        st.error(f"Unable to load Model V2 artifact: {e}")
        return

    # Header & Framing
    st.markdown("### ⚡ Entity Resolution Explorer")
    st.markdown(
        """
        <div style="font-size: 1.05rem; color: #f1f5f9; margin-bottom: 4px;">
            Select a reference entity and watch the system discover its corresponding records across noisy sources.
        </div>
        <div style="font-size: 0.85rem; color: #94a3b8; margin-bottom: 18px;">
            <strong>Source 1 (S1)</strong> contains reference/master entities. 
            <strong>Source 2 (S2)</strong> and <strong>Source 3 (S3)</strong> contain noisy, duplicated, reformatted, 
            or partially corrupted records. The model identifies which records refer to the same real-world entity.
        </div>
        """,
        unsafe_allow_html=True
    )

    # -------------------------------------------------------------
    # STEP 1: SELECT A REFERENCE ENTITY
    # -------------------------------------------------------------
    st.markdown("#### 1️⃣ Select a Reference Entity ($S_1$)")

    case_keys = list(DEMO_CASES.keys())
    case_titles = [f"{k}: {DEMO_CASES[k]['title']} ({DEMO_CASES[k]['category']})" for k in case_keys]

    # Initialize state safely before widget instantiation
    if "s1_case_selector" not in st.session_state:
        st.session_state["s1_case_selector"] = 0

    def set_selected_case(idx):
        st.session_state["s1_case_selector"] = idx

    # Search / Selectbox
    selected_case_idx = st.selectbox(
        "🔎 Search or choose reference entity:",
        range(len(case_keys)),
        format_func=lambda i: case_titles[i],
        key="s1_case_selector"
    )
    
    current_case = DEMO_CASES[case_keys[selected_case_idx]]

    # Quick Case Selectors Pills
    st.caption("Quick Case Scenarios:")
    pill_cols = st.columns(len(case_keys))
    for i, ck in enumerate(case_keys):
        c_info = DEMO_CASES[ck]
        with pill_cols[i]:
            st.button(
                c_info['id'],
                key=f"quick_{ck}",
                on_click=set_selected_case,
                args=(i,),
                help=f"{c_info['title']}\n{c_info['category']}",
                use_container_width=True
            )

    # -------------------------------------------------------------
    # STEP 2: SHOW THE SELECTED S1 REFERENCE CARD
    # -------------------------------------------------------------
    st.markdown(
        f"""
        <div class="glass-card" style="border-left: 4px solid #38bdf8; margin: 18px 0 20px 0; padding: 18px 22px;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                <span style="font-size: 0.75rem; font-weight: 700; color: #38bdf8; letter-spacing: 0.08em; text-transform: uppercase;">
                    📦 SOURCE 1 — REFERENCE ENTITY
                </span>
                <span class="badge badge-cyan">Reference Entity</span>
            </div>
            <div style="font-size: 1.55rem; font-weight: 800; color: #ffffff; margin-bottom: 6px;">
                {current_case['s1_name']}
            </div>
            <div style="font-size: 0.95rem; color: #cbd5e1; margin-bottom: 10px;">
                📍 {current_case['s1_addr']} • <strong style="color: #94a3b8;">{current_case['country']}</strong>
            </div>
            <div style="font-size: 0.8rem; color: #94a3b8; font-style: italic;">
                Scenario Note: {current_case['description']}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # -------------------------------------------------------------
    # STEP 3: "FIND MATCHES" INTERACTION
    # -------------------------------------------------------------
    search_clicked = st.button("⚡ FIND RELATED RECORDS ACROSS S2 & S3", type="primary", use_container_width=True)

    # Maintain execution state in session
    state_key = f"discovered_{current_case['id']}"
    if search_clicked:
        st.session_state[state_key] = True

    is_discovered = st.session_state.get(state_key, True)

    if is_discovered:
        # Animated Pipeline Flow Indicator
        st.markdown(
            """
            <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(56, 189, 248, 0.25); border-radius: 10px; padding: 12px 16px; margin: 14px 0 24px 0; text-align: center;">
                <div style="display: flex; justify-content: center; align-items: center; gap: 8px; flex-wrap: wrap; font-size: 0.8rem; font-weight: 600; font-family: monospace;">
                    <span style="color: #38bdf8;">S1 ENTITY</span>
                    <span style="color: #64748b;">➔</span>
                    <span style="color: #c084fc;">NORMALIZATION</span>
                    <span style="color: #64748b;">➔</span>
                    <span style="color: #fbbf24;">BLOCKING</span>
                    <span style="color: #64748b;">➔</span>
                    <span style="color: #38bdf8;">CANDIDATE POOL</span>
                    <span style="color: #64748b;">➔</span>
                    <span style="color: #c084fc;">11-D FEATURES</span>
                    <span style="color: #64748b;">➔</span>
                    <span style="color: #34d399;">LIGHTGBM</span>
                    <span style="color: #64748b;">➔</span>
                    <span style="color: #10b981; font-weight: 800;">DISCOVERED MATCHES</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # -------------------------------------------------------------
        # STEP 4: EVALUATE & SHOW MATCH RESULTS BY SOURCE
        # -------------------------------------------------------------
        st.markdown("#### 2️⃣ Discovered Source Records")

        # Evaluate all candidate records using actual Model V2
        candidate_evaluations = []
        for cand in current_case["candidates"]:
            prob, feats, tokens = score_candidate(
                model,
                current_case["s1_name"],
                current_case["s1_addr"],
                cand["name"],
                cand["address"]
            )
            is_match = (prob >= threshold)
            candidate_evaluations.append({
                "candidate": cand,
                "prob": prob,
                "features": feats,
                "tokens": tokens,
                "is_match": is_match
            })

        # Separate candidates into Source 2 and Source 3
        s2_records = [c for c in candidate_evaluations if c["candidate"]["source"] == "Source 2"]
        s3_records = [c for c in candidate_evaluations if c["candidate"]["source"] == "Source 3"]

        col_s2, col_s3 = st.columns(2)

        with col_s2:
            st.markdown("##### 📚 Source 2 Candidates")
            if not s2_records:
                st.info("No candidate records found in Source 2.")
            for idx, item in enumerate(s2_records):
                c = item["candidate"]
                p = item["prob"]
                m = item["is_match"]
                badge_color = "#10b981" if m else "#f43f5e"
                badge_text = "✓ MATCH" if m else "✗ REJECT"
                border_color = "rgba(16, 185, 129, 0.4)" if m else "rgba(244, 63, 94, 0.25)"
                
                st.markdown(
                    f"""
                    <div class="glass-card" style="border-left: 3px solid {badge_color}; margin-bottom: 12px; padding: 14px 16px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                            <span style="font-size: 0.72rem; font-weight: 700; color: #94a3b8; text-transform: uppercase;">
                                {c['source']} • {c['country']}
                            </span>
                            <span style="font-size: 0.72rem; font-weight: 800; color: {badge_color}; background: rgba(0,0,0,0.3); padding: 2px 8px; border-radius: 4px; border: 1px solid {border_color};">
                                {badge_text}
                            </span>
                        </div>
                        <div style="font-size: 1.05rem; font-weight: 700; color: #f8fafc; margin-bottom: 4px;">
                            {c['name']}
                        </div>
                        <div style="font-size: 0.82rem; color: #94a3b8; margin-bottom: 8px;">
                            📍 {c['address']}
                        </div>
                        <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.78rem;">
                            <span style="color: #cbd5e1;">Model Match Probability:</span>
                            <span style="font-weight: 700; font-family: monospace; color: {badge_color};">{p:.1%}</span>
                        </div>
                        <div style="font-size: 0.72rem; color: #64748b; margin-top: 4px;">
                            Note: {c['notes']}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        with col_s3:
            st.markdown("##### 📚 Source 3 Candidates")
            if not s3_records:
                st.info("No candidate records found in Source 3.")
            for idx, item in enumerate(s3_records):
                c = item["candidate"]
                p = item["prob"]
                m = item["is_match"]
                badge_color = "#10b981" if m else "#f43f5e"
                badge_text = "✓ MATCH" if m else "✗ REJECT"
                border_color = "rgba(16, 185, 129, 0.4)" if m else "rgba(244, 63, 94, 0.25)"
                
                st.markdown(
                    f"""
                    <div class="glass-card" style="border-left: 3px solid {badge_color}; margin-bottom: 12px; padding: 14px 16px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                            <span style="font-size: 0.72rem; font-weight: 700; color: #94a3b8; text-transform: uppercase;">
                                {c['source']} • {c['country']}
                            </span>
                            <span style="font-size: 0.72rem; font-weight: 800; color: {badge_color}; background: rgba(0,0,0,0.3); padding: 2px 8px; border-radius: 4px; border: 1px solid {border_color};">
                                {badge_text}
                            </span>
                        </div>
                        <div style="font-size: 1.05rem; font-weight: 700; color: #f8fafc; margin-bottom: 4px;">
                            {c['name']}
                        </div>
                        <div style="font-size: 0.82rem; color: #94a3b8; margin-bottom: 8px;">
                            📍 {c['address']}
                        </div>
                        <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.78rem;">
                            <span style="color: #cbd5e1;">Model Match Probability:</span>
                            <span style="font-weight: 700; font-family: monospace; color: {badge_color};">{p:.1%}</span>
                        </div>
                        <div style="font-size: 0.72rem; color: #64748b; margin-top: 4px;">
                            Note: {c['notes']}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        # -------------------------------------------------------------
        # STEP 5 & 6: INSPECT A CANDIDATE (PAIRWISE ANALYSIS)
        # -------------------------------------------------------------
        st.markdown("---")
        st.markdown("#### 3️⃣ Deep Candidate Analysis & Signal Decomposition")
        st.caption("Select any discovered record to inspect its pairwise feature extraction and model decision reasoning.")

        candidate_options = [
            f"[{item['candidate']['source']}] {item['candidate']['name']} ({'MATCH' if item['is_match'] else 'REJECT'}, {item['prob']:.1%})"
            for item in candidate_evaluations
        ]
        
        selected_cand_idx = st.selectbox(
            "Select Candidate to Inspect:",
            range(len(candidate_evaluations)),
            format_func=lambda i: candidate_options[i],
            key="candidate_inspector_select"
        )

        active_cand = candidate_evaluations[selected_cand_idx]
        ac_cand = active_cand["candidate"]
        ac_prob = active_cand["prob"]
        ac_feats = active_cand["features"]
        ac_toks = active_cand["tokens"]
        ac_match = active_cand["is_match"]

        col_comp1, col_comp2 = st.columns(2)
        with col_comp1:
            st.markdown(
                f"""
                <div class="glass-card" style="padding: 14px;">
                    <div style="font-size: 0.72rem; color: #38bdf8; font-weight: 700; text-transform: uppercase;">
                        Reference Entity (Source 1)
                    </div>
                    <div style="font-size: 1.15rem; font-weight: 700; color: #ffffff; margin: 4px 0;">
                        {current_case['s1_name']}
                    </div>
                    <div style="font-size: 0.85rem; color: #cbd5e1;">
                        📍 {current_case['s1_addr']}
                    </div>
                    <div style="font-size: 0.75rem; color: #94a3b8; font-family: monospace; margin-top: 6px;">
                        Clean Name: "{ac_toks['s1_clean']}" | Digits: {ac_toks['s1_digs']}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
        with col_comp2:
            st.markdown(
                f"""
                <div class="glass-card" style="padding: 14px;">
                    <div style="font-size: 0.72rem; color: #c084fc; font-weight: 700; text-transform: uppercase;">
                        Candidate Entity ({ac_cand['source']})
                    </div>
                    <div style="font-size: 1.15rem; font-weight: 700; color: #ffffff; margin: 4px 0;">
                        {ac_cand['name']}
                    </div>
                    <div style="font-size: 0.85rem; color: #cbd5e1;">
                        📍 {ac_cand['address']}
                    </div>
                    <div style="font-size: 0.75rem; color: #94a3b8; font-family: monospace; margin-top: 6px;">
                        Clean Name: "{ac_toks['t_clean']}" | Digits: {ac_toks['t_digs']}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

        # Decision & Feature Vector View
        col_feat_chart, col_decision = st.columns([3, 2])

        with col_feat_chart:
            st.markdown("##### 📐 Evaluated 11-Feature Vector")
            
            fig_bar = go.Figure(go.Bar(
                x=ac_feats,
                y=FEATURE_NAMES,
                orientation='h',
                marker=dict(
                    color=ac_feats,
                    colorscale='Tealgrn' if ac_match else 'Burg',
                    line=dict(color='rgba(255,255,255,0.2)', width=1)
                ),
                text=[f"{v:.3f}" if isinstance(v, float) else f"{v}" for v in ac_feats],
                textposition='auto',
                textfont=dict(color='#ffffff', family='JetBrains Mono')
            ))

            fig_bar.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(15, 23, 42, 0.4)',
                xaxis=dict(gridcolor='rgba(255,255,255,0.06)', tickfont=dict(color='#cbd5e1'), range=[0, max(1.1, max(ac_feats) + 0.1)]),
                yaxis=dict(tickfont=dict(color='#cbd5e1', family='JetBrains Mono')),
                margin=dict(l=10, r=20, t=10, b=10),
                height=290
            )
            st.plotly_chart(fig_bar, use_container_width=True)

        with col_decision:
            st.markdown("##### 🧠 Model Decision")
            if ac_match:
                st.markdown(
                    f"""
                    <div style="background: rgba(16, 185, 129, 0.15); border: 2px solid #10b981; border-radius: 12px; padding: 18px; text-align: center; box-shadow: 0 0 20px rgba(16, 185, 129, 0.25);">
                        <div style="font-size: 0.75rem; font-weight: 700; color: #34d399; text-transform: uppercase;">
                            LightGBM Model V2 Decision
                        </div>
                        <div style="font-size: 2.2rem; font-weight: 900; color: #10b981; margin: 6px 0;">
                            ✓ MATCH
                        </div>
                        <div style="font-size: 0.85rem; color: #cbd5e1;">
                            Resolved as identical real-world entity
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f"""
                    <div style="background: rgba(244, 63, 94, 0.12); border: 2px solid #f43f5e; border-radius: 12px; padding: 18px; text-align: center; box-shadow: 0 0 20px rgba(244, 63, 94, 0.2);">
                        <div style="font-size: 0.75rem; font-weight: 700; color: #fb7185; text-transform: uppercase;">
                            LightGBM Model V2 Decision
                        </div>
                        <div style="font-size: 2.2rem; font-weight: 900; color: #f43f5e; margin: 6px 0;">
                            ✗ REJECT
                        </div>
                        <div style="font-size: 0.85rem; color: #cbd5e1;">
                            Filtered out below decision cutoff
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            st.markdown(
                f"""
                <div class="glass-card" style="margin-top: 12px; padding: 12px 16px;">
                    <div style="font-size: 0.75rem; color: #94a3b8; text-transform: uppercase;">Posterior Match Probability</div>
                    <div style="font-size: 1.8rem; font-weight: 800; font-family: monospace; color: {'#34d399' if ac_match else '#f87171'};">
                        {ac_prob:.1%} <span style="font-size: 0.9rem; color: #94a3b8;">({ac_prob:.4f})</span>
                    </div>
                    <div style="font-size: 0.78rem; color: #94a3b8; margin-top: 2px;">
                        Calibrated Decision Threshold: <strong style="color: #f8fafc;">{threshold:.2f}</strong>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

        # Dynamic Reason Decomposition
        st.markdown("##### 💡 Signal Attribution Analysis")
        explanations = generate_explanation(ac_feats, ac_match)
        st.markdown(
            f"""
            <div class="glass-card" style="padding: 14px 18px;">
                <div style="font-size: 0.82rem; font-weight: 700; color: #f8fafc; margin-bottom: 6px;">
                    Why was this considered a {'match' if ac_match else 'rejection'}?
                </div>
                <div style="font-size: 0.85rem; color: #cbd5e1; line-height: 1.6;">
                    These signals contributed to the model's decision:
                    <ul style="margin-top: 6px; padding-left: 20px;">
                        {"".join(f"<li style='margin-bottom: 4px;'>{r}</li>" for r in explanations)}
                    </ul>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # -------------------------------------------------------------
    # ADVANCED MODE: COLLAPSIBLE CUSTOM PAIR INSPECTOR
    # -------------------------------------------------------------
    st.markdown("---")
    with st.expander("🛠️ Advanced → Inspect a custom candidate pair"):
        st.caption("Manually evaluate any arbitrary pair of business entities to inspect feature extraction and model inference live.")
        
        c_adv1, c_adv2 = st.columns(2)
        with c_adv1:
            cust_s1_name = st.text_input("Custom S1 Business Name:", value="Omkar Enterprises Pvt Ltd", key="adv_s1_name")
            cust_s1_addr = st.text_area("Custom S1 Address:", value="G-14, MIDC Industrial Area, Andheri East, Mumbai", height=65, key="adv_s1_addr")
        with c_adv2:
            cust_t_name = st.text_input("Custom Target Business Name:", value="Omkar Enterprises Private Limited", key="adv_t_name")
            cust_t_addr = st.text_area("Custom Target Address:", value="Plot G-14, MIDC, Andheri (E), Mumbai, MH", height=65, key="adv_t_addr")

        c_prob, c_feats, _ = score_candidate(model, cust_s1_name, cust_s1_addr, cust_t_name, cust_t_addr)
        c_match = (c_prob >= threshold)

        r1, r2 = st.columns([1, 2])
        with r1:
            st.metric("Custom Match Probability", f"{c_prob:.1%}", delta="MATCH" if c_match else "REJECT")
        with r2:
            st.write(f"**Classification**: {'✓ MATCH (P >= 0.40)' if c_match else '✗ REJECT (P < 0.40)'}")
            st.caption(f"Raw Features: `{[round(x, 3) for x in c_feats]}`")
