"""
Feature Engineering Explorer Component
Inspects the 11 pairwise similarity signals consumed by LightGBM Model V2,
including their mathematical formulation, operational role, and actual tree split importances.
"""

import streamlit as st
import plotly.graph_objects as go

# Exact 11 features with verified tree split counts from model_v2.pkl
FEATURE_CATALOG = [
    {
        "name": "char_dice",
        "label": "Character Bigram Dice Overlap",
        "splits": 787,
        "type": "Float [0.0, 1.0]",
        "formula": r"\frac{2 \cdot |BG(S_1) \cap BG(T)|}{|BG(S_1)| + |BG(T)|}",
        "description": "Computes the Sørensen-Dice similarity coefficient on character bigram sets from clean core names. Highly effective at capturing OCR misspellings, character transpositions, and phonetic variations.",
        "role": "Top decision tree split driver (26.2% of all splits)."
    },
    {
        "name": "addr_tok_jaccard",
        "label": "Address Token Jaccard",
        "splits": 621,
        "type": "Float [0.0, 1.0]",
        "formula": r"\frac{|Tok_{addr}(S_1) \cap Tok_{addr}(T)|}{|Tok_{addr}(S_1) \cup Tok_{addr}(T)|}",
        "description": "Calculates word token Jaccard similarity across physical address fields (tokens with length >= 4, excluding lone digits). Resolves entities with identical names in disparate locations.",
        "role": "Primary geographic discriminator (20.7% of all splits)."
    },
    {
        "name": "dig_jaccard",
        "label": "Digit Sequence Jaccard",
        "splits": 407,
        "type": "Float [0.0, 1.0]",
        "formula": r"\frac{|Dig(S_1) \cap Dig(T)|}{|Dig(S_1) \cup Dig(T)|}",
        "description": "Evaluates Jaccard overlap on numerical identifier tokens extracted via regex (e.g. branch numbers, plot numbers, pin codes). Distinguishes chains (e.g. 'Store 101' vs 'Store 105').",
        "role": "Crucial for branch and unit separation (13.6% of splits)."
    },
    {
        "name": "len_ratio",
        "label": "Name Length Ratio",
        "splits": 349,
        "type": "Float [0.0, 1.0]",
        "formula": r"\frac{\min(|S_1|, |T|)}{\max(|S_1|, |T|)}",
        "description": "Ratio of character lengths between clean core names. Prevents severe over-merging when a short acronym or word is a substring of an unrelated long company title.",
        "role": "Filters acronym-to-parent overmatches (11.6% of splits)."
    },
    {
        "name": "pref4_match",
        "label": "4-Character Prefix Equality",
        "splits": 283,
        "type": "Binary {0.0, 1.0}",
        "formula": r"\mathbb{I}(S_{1}[:4] = T[:4])",
        "description": "Binary indicator checking whether the initial 4 characters of the clean core names are strictly identical.",
        "role": "Fast prefix anchor for brand matching (9.4% of splits)."
    },
    {
        "name": "tok_jaccard",
        "label": "Name Token Jaccard",
        "splits": 236,
        "type": "Float [0.0, 1.0]",
        "formula": r"\frac{|Tok(S_1) \cap Tok(T)|}{|Tok(S_1) \cup Tok(T)|}",
        "description": "Jaccard similarity on significant alphabetical tokens (length >= 5, excluding corporate legal suffixes like 'pvt', 'ltd', 'inc'). Invariant to word reordering.",
        "role": "Captures multi-word business title overlap (7.9% of splits)."
    },
    {
        "name": "len_diff",
        "label": "Absolute Length Difference",
        "splits": 217,
        "type": "Float >= 0.0",
        "formula": r"||S_1| - |T||",
        "description": "Raw character length delta between query and target core names.",
        "role": "Complements len_ratio on absolute scale (7.2% of splits)."
    },
    {
        "name": "exact_dig",
        "label": "Exact Digits Equality",
        "splits": 70,
        "type": "Binary {0.0, 1.0}",
        "formula": r"\mathbb{I}(Dig(S_1) = Dig(T) \land Dig(S_1) \neq \emptyset)",
        "description": "Binary indicator that evaluates to 1.0 only if both entities possess identical sets of numeric sequences.",
        "role": "Strong positive match signal (2.3% of splits)."
    },
    {
        "name": "has_shared_dig",
        "label": "Has Shared Digits",
        "splits": 17,
        "type": "Binary {0.0, 1.0}",
        "formula": r"\mathbb{I}(|Dig(S_1) \cap Dig(T)| > 0)",
        "description": "Binary indicator for whether at least one number is shared between the two records.",
        "role": "Coarse numeric alignment filter (0.6% of splits)."
    },
    {
        "name": "first_dig_match",
        "label": "First Digit Match",
        "splits": 11,
        "type": "Binary {0.0, 1.0}",
        "formula": r"\mathbb{I}(Dig(S_1)[0] = Dig(T)[0])",
        "description": "Checks if the primary street or unit number sequence matches exactly.",
        "role": "Pinpoint street address alignment (0.4% of splits)."
    },
    {
        "name": "exact_match",
        "label": "Exact Clean Name Equality",
        "splits": 2,
        "type": "Binary {0.0, 1.0}",
        "formula": r"\mathbb{I}(Clean(S_1) = Clean(T))",
        "description": "Binary indicator for perfect character-for-character equality after lowercase alphanumeric stripping.",
        "role": "Instant deterministic short-circuit (0.1% of splits)."
    }
]

def render_feature_view():
    """Renders the feature analysis and LightGBM tree importance view."""
    
    st.markdown("### 🔬 11-Dimensional Feature Engineering Matrix")
    st.caption("Detailed taxonomy of the 11 verified pairwise signals consumed by LightGBM Model V2.")

    col_chart, col_stats = st.columns([3, 2])
    
    with col_chart:
        st.markdown("##### 🌲 Model V2 Feature Importance (Total Tree Splits = 3,000)")
        
        feature_names = [f["name"] for f in FEATURE_CATALOG]
        split_counts = [f["splits"] for f in FEATURE_CATALOG]
        
        # Horizontal bar chart sorted by splits
        fig_bar = go.Figure(go.Bar(
            x=split_counts[::-1],
            y=feature_names[::-1],
            orientation='h',
            marker=dict(
                color=split_counts[::-1],
                colorscale='Viridis',
                line=dict(color='rgba(255,255,255,0.2)', width=1)
            ),
            text=[f"{s} splits" for s in split_counts[::-1]],
            textposition='auto',
            textfont=dict(color='#ffffff', family='JetBrains Mono')
        ))

        fig_bar.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(15, 23, 42, 0.4)',
            xaxis=dict(gridcolor='rgba(255,255,255,0.06)', tickfont=dict(color='#cbd5e1'), title="Number of Tree Decision Splits"),
            yaxis=dict(tickfont=dict(color='#cbd5e1', family='JetBrains Mono')),
            margin=dict(l=10, r=20, t=10, b=10),
            height=380
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_stats:
        st.markdown("##### 💡 Key Feature Takeaways")
        st.markdown(
            """
            - **Top Discriminator (`char_dice` = 787 splits)**:
              Character bigram dice coefficient drives **26.2%** of all tree splits. It gracefully absorbs OCR typos, punctuation omissions, and minor spelling differences without expensive edit-distance algorithms.
            
            - **Geographic Confirmation (`addr_tok_jaccard` = 621 splits)**:
              Address token similarity is the second most critical signal (**20.7%**), preventing false merges between identically named franchises in different metropolitan districts.
            
            - **Numerical Identifiers (`dig_jaccard` = 407 splits)**:
              Digits represent store branches, ward numbers, and building numbers. High digit overlap strongly separates true branches.
            """
        )

    # Detailed expandable feature table
    st.markdown("---")
    st.markdown("#### 📚 Full Feature Specification & Mathematical Formulations")
    
    for f in FEATURE_CATALOG:
        with st.expander(f"`{f['name']}` — {f['label']} ({f['splits']} splits)"):
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(f"**Description**: {f['description']}")
                st.markdown(f"**Mathematical Formula**:")
                st.latex(f["formula"])
            with c2:
                st.markdown(f"**Type**: `{f['type']}`")
                st.markdown(f"**Tree Splits**: `{f['splits']}` / 3,000")
                st.markdown(f"**Role**: {f['role']}")
