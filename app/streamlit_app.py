"""
Entity Resolution Lab — Futuristic AI Architecture & Demo Suite
Amazon ML Challenge 2026 Portfolio Demonstration Layer
"""

import os
import streamlit as st

# Configure wide page with dark theme
st.set_page_config(
    page_title="Entity Resolution Lab",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Load external CSS styles
CSS_PATH = os.path.join(os.path.dirname(__file__), "assets/styles.css")
if os.path.exists(CSS_PATH):
    with open(CSS_PATH, "r") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Import modular presentation components
from components.architecture import render_architecture_visualization
from components.entity_graph import render_entity_resolver
from components.funnel import render_funnel_view
from components.feature_view import render_feature_view
from components.metrics import render_metrics_dashboard


def main():
    # Header Banner
    st.markdown('<div class="lab-title">⚡ ENTITY RESOLUTION LAB</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="lab-subtitle">Industrial-Scale Multilingual Business Entity Resolution • Multi-Channel Blocking & Gradient Boosted Classification</div>',
        unsafe_allow_html=True
    )

    # Status Badges
    st.markdown(
        """
        <div class="badge-container">
            <span class="badge badge-cyan">Model V2 (LightGBM)</span>
            <span class="badge badge-emerald">Macro F0.5 = 0.8237</span>
            <span class="badge badge-purple">1.73M Queries • 9.97M Targets</span>
            <span class="badge badge-amber">Streaming Peak RAM: 4.8 GB</span>
            <span class="badge badge-cyan">Official Validator: 100% PASS</span>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Primary Navigation Tabs
    tab_arch, tab_live, tab_funnel, tab_features, tab_metrics = st.tabs([
        "🌐 System Architecture",
        "⚡ Live Entity Resolver",
        "🌪️ Search Space Funnel",
        "🔬 Feature Matrix",
        "📊 Telemetry & Metrics"
    ])

    with tab_arch:
        render_architecture_visualization()

    with tab_live:
        render_entity_resolver()

    with tab_funnel:
        render_funnel_view()

    with tab_features:
        render_feature_view()

    with tab_metrics:
        render_metrics_dashboard()

    # Footer
    st.markdown("---")
    st.caption(
        "⚡ **Entity Resolution Lab** • Standalone portfolio & architecture demonstration suite. "
        "Built strictly as an isolated visualization layer around the frozen entity resolution pipeline."
    )


if __name__ == "__main__":
    main()
