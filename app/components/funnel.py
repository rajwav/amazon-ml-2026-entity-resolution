"""
Candidate Search-Space Reduction Funnel Visualization
Visualizes the logarithmic pruning from 17.27 Trillion pairwise combinations
down to 5.15 Million blocked candidates, and finally 712,042 resolved entities.
"""

import streamlit as st
import plotly.graph_objects as go

def render_funnel_view():
    """Renders the interactive search-space reduction funnel and analytical breakdown."""
    
    st.markdown("### 🌪️ Candidate Space Reduction Funnel")
    st.caption("Visualizing the compression from over 17 Trillion pairwise Cartesian combinations down to verified matches.")

    # High-level summary metrics
    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        st.markdown(
            """
            <div class="glass-card metric-box">
                <div class="metric-label">Full Cartesian Space</div>
                <div class="metric-value" style="color: #94a3b8;">17.27 T</div>
                <div style="font-size: 0.75rem; color: #64748b; margin-top: 4px;">1,732,544 × 9,969,589 pairs</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col_m2:
        st.markdown(
            """
            <div class="glass-card metric-box">
                <div class="metric-label">Candidate Space Pruned</div>
                <div class="metric-value" style="color: #38bdf8;">99.99997%</div>
                <div style="font-size: 0.75rem; color: #34d399; margin-top: 4px;">5.15M Evaluated Pairs</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col_m3:
        st.markdown(
            """
            <div class="glass-card metric-box">
                <div class="metric-label">High-Confidence Matches</div>
                <div class="metric-value" style="color: #34d399;">712,042</div>
                <div style="font-size: 0.75rem; color: #38bdf8; margin-top: 4px;">P(Match) ≥ 0.40 Threshold</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # Funnel Chart
    col_chart, col_narrative = st.columns([3, 2])
    
    with col_chart:
        stages = [
            "1. Exhaustive Cartesian Product (Conceptual)",
            "2. Country Partition Pruning",
            "3. Multi-Channel Blocking Candidates",
            "4. LightGBM Scoring (Model V2)",
            "5. Calibrated Matches (P >= 0.40)"
        ]
        
        # Expressed in millions / billions for readable logarithmic scale
        values = [17272624, 1500000, 5.148, 5.148, 0.712]
        display_texts = [
            "~17.27 Trillion pairs (100%)",
            "~1.50 Trillion within-country pairs",
            "5,148,829 candidate pairs (~0.00003%)",
            "5,148,829 pairs scored by 11 features",
            "712,042 verified matches (Leaderboard)"
        ]

        fig_funnel = go.Figure(go.Funnel(
            y=stages,
            x=[100, 45, 12, 12, 4], # Scaled for visual representation
            text=display_texts,
            textposition="inside",
            textfont=dict(family="JetBrains Mono, monospace", size=11, color="#ffffff"),
            marker=dict(
                colors=["#1e293b", "#334155", "#6366f1", "#0284c7", "#10b981"],
                line=dict(width=1, color="rgba(255, 255, 255, 0.15)")
            ),
            connector=dict(line=dict(color="rgba(56, 189, 248, 0.3)", width=1))
        ))

        fig_funnel.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=10, r=10, t=10, b=10),
            height=360,
            yaxis=dict(tickfont=dict(color='#cbd5e1', size=11))
        )
        st.plotly_chart(fig_funnel, use_container_width=True)

    with col_narrative:
        st.markdown("##### 🔍 Pruning Architecture Analysis")
        st.markdown(
            r"""
            - **Theoretical Search Space**:
              Comparing each of the $1,732,544$ query entities against all $9,969,589$ targets produces:
              $$1.7325 \times 10^6 \times 9.9696 \times 10^6 = 17,272,624,374,416 \text{ pairs}$$
            
            - **Phase 1: Country Partitioning**:
              Since businesses cannot resolve across borders, target indexing is strictly isolated per country.
            
            - **Phase 2: Multi-Channel Hashing**:
              Inverted indexes on clean core names, significant tokens, and address digits yield only **5,148,829 total candidate pairs**—achieving a **$99.99997\%$ reduction** in candidate volume.
            
            - **Phase 3: LightGBM Vectorization**:
              Each candidate pair receives an 11-feature vector and is scored by Model V2. Pairs meeting or exceeding the **0.40 threshold** yield **712,042 matches**.
            """
        )
